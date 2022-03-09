import click
from click_default_group import DefaultGroup
from playwright.sync_api import sync_playwright
from runpy import run_module
import sys
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
@click.option(
    "-j", "--javascript", help="Execute this JavaScript prior to taking the shot"
)
def shot(url, output, width, height, selector, javascript):
    """
        Take a single screenshot of a page or portion of a page.

        Usage:

            shot-scraper http://www.example.com/ -o example.png
    .
        Use -s to take a screenshot of one area of the page, identified
        using a CSS selector:

            shot-scraper https://simonwillison.net -o bighead.png -s '#bighead'
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        if output == "-":
            shot = take_shot(
                browser,
                {
                    "url": url,
                    "selector": selector,
                    "javascript": javascript,
                    "width": width,
                    "height": height,
                },
                selector=selector,
                return_bytes=True,
            )
            sys.stdout.buffer.write(shot)
        else:
            shot = take_shot(
                browser,
                {
                    "url": url,
                    "output": str(output),
                    "selector": selector,
                    "javascript": javascript,
                    "width": width,
                    "height": height,
                },
            )
        browser.close()


@cli.command()
@click.argument("config", type=click.File(mode="r"))
def multi(config):
    """
    Take multiple screenshots, defined by a YAML file

    Usage:

        shot-scraper config.yml

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
    message = ""
    selector = shot.get("selector")
    javascript = shot.get("javascript")
    if javascript:
        page.evaluate(javascript)
    if selector:
        if return_bytes:
            return page.locator(selector).screenshot()
        else:
            page.locator(selector).screenshot(path=output)
            message = "Screenshot of '{}' on '{}' written to '{}'".format(
                selector, url, output
            )
    else:
        # Whole page
        if return_bytes:
            return page.screenshot(full_page=full_page)
        else:
            page.screenshot(path=output, full_page=full_page)
            message = "Screenshot of '{}' written to '{}'".format(url, output)
    click.echo(message, err=True)
