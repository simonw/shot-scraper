import click
from click_default_group import DefaultGroup
import json
import pathlib
from playwright.sync_api import sync_playwright
from runpy import run_module
import secrets
import sys
import textwrap
import time
import yaml


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
    default="-",
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
@click.option("--quality", type=int, help="Save as JPEG with this quality, e.g. 80")
@click.option(
    "--wait", type=int, help="Wait this many milliseconds before taking the screenshot"
)
@click.option(
    "-i",
    "--interactive",
    is_flag=True,
    help="Interact with the page in a browser before taking the shot",
)
def shot(
    url,
    auth,
    output,
    width,
    height,
    selectors,
    padding,
    javascript,
    quality,
    wait,
    interactive,
):
    """
    Take a single screenshot of a page or portion of a page.

    Usage:

        shot-scraper http://www.example.com/ -o example.png

    Use -s to take a screenshot of one area of the page, identified using a CSS selector:

        shot-scraper https://simonwillison.net -o bighead.png -s '#bighead'
    """
    shot = {
        "url": url,
        "selectors": selectors,
        "javascript": javascript,
        "width": width,
        "height": height,
        "quality": quality,
        "wait": wait,
        "padding": padding,
    }
    with sync_playwright() as p:
        use_existing_page = False
        context, browser = _browser_context(p, auth, headless=not interactive)
        if interactive:
            use_existing_page = True
            page = context.new_page()
            page.goto(url)
            context = page
            click.echo("Hit <enter> to take the shot and close the browser window:", err=True)
            input()
        if output == "-":
            shot = take_shot(
                context, shot, return_bytes=True, use_existing_page=use_existing_page
            )
            sys.stdout.buffer.write(shot)
        else:
            shot["output"] = str(output)
            shot = take_shot(context, shot, use_existing_page=use_existing_page)
        browser.close()


def _browser_context(p, auth, headless=True):
    browser = p.chromium.launch(headless=headless)
    if auth:
        context = browser.new_context(storage_state=json.load(auth))
    else:
        context = browser.new_context()
    return context, browser


@cli.command()
@click.argument("config", type=click.File(mode="r"))
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
def multi(config, auth):
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
    with sync_playwright() as p:
        context, browser = _browser_context(p, auth)
        for shot in shots:
            take_shot(context, shot)
        browser.close()


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
    with sync_playwright() as p:
        context, browser = _browser_context(p, auth)
        page = context.new_page()
        page.goto(url)
        if javascript:
            page.evaluate(javascript)
        snapshot = page.accessibility.snapshot()
        browser.close()
    output.write(json.dumps(snapshot, indent=4))
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
    default="-",
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

        shot-scraper pdf https://datasette.io/ -o datasette.pdf
    """
    with sync_playwright() as p:
        context, browser = _browser_context(p, auth)
        page = context.new_page()
        page.goto(url)
        if wait:
            time.sleep(wait / 1000)
        if javascript:
            page.evaluate(javascript)

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

        browser.close()


@cli.command()
def install():
    """
    Install Playwright browser needed by this tool.

    Usage:

        shot-scraper install
    """
    sys.argv = ["playwright", "install", "chromium"]
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


def take_shot(context_or_page, shot, return_bytes=False, use_existing_page=False):
    url = shot.get("url") or ""
    if not (url.startswith("http://") or url.startswith("https://")):
        raise click.ClickException(
            "'url' must start http:// or https:// - got:  \n{}".format(url)
        )
    output = shot.get("output", "").strip()
    if not output and not return_bytes:
        raise click.ClickException(
            "'output' filename is required, messing for url:\n  {}".format(url)
        )
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

    if not use_existing_page:
        page.goto(url)

    if wait:
        time.sleep(wait / 1000)
    message = ""
    javascript = shot.get("javascript")
    if javascript:
        page.evaluate(javascript)

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
        page.evaluate(selector_javascript)
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
