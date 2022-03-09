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
    "-o",
    "--output",
    type=click.Path(file_okay=True, writable=True, dir_okay=False, allow_dash=True),
    default="-",
)
def shot(url, output):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        if output == "-":
            shot = take_shot(
                browser,
                {
                    "url": url,
                },
                return_bytes=True,
            )
            sys.stdout.buffer.write(shot)
        else:
            shot = take_shot(
                browser,
                {
                    "url": url,
                    "output": str(output),
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
    page.goto(url)
    if return_bytes:
        return page.screenshot(full_page=True)
    else:
        page.screenshot(path=output, full_page=True)
    click.echo("Screenshot of '{}' written to '{}'".format(url, output))
