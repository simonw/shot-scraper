import click
from click_default_group import DefaultGroup
import json
import os
import pathlib
from playwright.sync_api import sync_playwright, Error, TimeoutError
from runpy import run_module
import secrets
import sys
import textwrap
import time
import yaml

from shot_scraper.utils import filename_for_url, url_or_file_path

BROWSERS = ("chromium", "firefox", "chrome", "chrome-beta")


def browser_option(fn):
    click.option(
        "--browser",
        "-b",
        default="chromium",
        type=click.Choice(BROWSERS, case_sensitive=False),
        help="Which browser to use",
    )(fn)
    return fn


@click.group(
    cls=DefaultGroup,
    default="shot",
    default_if_no_args=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
)
@click.version_option()
def cli():
    "Tools for taking automated screenshots"
    pass


@cli.command()
@click.argument("url")  # TODO: validate with custom type
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option(
    "-w",
    "--width",
    type=int,
    help="Width of browser window, defaults to 1280",
    default=1280,
)
@click.option(
    "-h",
    "--height",
    type=int,
    help="Height of browser window and shot - defaults to the full height of the page",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=True, writable=True, dir_okay=False, allow_dash=True),
)
@click.option(
    "selectors",
    "-s",
    "--selector",
    help="Take shot of first element matching this CSS selector",
    multiple=True,
)
@click.option(
    "-p",
    "--padding",
    type=int,
    help="When using selectors, add this much padding in pixels",
    default=0,
)
@click.option("-j", "--javascript", help="Execute this JS prior to taking the shot")
@click.option("--retina", is_flag=True, help="Use device scale factor of 2")
@click.option("--quality", type=int, help="Save as JPEG with this quality, e.g. 80")
@click.option(
    "--wait", type=int, help="Wait this many milliseconds before taking the screenshot"
)
@click.option(
    "--timeout",
    type=int,
    help="Wait this many milliseconds before failing",
)
@click.option(
    "-i",
    "--interactive",
    is_flag=True,
    help="Interact with the page in a browser before taking the shot",
)
@click.option(
    "--devtools",
    is_flag=True,
    help="Interact mode with developer tools",
)
@browser_option
def shot(
    url,
    auth,
    output,
    width,
    height,
    selectors,
    padding,
    javascript,
    retina,
    quality,
    wait,
    timeout,
    interactive,
    devtools,
    browser,
):
    """
    Take a single screenshot of a page or portion of a page.

    Usage:

        shot-scraper www.example.com

    This will write the screenshot to www-example-com.png

    Use "-o" to write to a specific file:

        shot-scraper https://www.example.com/ -o example.png

    You can also pass a path to a local file on disk:

        shot-scraper index.html -o index.png

    Using "-o -" will output to standard out:

        shot-scraper https://www.example.com/ -o - > example.png

    Use -s to take a screenshot of one area of the page, identified using
    one or more CSS selectors:

        shot-scraper https://simonwillison.net -s '#bighead'
    """
    if output is None:
        output = filename_for_url(url, file_exists=os.path.exists)
    shot = {
        "url": url,
        "selectors": selectors,
        "javascript": javascript,
        "width": width,
        "height": height,
        "quality": quality,
        "wait": wait,
        "timeout": timeout,
        "padding": padding,
        "retina": retina,
    }
    interactive = interactive or devtools
    with sync_playwright() as p:
        use_existing_page = False
        context, browser_obj = _browser_context(
            p,
            auth,
            interactive=interactive,
            devtools=devtools,
            retina=retina,
            browser=browser,
            timeout=timeout,
        )
        if interactive or devtools:
            use_existing_page = True
            page = context.new_page()
            page.goto(url)
            context = page
            click.echo(
                "Hit <enter> to take the shot and close the browser window:", err=True
            )
            input()
        try:
            if output == "-":
                shot = take_shot(
                    context,
                    shot,
                    return_bytes=True,
                    use_existing_page=use_existing_page,
                )
                sys.stdout.buffer.write(shot)
            else:
                shot["output"] = str(output)
                shot = take_shot(context, shot, use_existing_page=use_existing_page)
        except TimeoutError as e:
            raise click.ClickException(str(e))
        browser_obj.close()


def _browser_context(
    p,
    auth,
    interactive=False,
    devtools=False,
    retina=False,
    browser="chromium",
    timeout=None,
):
    browser_kwargs = dict(headless=not interactive, devtools=devtools)
    if browser == "chromium":
        browser_obj = p.chromium.launch(**browser_kwargs)
    elif browser == "firefox":
        browser_obj = p.firefox.launch(**browser_kwargs)
    else:
        browser_kwargs["channel"] = browser
        browser_obj = p.chromium.launch(**browser_kwargs)
    context_args = {}
    if auth:
        context_args["storage_state"] = json.load(auth)
    if retina:
        context_args["device_scale_factor"] = 2
    context = browser_obj.new_context(**context_args)
    if timeout:
        context.set_default_timeout(timeout)
    return context, browser_obj


