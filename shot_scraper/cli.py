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

BROWSERS = ("chromium", "firefox", "webkit", "chrome", "chrome-beta")


def browser_option(fn):
    click.option(
        "--browser",
        "-b",
        default="chromium",
        type=click.Choice(BROWSERS, case_sensitive=False),
        help="Which browser to use",
    )(fn)
    return fn


def user_agent_option(fn):
    click.option("--user-agent", help="User-Agent header to use")(fn)
    return fn


def reduced_motion_option(fn):
    click.option(
        "--reduced-motion",
        is_flag=True,
        help="Emulate 'prefers-reduced-motion' media feature",
    )(fn)
    return fn


@click.group(
    cls=DefaultGroup,
    default="shot",
    default_if_no_args=True,
    context_settings=dict(help_option_names=["--help"]),
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
    "selectors_all",
    "--selector-all",
    help="Take shot of all elements matching this CSS selector",
    multiple=True,
)
@click.option(
    "js_selectors",
    "--js-selector",
    help="Take shot of first element matching this JS (el) expression",
    multiple=True,
)
@click.option(
    "js_selectors_all",
    "--js-selector-all",
    help="Take shot of all elements matching this JS (el) expression",
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
@click.option("--wait-for", help="Wait until this JS expression returns true")
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
@click.option(
    "--log-requests",
    type=click.File("w"),
    help="Log details of all requests to this file",
)
@browser_option
@user_agent_option
@reduced_motion_option
def shot(
    url,
    auth,
    output,
    width,
    height,
    selectors,
    selectors_all,
    js_selectors,
    js_selectors_all,
    padding,
    javascript,
    retina,
    quality,
    wait,
    wait_for,
    timeout,
    interactive,
    devtools,
    log_requests,
    browser,
    user_agent,
    reduced_motion,
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
        ext = "jpg" if quality else None
        output = filename_for_url(url, ext=ext, file_exists=os.path.exists)
    shot = {
        "url": url,
        "selectors": selectors,
        "selectors_all": selectors_all,
        "js_selectors": js_selectors,
        "js_selectors_all": js_selectors_all,
        "javascript": javascript,
        "width": width,
        "height": height,
        "quality": quality,
        "wait": wait,
        "wait_for": wait_for,
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
            user_agent=user_agent,
            timeout=timeout,
            reduced_motion=reduced_motion,
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
                    log_requests=log_requests,
                )
                sys.stdout.buffer.write(shot)
            else:
                shot["output"] = str(output)
                shot = take_shot(
                    context,
                    shot,
                    use_existing_page=use_existing_page,
                    log_requests=log_requests,
                )
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
    user_agent=None,
    timeout=None,
    reduced_motion=False,
):
    browser_kwargs = dict(headless=not interactive, devtools=devtools)
    if browser == "chromium":
        browser_obj = p.chromium.launch(**browser_kwargs)
    elif browser == "firefox":
        browser_obj = p.firefox.launch(**browser_kwargs)
    elif browser == "webkit":
        browser_obj = p.webkit.launch(**browser_kwargs)
    else:
        browser_kwargs["channel"] = browser
        browser_obj = p.chromium.launch(**browser_kwargs)
    context_args = {}
    if auth:
        context_args["storage_state"] = json.load(auth)
    if retina:
        context_args["device_scale_factor"] = 2
    if reduced_motion:
        context_args["reduced_motion"] = "reduce"
    if user_agent is not None:
        context_args["user_agent"] = user_agent
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
@click.option(
    "noclobber",
    "-n",
    "--no-clobber",
    is_flag=True,
    help="Skip images that already exist",
)
@click.option(
    "outputs",
    "-o",
    "--output",
    help="Just take shots matching these output files",
    multiple=True,
)
@browser_option
@user_agent_option
@reduced_motion_option
def multi(
    config,
    auth,
    retina,
    timeout,
    fail_on_error,
    noclobber,
    outputs,
    browser,
    user_agent,
    reduced_motion,
):
    """
    Take multiple screenshots, defined by a YAML file

    Usage:

        shot-scraper multi config.yml

    Where config.yml contains configuration like this:

    \b
        - output: example.png
          url: http://www.example.com/

    https://shot-scraper.datasette.io/en/stable/multi.html
    """
    shots = yaml.safe_load(config)
    if shots is None:
        shots = []
    if not isinstance(shots, list):
        raise click.ClickException("YAML file must contain a list")
    with sync_playwright() as p:
        context, browser_obj = _browser_context(
            p,
            auth,
            retina=retina,
            browser=browser,
            user_agent=user_agent,
            timeout=timeout,
            reduced_motion=reduced_motion,
        )
        for shot in shots:
            if (
                noclobber
                and shot.get("output")
                and pathlib.Path(shot["output"]).exists()
            ):
                continue
            if outputs and shot.get("output") not in outputs:
                continue
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
@click.option(
    "--timeout",
    type=int,
    help="Wait this many milliseconds before failing",
)
def accessibility(url, auth, output, javascript, timeout):
    """
    Dump the Chromium accessibility tree for the specifed page

    Usage:

        shot-scraper accessibility https://datasette.io/
    """
    url = url_or_file_path(url, _check_and_absolutize)
    with sync_playwright() as p:
        context, browser_obj = _browser_context(p, auth, timeout=timeout)
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
@user_agent_option
@reduced_motion_option
def javascript(
    url, javascript, input, auth, output, browser, user_agent, reduced_motion
):
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
        context, browser_obj = _browser_context(
            p,
            auth,
            browser=browser,
            user_agent=user_agent,
            reduced_motion=reduced_motion,
        )
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
@click.option(
    "--format",
    "format_",
    type=click.Choice(
        [
            "Letter",
            "Legal",
            "Tabloid",
            "Ledger",
            "A0",
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
            "A6",
        ],
        case_sensitive=False,
    ),
    help="Which standard paper size to use",
)
@click.option("--width", help="PDF width including units, e.g. 10cm")
@click.option("--height", help="PDF height including units, e.g. 10cm")
@click.option(
    "--scale",
    type=click.FloatRange(min=0.1, max=2.0),
    help="Scale of the webpage rendering",
)
@click.option("--print-background", is_flag=True, help="Print background graphics")
def pdf(
    url,
    auth,
    output,
    javascript,
    wait,
    media_screen,
    landscape,
    format_,
    width,
    height,
    scale,
    print_background,
):
    """
    Create a PDF of the specified page

    Usage:

        shot-scraper pdf https://datasette.io/

    Use -o to specify a filename:

        shot-scraper pdf https://datasette.io/ -o datasette.pdf

    You can pass a path to a file instead of a URL:

        shot-scraper pdf invoice.html -o invoice.pdf
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
            "format": format_,
            "width": width,
            "height": height,
            "scale": scale,
            "print_background": print_background,
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
@browser_option
@user_agent_option
@click.option("--devtools", is_flag=True, help="Open browser DevTools")
def auth(url, context_file, browser, user_agent, devtools):
    """
    Open a browser so user can manually authenticate with the specified site,
    then save the resulting authentication context to a file.

    Usage:

        shot-scraper auth https://github.com/ auth.json
    """
    with sync_playwright() as p:
        context, browser_obj = _browser_context(
            p,
            auth=None,
            interactive=True,
            devtools=devtools,
            browser=browser,
            user_agent=user_agent,
        )
        context = browser_obj.new_context()
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
    log_requests=None,
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
    wait_for = shot.get("wait_for")
    padding = shot.get("padding") or 0

    selectors = shot.get("selectors") or []
    selectors_all = shot.get("selectors_all") or []
    js_selectors = shot.get("js_selectors") or []
    js_selectors_all = shot.get("js_selectors_all") or []
    # If a single 'selector' append to 'selectors' array (and 'js_selectors' etc)
    if shot.get("selector"):
        selectors.append(shot["selector"])
    if shot.get("selector_all"):
        selectors_all.append(shot["selector_all"])
    if shot.get("js_selector"):
        js_selectors.append(shot["js_selector"])
    if shot.get("js_selector_all"):
        js_selectors_all.append(shot["js_selector_all"])

    if not use_existing_page:
        page = context_or_page.new_page()
        if log_requests:

            def on_response(response):
                try:
                    body = response.body()
                    size = len(body)
                except Error:
                    size = None
                log_requests.write(
                    json.dumps(
                        {
                            "method": response.request.method,
                            "url": response.url,
                            "status": response.status,
                            "size": size,
                            "timing": response.request.timing,
                        }
                    )
                    + "\n"
                )

            page.on("response", on_response)
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

    if wait_for:
        page.wait_for_function(wait_for)

    screenshot_args = {}
    if quality:
        screenshot_args.update({"quality": quality, "type": "jpeg"})
    if not return_bytes:
        screenshot_args["path"] = output

    if (
        not selectors
        and not js_selectors
        and not selectors_all
        and not js_selectors_all
    ):
        screenshot_args["full_page"] = full_page

    if js_selectors or js_selectors_all:
        # Evaluate JavaScript adding classes we can select on
        (
            js_selector_javascript,
            extra_selectors,
            extra_selectors_all,
        ) = _js_selector_javascript(js_selectors, js_selectors_all)
        selectors.extend(extra_selectors)
        selectors_all.extend(extra_selectors_all)
        _evaluate_js(page, js_selector_javascript)

    if selectors or selectors_all:
        # Use JavaScript to create a box around those elementsdef
        selector_javascript, selector_to_shoot = _selector_javascript(
            selectors, selectors_all, padding
        )
        _evaluate_js(page, selector_javascript)
        try:
            bytes_ = page.locator(selector_to_shoot).screenshot(**screenshot_args)
        except TimeoutError as e:
            raise click.ClickException(
                "Timed out while waiting for element to become available.\n\n{}".format(
                    e
                )
            )
        if return_bytes:
            return bytes_
        else:
            page.locator(selector_to_shoot).screenshot(**screenshot_args)
            message = "Screenshot of '{}' on '{}' written to '{}'".format(
                ", ".join(list(selectors) + list(selectors_all)), url, output
            )
    else:
        # Whole page
        if return_bytes:
            return page.screenshot(**screenshot_args)
        else:
            page.screenshot(**screenshot_args)
            message = "Screenshot of '{}' written to '{}'".format(url, output)
    click.echo(message, err=True)


def _js_selector_javascript(js_selectors, js_selectors_all):
    extra_selectors = []
    extra_selectors_all = []
    js_blocks = []
    for js_selector in js_selectors:
        klass = "js-selector-{}".format(secrets.token_hex(16))
        extra_selectors.append(".{}".format(klass))
        js_blocks.append(
            textwrap.dedent(
                """
        Array.from(
          document.getElementsByTagName('*')
        ).find(el => {}).classList.add("{}");
        """.format(
                    js_selector, klass
                )
            )
        )
    for js_selector_all in js_selectors_all:
        klass = "js-selector-all-{}".format(secrets.token_hex(16))
        extra_selectors_all.append(".{}".format(klass))
        js_blocks.append(
            textwrap.dedent(
                """
        Array.from(
          document.getElementsByTagName('*')
        ).filter(el => {}).forEach(el => el.classList.add("{}"));
        """.format(
                    js_selector_all, klass
                )
            )
        )
    js_selector_javascript = "() => {" + "\n".join(js_blocks) + "}"
    return js_selector_javascript, extra_selectors, extra_selectors_all


def _selector_javascript(selectors, selectors_all, padding=0):
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
        // Add the --selector-all elements
        %s.map(s => els.push(...document.querySelectorAll(s)));
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
        % (
            padding,
            json.dumps(selectors),
            json.dumps(selectors_all),
            json.dumps(selector_to_shoot),
        )
    )
    return selector_javascript, "#" + selector_to_shoot


def _evaluate_js(page, javascript):
    try:
        return page.evaluate(javascript)
    except Error as error:
        raise click.ClickException(error.message)
