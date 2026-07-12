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

(installation-docker)=

## Running with Docker

The repository includes a `Dockerfile` that packages shot-scraper together with Chromium, its system libraries, `ffmpeg`, `espeak-ng` and the Kokoro narration model, so the only thing the host needs is Docker.

Build the image:
```bash
docker build -t shot-scraper .
```

Then mount a directory as `/work` for inputs and outputs. Chromium cannot use its sandbox as root inside a container, so pass `--no-sandbox` (and `--disable-dev-shm-usage`, since the default 64MB `/dev/shm` is too small) via `--browser-arg`:
```bash
docker run --rm -v "$PWD:/work" shot-scraper \
  shot https://example.com/ -o /work/example.png \
  --browser-arg --no-sandbox --browser-arg --disable-dev-shm-usage
```

Recording a {ref}`narrated video <video>` works fully offline — the Kokoro model is baked into the image:
```bash
docker run --rm -v "$PWD:/work" shot-scraper \
  video /work/storyboard.yml -o /work/demo.webm --mp4 \
  --browser-arg --no-sandbox --browser-arg --disable-dev-shm-usage
```

To reach a server running on the host's own `localhost`, add `--network host` (Linux) or point the storyboard `url:` at `http://host.docker.internal:PORT/` (Docker Desktop on macOS/Windows).

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