@cli.command()
@click.argument("config", type=click.File(mode="r"))
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option("--retina", is_flag=True, help="Use device scale factor of 2")
@click.option(
    "--timeout",
    type=int,
    help="Wait this many milliseconds before failing",
)
@click.option("--fail-on-error", is_flag=True, help="Fail noisily on error")
@browser_option
def multi(config, auth, retina, timeout, fail_on_error, browser):
    """
    Take multiple screenshots, defined by a YAML file

    Usage:

        shot-scraper multi config.yml

    Where config.yml contains configuration like this:

    \b
        - output: example.png
          url: http://www.example.com/
    """
    shots = yaml.safe_load(config)
    if shots is None:
        shots = []
    if not isinstance(shots, list):
        raise click.ClickException("YAML file must contain a list")
    with sync_playwright() as p:
        context, browser_obj = _browser_context(
            p, auth, retina=retina, browser=browser, timeout=timeout
        )
        for shot in shots:
            try:
                take_shot(context, shot)
            except TimeoutError as e:
                if fail_on_error:
                    raise click.ClickException(str(e))
                else:
                    click.echo(str(e), err=True)
                    continue
        browser_obj.close()


@cli.command()
@click.argument("url")
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option(
    "-o",
    "--output",
    type=click.File("w"),
    default="-",
)
@click.option("-j", "--javascript", help="Execute this JS prior to taking the snapshot")
def accessibility(url, auth, output, javascript):
    """
    Dump the Chromium accessibility tree for the specifed page

    Usage:

        shot-scraper accessibility https://datasette.io/
    """
    url = url_or_file_path(url, _check_and_absolutize)
    with sync_playwright() as p:
        context, browser_obj = _browser_context(p, auth)
        page = context.new_page()
        page.goto(url)
        if javascript:
            _evaluate_js(page, javascript)
        snapshot = page.accessibility.snapshot()
        browser_obj.close()
    output.write(json.dumps(snapshot, indent=4))
    output.write("\n")


@cli.command()
@click.argument("url")
@click.argument("javascript", required=False)
@click.option(
    "-i",
    "--input",
    type=click.File("r"),
    default="-",
    help="Read input JavaScript from this file",
)
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option(
    "-o",
    "--output",
    type=click.File("w"),
    default="-",
    help="Save output JSON to this file",
)
@browser_option
def javascript(url, javascript, input, auth, output, browser):
    """
    Execute JavaScript against the page and return the result as JSON

    Usage:

        shot-scraper javascript https://datasette.io/ "document.title"

    To return a JSON object, use this:

        "({title: document.title, location: document.location})"

    To use setInterval() or similar, pass a promise:

    \b
        "new Promise(done => setInterval(
          () => {
            done({
              title: document.title,
              h2: document.querySelector('h2').innerHTML
            });
          }, 1000
        ));"

    If a JavaScript error occurs an exit code of 1 will be returned.
    """
    if not javascript:
        javascript = input.read()
    url = url_or_file_path(url, _check_and_absolutize)
    with sync_playwright() as p:
        context, browser_obj = _browser_context(p, auth, browser=browser)
        page = context.new_page()
        page.goto(url)
        result = _evaluate_js(page, javascript)
        browser_obj.close()
    output.write(json.dumps(result, indent=4, default=str))
    output.write("\n")


@cli.command()
@click.argument("url")
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=True, writable=True, dir_okay=False, allow_dash=True),
)
@click.option("-j", "--javascript", help="Execute this JS prior to creating the PDF")
@click.option(
    "--wait", type=int, help="Wait this many milliseconds before taking the screenshot"
)
@click.option(
    "--media-screen", is_flag=True, help="Use screen rather than print styles"
)
@click.option("--landscape", is_flag=True, help="Use landscape orientation")
def pdf(url, auth, output, javascript, wait, media_screen, landscape):
    """
    Create a PDF of the specified page

    Usage:

        shot-scraper pdf https://datasette.io/

    Use -o to specify a filename:

        shot-scarper pdf https://datasette.io/ -o datasette.pdf
    """
    url = url_or_file_path(url, _check_and_absolutize)
    if output is None:
        output = filename_for_url(url, ext="pdf", file_exists=os.path.exists)
    with sync_playwright() as p:
        context, browser_obj = _browser_context(p, auth)
        page = context.new_page()
        page.goto(url)
        if wait:
            time.sleep(wait / 1000)
        if javascript:
            _evaluate_js(page, javascript)

        kwargs = {
            "landscape": landscape,
        }
        if output != "-":
            kwargs["path"] = output

        if media_screen:
            page.emulate_media(media="screen")

        pdf = page.pdf(**kwargs)

        if output == "-":
            sys.stdout.buffer.write(pdf)
        else:
            click.echo(
                "Screenshot of '{}' written to '{}'".format(url, output), err=True
            )

        browser_obj.close()


@cli.command()
@click.option(
    "--browser",
    "-b",
    default="chromium",
    type=click.Choice(BROWSERS, case_sensitive=False),
    help="Which browser to install",
)
def install(browser):
    """
    Install the Playwright browser needed by this tool.

    Usage:

        shot-scraper install

    Or for browsers other than the Chromium default:

        shot-scraper install -b firefox
    """
    sys.argv = ["playwright", "install", browser]
    run_module("playwright", run_name="__main__")


