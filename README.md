# shot-scraper

[![PyPI](https://img.shields.io/pypi/v/shot-scraper.svg)](https://pypi.org/project/shot-scraper/)
[![Changelog](https://img.shields.io/github/v/release/simonw/shot-scraper?include_prereleases&label=changelog)](https://github.com/simonw/shot-scraper/releases)
[![Tests](https://github.com/simonw/shot-scraper/workflows/Test/badge.svg)](https://github.com/simonw/shot-scraper/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/shot-scraper/blob/master/LICENSE)

Tool for taking automated screenshots

For background on this project see [shot-scraper: automated screenshots for documentation, built on Playwright](https://simonwillison.net/2022/Mar/10/shot-scraper/).

## Demos

- The [shot-scraper-demo](https://github.com/simonw/shot-scraper-demo) repository uses this tool to capture recently spotted owls in El Granada, CA according to [this page](https://www.owlsnearme.com/?place=127871), and to  generate an annotated screenshot illustrating a Datasette feature as described [in my blog](https://simonwillison.net/2022/Mar/10/shot-scraper/#a-complex-example).
- Ben Welsh built [@newshomepages](https://twitter.com/newshomepages), a Twitter bot that uses `shot-scraper` and GitHub Actions to take screenshots of news website homepages and publish them to Twitter. The code for that lives in [palewire/news-homepages](https://github.com/palewire/news-homepages).


## Installation

Install this tool using `pip`:

    pip install shot-scraper

This tool depends on Playwright, which first needs to install its own dedicated browser.

Run `shot-scraper install` once to install that:
```
% shot-scraper install
Downloading Playwright build of chromium v965416 - 117.2 Mb [====================] 100% 0.0s 
Playwright build of chromium v965416 downloaded to /Users/simon/Library/Caches/ms-playwright/chromium-965416
Downloading Playwright build of ffmpeg v1007 - 1.1 Mb [====================] 100% 0.0s 
Playwright build of ffmpeg v1007 downloaded to /Users/simon/Library/Caches/ms-playwright/ffmpeg-1007
```
## Taking a screenshot

To take a screenshot of a web page and write it to `screenshot.png` run this:

    shot-scraper https://datasette.io/ -o screenshot.png

If you omit the `-o` the screenshot PNG binary will be output by the tool, so you can pipe it or redirect it to a file:

    shot-scraper https://datasette.io/ > datasette.png

The browser window used to take the screenshots defaults to 1280px wide and 780px tall.

You can adjust these with the `--width` and `--height` options:

    shot-scraper https://datasette.io/ -o small.png --width 400 --height 800

If you provide both options, the resulting screenshot will be of that size. If you omit `--height` a full page length screenshot will be produced (the default).

To take a screenshot of a specific element on the page, use `--selector` or `-s` with its CSS selector:

    shot-scraper https://simonwillison.net/ -s '#bighead' -o bighead.png

When using `--selector` the height and width, if provided, will set the size of the browser window when the page is loaded but the resulting screenshot will still be the same dimensions as the element on the page.

Sometimes a page will not have completely loaded before a screenshot is taken. You can use `--wait X` to wait the specified number of milliseconds after the page load event has fired before taking the screenshot:

    shot-scraper https://simonwillison.net/ --wait 2000 -o after-wait.png

You can use custom JavaScript to modify the page after it has loaded (after the 'onload' event has fired) but before the screenshot is taken using the `--javascript` option:

    shot-scraper https://simonwillison.net/ -o simonwillison-pink.png \
      --javascript "document.body.style.backgroundColor = 'pink';"

Screenshots default to PNG. You can save as a JPEG by specifying a `-o` filename that ends with `.jpg`.

You can also use `--quality X` to save as a JPEG with the specified quality, in order to reduce the filesize. 80 is a good value to use here:

    shot-scraper https://simonwillison.net/ \
      -h 800 -o simonwillison.jpg --quality 80
    % ls -lah simonwillison.jpg
    -rw-r--r--@ 1 simon  staff   168K Mar  9 13:53 simonwillison.jpg

Full `--help` for this command:

<!-- [[[cog
import cog
from shot_scraper import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["shot", "--help"])
help = result.output.replace("Usage: cli", "Usage: shot-scraper")
cog.out(
    "```\n{}\n```\n".format(help.strip())
)
]]] -->
```
Usage: shot-scraper shot [OPTIONS] URL

  Take a single screenshot of a page or portion of a page.

  Usage:

      shot-scraper http://www.example.com/ -o example.png

  Use -s to take a screenshot of one area of the page, identified using a CSS
  selector:

      shot-scraper https://simonwillison.net -o bighead.png -s '#bighead'

Options:
  -w, --width INTEGER    Width of browser window, defaults to 1280
  -h, --height INTEGER   Height of browser window and shot - defaults to the
                         full height of the page
  -o, --output FILE
  -s, --selector TEXT    Take shot of first element matching this CSS selector
  -j, --javascript TEXT  Execute this JS prior to taking the shot
  --quality INTEGER      Save as JPEG with this quality, e.g. 80
  --wait INTEGER         Wait this many milliseconds before taking the
                         screenshot
  --help                 Show this message and exit.
```
<!-- [[[end]]] -->

## Taking multiple screenshots

You can configure multiple screenshots using a YAML file. Create a file called `shots.yml` that looks like this:

```yaml
- output: example.com.png
  url: http://www.example.com/
- output: w3c.org.png
  url: https://www.w3.org/
```
Then run the tool like so:

    shot-scraper multi shots.yml

This will create two image files, `example.com.png` and `w3c.org.png`, containing screenshots of those two URLs.

To take a screenshot of just the area of a page defined by a CSS selector, add `selector` to the YAML block:

```yaml
- output: bighead.png
  url: https://simonwillison.net/
  selector: "#bighead"
```
To execute JavaScript after the page has loaded but before the screenshot is taken, add a `javascript` key:
```yaml
- output: bighead-pink.png
  url: https://simonwillison.net/
  selector: "#bighead"
  javascript: |
    document.body.style.backgroundColor = 'pink'
```

You can include desired `height`, `width`, `quality` and `wait` options on each item as well:

```yaml
- output: simon-narrow.jpg
  url: https://simonwillison.net/
  width: 400
  height: 800
  quality: 80
  wait: 500
```

Full `--help` for this command:

<!-- [[[cog
result = runner.invoke(cli.cli, ["multi", "--help"])
help = result.output.replace("Usage: cli", "Usage: shot-scraper")
cog.out(
    "```\n{}\n```\n".format(help.strip())
)
]]] -->
```
Usage: shot-scraper multi [OPTIONS] CONFIG

  Take multiple screenshots, defined by a YAML file

  Usage:

      shot-scraper multi config.yml

  Where config.yml contains configuration like this:

      - output: example.png
        url: http://www.example.com/

Options:
  -h, --help  Show this message and exit.
```
<!-- [[[end]]] -->

## Saving a webpage to PDF

The `shot-scrapr pdf` command saves a PDF version of a web page - the equivalent of using `Print -> Save to PDF` in Chromium.

    shot-scraper pdf https://datasette.io/ -o datasette.pdf

Full `--help` for this command:

<!-- [[[cog
result = runner.invoke(cli.cli, ["pdf", "--help"])
help = result.output.replace("Usage: cli", "Usage: shot-scraper")
cog.out(
    "```\n{}\n```\n".format(help.strip())
)
]]] -->
```
Usage: shot-scraper pdf [OPTIONS] URL

  Create a PDF of the specified page

  Usage:

      shot-scraper pdf https://datasette.io/ -o datasette.pdf

Options:
  -o, --output FILE
  -j, --javascript TEXT  Execute this JS prior to creating the PDF
  --wait INTEGER         Wait this many milliseconds before taking the
                         screenshot
  --media-screen         Use screen rather than print styles
  --landscape            Use landscape orientation
  -h, --help             Show this message and exit.
```
<!-- [[[end]]] -->

## Dumping out an accessibility tree

The `shot-scraper accessibility` command dumps out the Chromium accessibility tree for the provided URL, as JSON:

    shot-scraper accessibility https://datasette.io/

Use `-o filename.json` to write the output to a file instead of displaying it.

Add `--javascript SCRIPT` to execute custom JavaScript before taking the snapshot.

Full `--help` for this command:

<!-- [[[cog
result = runner.invoke(cli.cli, ["accessibility", "--help"])
help = result.output.replace("Usage: cli", "Usage: shot-scraper")
cog.out(
    "```\n{}\n```\n".format(help.strip())
)
]]] -->
```
Usage: shot-scraper accessibility [OPTIONS] URL

  Dump the Chromium accessibility tree for the specifed page

  Usage:

      shot-scraper accessibility https://datasette.io/

Options:
  -o, --output FILENAME
  -j, --javascript TEXT  Execute this JS prior to taking the snapshot
  -h, --help             Show this message and exit.
```
<!-- [[[end]]] -->

## Tips for executing JavaScript

If you are using the `--javascript` option to execute code, that code will be executed after the page load event has fired but before the screenshot is taken.

You can use that code to do things like hide or remove specific page elements, click on links to open menus, or even add annotations to the page such as this [pink arrow example](https://simonwillison.net/2022/Mar/10/shot-scraper/#a-complex-example).

This code hides any element with a `[data-ad-rendered]` attribute and the element with `id="ensNotifyBanner"`:

    document.querySelectorAll(
        '[data-ad-rendered],#ensNotifyBanner'
    ).forEach(el => el.style.display = 'none')

You can execute that like so:

```
shot-scraper https://www.latimes.com/ -o latimes.png --javascript "
document.querySelectorAll(
    '[data-ad-rendered],#ensNotifyBanner'
).forEach(el => el.style.display = 'none')
"
```

In some cases you may need to add a pause that executes during your custom JavaScript before the screenshot is taken - for example if you click on a button that triggers a short fading animation.

You can do that using the following pattern:
```javascript
new Promise(takeShot => {
  // Your code goes here
  // ...
  setTimeout(() => {
    // Resolving the promise takes the shot
    takeShot();
  }, 1000);
});
```
If your custom code defines a `Promise`, `shot-scraper` will wait for that promise to complete before taking the screenshot. Here the screenshot does not occur until the `takeShot()` function is called.

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:

    cd shot-scraper
    python -m venv venv
    source venv/bin/activate

Or if you are using `pipenv`:

    pipenv shell

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
