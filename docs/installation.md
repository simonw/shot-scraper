(installation)=

# Installation

Install this tool using `pip`:
```bash
pip install shot-scraper
```
This tool depends on Playwright, which first needs to install its own dedicated Chromium browser.

Run `shot-scraper install` once to install that:
```bash
shot-scraper install
```
Which outputs:
```
Downloading Playwright build of chromium v965416 - 117.2 Mb [====================] 100% 0.0s 
Playwright build of chromium v965416 downloaded to /Users/simon/Library/Caches/ms-playwright/chromium-965416
Downloading Playwright build of ffmpeg v1007 - 1.1 Mb [====================] 100% 0.0s 
Playwright build of ffmpeg v1007 downloaded to /Users/simon/Library/Caches/ms-playwright/ffmpeg-1007
```
If you want to use other browsers such as Firefox you should install those too:
```bash
shot-scraper install -b firefox
```

## `shot-scraper install --help`

Full `--help` for the `shot-scraper install` command:
<!-- [[[cog
import cog
from shot_scraper import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["install", "--help"])
help = result.output.replace("Usage: cli", "Usage: shot-scraper")
cog.out(
    "```\n{}\n```\n".format(help.strip())
)
]]] -->
```
Usage: shot-scraper install [OPTIONS]

  Install the Playwright browser needed by this tool.

  Usage:

      shot-scraper install

  Or for browsers other than the Chromium default:

      shot-scraper install -b firefox

Options:
  -b, --browser [chromium|firefox|webkit|chrome|chrome-beta]
                                  Which browser to install
  --help                          Show this message and exit.
```
<!-- [[[end]]] -->
