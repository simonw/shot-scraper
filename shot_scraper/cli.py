import click
from click_default_group import DefaultGroup
import json
from playwright.sync_api import sync_playwright
from runpy import run_module
import sys
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
    "-s", "--selector", help="Take shot of first element matching this CSS selector"
)
@click.option("-j", "--javascript", help="Execute this JS prior to taking the shot")
@click.option("--quality", type=int, help="Save as JPEG with this quality, e.g. 80")
@click.option(
    "--wait", type=int, help="Wait this many milliseconds before taking the screenshot"
)
def shot(url, output, width, height, selector, javascript, quality, wait):
    """
    Take a single screenshot of a page or portion of a page.

    Usage:

        shot-scraper http://www.example.com/ -o example.png

    Use -s to take a screenshot of one area of the page, identified using a CSS selector:

        shot-scraper https://simonwillison.net -o bighead.png -s '#bighead'
    """
    shot = {
        "url": url,
        "selector": selector,
        "javascript": javascript,
        "width": width,
        "height": height,
        "quality": quality,
        "wait": wait,
    }
    with sync_playwright() as p:
        browser = p.chromium.launch()
        if output == "-":
            shot = take_shot(browser, shot, return_bytes=True)
            sys.stdout.buffer.write(shot)
        else:
            shot["output"] = str(output)
            shot = take_shot(browser, shot)
        browser.close()


@cli.command()
@click.argument("config", type=click.File(mode="r"))
def multi(config):
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
        browser = p.chromium.launch()
        for shot in shots:
            take_shot(browser, shot)
        browser.close()


@cli.command()
@click.argument("url")
@click.option(
    "-o",
    "--output",
    type=click.File("w"),
    default="-",
)
@click.option("-j", "--javascript", help="Execute this JS prior to taking the snapshot")
def accessibility(url, output, javascript):
    """
    Dump the Chromium accessibility tree for the specifed page

    Usage:

        shot-scraper accessibility https://datasette.io/
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
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
def pdf(url, output, javascript, wait, media_screen, landscape):
    """
    Create a PDF of the specified page

    Usage:

        shot-scraper pdf https://datasette.io/ -o datasette.pdf
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
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


def take_shot(browser, shot, return_bytes=False):
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

    page = browser.new_page()

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
    message = ""
    selector = shot.get("selector")
    javascript = shot.get("javascript")
    if javascript:
        page.evaluate(javascript)

    screenshot_args = {}
    if quality:
        screenshot_args.update({"quality": quality, "type": "jpeg"})
    if not return_bytes:
        screenshot_args["path"] = output

    if not selector:
        screenshot_args["full_page"] = full_page

    if selector:
        if return_bytes:
            return page.locator(selector).screenshot(**screenshot_args)
        else:
            page.locator(selector).screenshot(**screenshot_args)
            message = "Screenshot of '{}' on '{}' written to '{}'".format(
                selector, url, output
            )
    else:
        # Whole page
        if return_bytes:
            return page.screenshot(**screenshot_args)
        else:
            page.screenshot(**screenshot_args)
            message = "Screenshot of '{}' written to '{}'".format(url, output)
    click.echo(message, err=True)
