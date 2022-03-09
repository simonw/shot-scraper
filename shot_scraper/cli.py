import click
from playwright.sync_api import sync_playwright
import yaml


@click.command()
@click.version_option()
@click.argument("config", type=click.File(mode="r"))
def cli(config):
    """
    Tool for taking automated screenshots

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


def take_shot(browser, shot):
    url = shot.get("url") or ""
    if not (url.startswith("http://") or url.startswith("https://")):
        raise click.ClickException(
            "'url' must start http:// or https:// - got:  \n{}".format(url)
        )
    output = shot.get("output", "").strip()
    if not output:
        raise click.ClickException(
            "'output' filename is required, messing for url:\n  {}".format(url)
        )
    page = browser.new_page()
    page.goto(url)
    page.screenshot(path=output, full_page=True)
    click.echo("Screenshot of '{}' written to '{}'".format(url, output))
