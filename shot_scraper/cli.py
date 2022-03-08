import click
import subprocess
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
    for shot in shots:
        take_shot(shot)


def take_shot(shot):
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
    # Capture the screenshot with puppeteer
    subprocess.run(
        [
            "npx",
            "playwright",
            "screenshot",
            "--full-page",
            url,
            output,
        ],
        capture_output=True,
    )
    click.echo("Screenshot of '{}' written to '{}'".format(url, output))
