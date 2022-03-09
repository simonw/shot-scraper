# shot-scraper

[![PyPI](https://img.shields.io/pypi/v/shot-scraper.svg)](https://pypi.org/project/shot-scraper/)
[![Changelog](https://img.shields.io/github/v/release/simonw/shot-scraper?include_prereleases&label=changelog)](https://github.com/simonw/shot-scraper/releases)
[![Tests](https://github.com/simonw/shot-scraper/workflows/Test/badge.svg)](https://github.com/simonw/shot-scraper/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/shot-scraper/blob/master/LICENSE)

Tool for taking automated screenshots

## Demo

A live demo of the output of this tool can be found in the [shot-scraper-demo](https://github.com/simonw/shot-scraper-demo) repository.

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

## Taking multiple screenshot

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