@cli.command()
@click.argument("url")
@click.argument(
    "context_file",
    type=click.Path(file_okay=True, writable=True, dir_okay=False, allow_dash=True),
)
def auth(url, context_file):
    """
    Open a browser so user can manually authenticate with the specified site,
    then save the resulting authentication context to a file.

    Usage:

        shot-scraper auth https://github.com/ auth.json
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)
        click.echo("Hit <enter> after you have signed in:", err=True)
        input()
        context_state = context.storage_state()
    context_json = json.dumps(context_state, indent=2) + "\n"
    if context_file == "-":
        click.echo(context_json)
    else:
        with open(context_file, "w") as fp:
            fp.write(context_json)
        # chmod 600 to avoid other users on the shared machine reading it
        pathlib.Path(context_file).chmod(0o600)


class ShotError(Exception):
    pass


def _check_and_absolutize(filepath):
    path = pathlib.Path(filepath)
    if path.exists():
        return path.absolute()
    return False


def take_shot(
    context_or_page,
    shot,
    return_bytes=False,
    use_existing_page=False,
):
    url = shot.get("url") or ""
    if not url:
        raise ShotError("url is required")

    url = url_or_file_path(url, file_exists=_check_and_absolutize)

    output = shot.get("output", "").strip()
    if not output and not return_bytes:
        output = filename_for_url(url, ext="png", file_exists=os.path.exists)
    quality = shot.get("quality")
    wait = shot.get("wait")
    padding = shot.get("padding") or 0

    # If a single 'selector' turn that into selectors array with one item
    selectors = shot.get("selectors") or []
    if shot.get("selector"):
        selectors.append(shot["selector"])

    if not use_existing_page:
        page = context_or_page.new_page()
    else:
        page = context_or_page

    viewport = {}
    full_page = True
    if shot.get("width") or shot.get("height"):
        viewport = {
            "width": shot.get("width") or 1280,
            "height": shot.get("height") or 720,
        }
        page.set_viewport_size(viewport)
        if shot.get("height"):
            full_page = False

    page.goto(url)

    if wait:
        time.sleep(wait / 1000)
    javascript = shot.get("javascript")
    if javascript:
        _evaluate_js(page, javascript)

    screenshot_args = {}
    if quality:
        screenshot_args.update({"quality": quality, "type": "jpeg"})
    if not return_bytes:
        screenshot_args["path"] = output

    if not selectors:
        screenshot_args["full_page"] = full_page

    if selectors:
        # Use JavaScript to create a box around those elements
        selector_javascript, selector_to_shoot = _selector_javascript(
            selectors, padding
        )
        _evaluate_js(page, selector_javascript)
        if return_bytes:
            return page.locator(selector_to_shoot).screenshot(**screenshot_args)
        else:
            page.locator(selector_to_shoot).screenshot(**screenshot_args)
            message = "Screenshot of '{}' on '{}' written to '{}'".format(
                ", ".join(selectors), url, output
            )
    else:
        # Whole page
        if return_bytes:
            return page.screenshot(**screenshot_args)
        else:
            page.screenshot(**screenshot_args)
            message = "Screenshot of '{}' written to '{}'".format(url, output)
    click.echo(message, err=True)


def _selector_javascript(selectors, padding=0):
    selector_to_shoot = "shot-scraper-{}".format(secrets.token_hex(8))
    selector_javascript = textwrap.dedent(
        """
    new Promise(takeShot => {
        let padding = %s;
        let minTop = 100000000;
        let minLeft = 100000000;
        let maxBottom = 0;
        let maxRight = 0;
        let els = %s.map(s => document.querySelector(s));
        els.forEach(el => {
            let rect = el.getBoundingClientRect();
            if (rect.top < minTop) {
                minTop = rect.top;
            }
            if (rect.left < minLeft) {
                minLeft = rect.left;
            }
            if (rect.bottom > maxBottom) {
                maxBottom = rect.bottom;
            }
            if (rect.right > maxRight) {
                maxRight = rect.right;
            }
        });
        // Adjust them based on scroll position
        let top = minTop + window.scrollY;
        let bottom = maxBottom + window.scrollY;
        let left = minLeft + window.scrollX;
        let right = maxRight + window.scrollX;
        // Apply padding
        top = top - padding;
        bottom = bottom + padding;
        left = left - padding;
        right = right + padding;
        let div = document.createElement('div');
        div.style.position = 'absolute';
        div.style.top = top + 'px';
        div.style.left = left + 'px';
        div.style.width = (right - left) + 'px';
        div.style.height = (bottom - top) + 'px';
        div.setAttribute('id', %s);
        document.body.appendChild(div);
        setTimeout(() => {
            takeShot();
        }, 300);
    });
    """
        % (padding, json.dumps(selectors), json.dumps(selector_to_shoot))
    )
    return selector_javascript, "#" + selector_to_shoot


def _evaluate_js(page, javascript):
    try:
        return page.evaluate(javascript)
    except Error as error:
        raise click.ClickException(error.message)
