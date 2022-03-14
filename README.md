# shot-scraper

[![PyPI](https://img.shields.io/pypi/v/shot-scraper.svg)](https://pypi.org/project/shot-scraper/)
[![Changelog](https://img.shields.io/github/v/release/simonw/shot-scraper?include_prereleases&label=changelog)](https://github.com/simonw/shot-scraper/releases)
[![Tests](https://github.com/simonw/shot-scraper/workflows/Test/badge.svg)](https://github.com/simonw/shot-scraper/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/shot-scraper/blob/master/LICENSE)

Tools for taking automated screenshots of websites

For background on this project see [shot-scraper: automated screenshots for documentation, built on Playwright](https://simonwillison.net/2022/Mar/10/shot-scraper/).

## Quickstart

To get started without installing any software, use the [shot-scraper-template](https://github.com/simonw/shot-scraper-template) template to create your own GitHub repository which takes screenshots of a page using `shot-scraper`. See [Instantly create a GitHub repository to take screenshots of a web page](https://simonwillison.net/2022/Mar/14/shot-scraper-template/) for details.

## Demos

- The [shot-scraper-demo](https://github.com/simonw/shot-scraper-demo) repository uses this tool to capture recently spotted owls in El Granada, CA according to [this page](https://www.owlsnearme.com/?place=127871), and to  generate an annotated screenshot illustrating a Datasette feature as described [in my blog](https://simonwillison.net/2022/Mar/10/shot-scraper/#a-complex-example).
- Ben Welsh built [@newshomepages](https://twitter.com/newshomepages), a Twitter bot that uses `shot-scraper` and GitHub Actions to take screenshots of news website homepages and publish them to Twitter. The code for that lives in [palewire/news-homepages](https://github.com/palewire/news-homepages).
- [scrape-hacker-news-by-domain](https://github.com/simonw/scrape-hacker-news-by-domain) uses `shot-scraper javascript` to scrape a web page. See [Scraping web pages from the command-line with shot-scraper](https://simonwillison.net/2022/Mar/14/scraping-web-pages-shot-scraper/) for details of how this works.

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

To take a screenshot of a web page and write it to `datasette-io.png` run this:

    shot-scraper https://datasette.io/

If a file called `datasette-io.png` already exists the filename `datasette-io.1.png` will be used instead.

You can use the `-o` option to specify a filename:

    shot-scraper https://datasette.io/ -o datasette.png

Use `-o -` to write the PNG image to standard output:

    shot-scraper https://datasette.io/ -o - > datasette.png

If you omit the protocol `http://` will be added automatically, and any redirects will be followed:

    shot-scraper datasette.io -o datasette.png

### Adjusting the browser width and height

The browser window used to take the screenshots defaults to 1280px wide and 780px tall.

You can adjust these with the `--width` and `--height` options:

    shot-scraper https://datasette.io/ -o small.png --width 400 --height 800

If you provide both options, the resulting screenshot will be of that size. If you omit `--height` a full page length screenshot will be produced (the default).

### Screenshotting a specific area with CSS selectors

To take a screenshot of a specific element on the page, use `--selector` or `-s` with its CSS selector:

    shot-scraper https://simonwillison.net/ -s '#bighead'

When using `--selector` the height and width, if provided, will set the size of the browser window when the page is loaded but the resulting screenshot will still be the same dimensions as the element on the page.

You can pass `--selector` multiple times. The resulting screenshot will cover the smallest area of the page that contains all of the elements you specified, for example:

    shot-scraper https://simonwillison.net/ \
      -s '#bighead' -s .overband \
      -o bighead-multi-selector.png

You can add `--padding 20` to add 20px of padding around the elements when the shot is taken.

### Adding a delay

Sometimes a page will not have completely loaded before a screenshot is taken. You can use `--wait X` to wait the specified number of milliseconds after the page load event has fired before taking the screenshot:

    shot-scraper https://simonwillison.net/ --wait 2000

### Executing custom JavaScript

You can use custom JavaScript to modify the page after it has loaded (after the 'onload' event has fired) but before the screenshot is taken using the `--javascript` option:

    shot-scraper https://simonwillison.net/ \
      -o simonwillison-pink.png \
      --javascript "document.body.style.backgroundColor = 'pink';"

### Using JPEGs instead of PNGs

Screenshots default to PNG. You can save as a JPEG by specifying a `-o` filename that ends with `.jpg`.

You can also use `--quality X` to save as a JPEG with the specified quality, in order to reduce the filesize. 80 is a good value to use here:

    shot-scraper https://simonwillison.net/ \
      -h 800 -o simonwillison.jpg --quality 80
    % ls -lah simonwillison.jpg
    -rw-r--r--@ 1 simon  staff   168K Mar  9 13:53 simonwillison.jpg

### Retina images

The `--retina` option sets a device scale factor of 2. This means that an image will have its resolution effectively doubled, emulating the display of images on [retina](https://en.wikipedia.org/wiki/Retina_display) or higher pixel density screens.

    shot-scraper https://simonwillison.net/ -o simon.png \
      --width 400 --height 600 --retina

This example will produce an image that is 800px wide and 1200px high.

### Interacting with the page

Sometimes it's useful to be able to manually interact with a page before the screenshot is captured.

Add the `--interactive` option to open a browser window that you can interact with. Then hit `<enter>` in the terminal when you are ready to take the shot and close the window.

    shot-scraper https://simonwillison.net/ -o after-interaction.png \
      --height 800 --interactive

This will output:

    Hit <enter> to take the shot and close the browser window:
      # And after you hit <enter>...
    Screenshot of 'https://simonwillison.net/' written to 'after-interaction.png'

### Taking screenshots of local HTML files

You can pass the path to an HTML file on disk to take a screenshot of that rendered file:

    shot-scraper index.html -o index.png

CSS and images referenced from that file using relative paths will also be included.

### shot-scraper shot --help

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

      shot-scraper www.example.com

  This will write the screenshot to www-example-com.png

  Use "-o" to write to a specific file:

      shot-scraper https://www.example.com/ -o example.png

  You can also pass a path to a local file on disk:

      shot-scraper index.html -o index.png

  Using "-o -" will output to standard out:

      shot-scraper https://www.example.com/ -o - > example.png

  Use -s to take a screenshot of one area of the page, identified using one or
  more CSS selectors:

      shot-scraper https://simonwillison.net -s '#bighead'

Options:
  -a, --auth FILENAME    Path to JSON authentication context file
  -w, --width INTEGER    Width of browser window, defaults to 1280
  -h, --height INTEGER   Height of browser window and shot - defaults to the
                         full height of the page
  -o, --output FILE
  -s, --selector TEXT    Take shot of first element matching this CSS selector
  -p, --padding INTEGER  When using selectors, add this much padding in pixels
  -j, --javascript TEXT  Execute this JS prior to taking the shot
  --retina               Use device scale factor of 2
  --quality INTEGER      Save as JPEG with this quality, e.g. 80
  --wait INTEGER         Wait this many milliseconds before taking the
                         screenshot
  -i, --interactive      Interact with the page in a browser before taking the
                         shot
  --devtools             Interact mode with developer tools
  --help                 Show this message and exit.
```
<!-- [[[end]]] -->

## Websites that need authentication

If you want to take screnshots of a site that has some form of authentication, you will first need to authenticate with that website manually.

You can do that using the `shot-scraper auth` command:

    shot-scraper auth https://datasette-auth-passwords-demo.datasette.io/-/login auth.json

(For this demo, use username = `root` and password = `password!`)

This will open a browser window on your computer showing the page you specified.

You can then sign in using that browser window - including 2FA or CAPTCHAs or other more complex form of authentication.

When you are finished, hit `<enter>` at the `shot-scraper` command-line prompt. The browser will close and the authentication credentials (usually cookies) for that browser session will be written out to the `auth.json` file.

To take authenticated screenshots you can then use the `-a` or `--auth` options to point to the JSON file that you created:

    shot-scraper https://datasette-auth-passwords-demo.datasette.io/ \
      -a auth.json -o authed.png

## Taking multiple screenshots

You can configure multiple screenshots using a YAML file. Create a file called `shots.yml` that looks like this:

```yaml
  url: http://www.example.com/
- output: w3c.org.png
  url: https://www.w3.org/
```
Then run the tool like so:

    shot-scraper multi shots.yml

This will create two image files, `www-example-com.png` and `w3c.org.png`, containing screenshots of those two URLs.

You can set `url:` to a path to a file on disk as well:

```yaml
- output: index.png
  url: index.html
```

Use `--retina` to take all screenshots at retina resolution instead, doubling the dimensions of the files:

    shot-scraper multi shots.yml --retina

To take a screenshot of just the area of a page defined by a CSS selector, add `selector` to the YAML block:

```yaml
- output: bighead.png
  url: https://simonwillison.net/
  selector: "#bighead"
```

You can pass more than one selector using a `selectors:` list. You can also use `padding:` to specify additional padding:
```yaml
- output: bighead-multi-selector.png
  url: https://simonwillison.net/
  selectors:
  - "#bighead"
  - .overband
  padding: 20
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
  -a, --auth FILENAME  Path to JSON authentication context file
  --retina             Use device scale factor of 2
  -h, --help           Show this message and exit.
```
<!-- [[[end]]] -->

## Saving a web page to PDF

The `shot-scraper pdf` command saves a PDF version of a web page - the equivalent of using `Print -> Save to PDF` in Chromium.

    shot-scraper pdf https://datasette.io/

This will save to `datasette-io.pdf`. You can use `-o` to specify a filename:

    shot-scraper pdf https://datasette.io/tutorials/learn-sql \
      -o learn-sql.pdf

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

      shot-scraper pdf https://datasette.io/

  Use -o to specify a filename:

      shot-scarper pdf https://datasette.io/ -o datasette.pdf

Options:
  -a, --auth FILENAME    Path to JSON authentication context file
  -o, --output FILE
  -j, --javascript TEXT  Execute this JS prior to creating the PDF
  --wait INTEGER         Wait this many milliseconds before taking the
                         screenshot
  --media-screen         Use screen rather than print styles
  --landscape            Use landscape orientation
  -h, --help             Show this message and exit.
```
<!-- [[[end]]] -->

## Scraping pages using JavaScript

The `shot-scraper javascript` command can be used to execute JavaScript directly against a page and return the result as JSON.

This command doesn't produce a screenshot, but has interesting applications for scraping.

To retrieve a string title of a document:

    shot-scraper javascript https://datasette.io/ "document.title"

This returns a JSON string:
```json
"Datasette: An open source multi-tool for exploring and publishing data"
```
To return a JSON object, wrap an object literal in parenthesis:

    shot-scraper javascript https://datasette.io/ "({
      title: document.title,
      tagline: document.querySelector('.tagline').innerText
    })"

This returns:
```json
{
  "title": "Datasette: An open source multi-tool for exploring and publishing data",
  "tagline": "An open source multi-tool for exploring and publishing data"
}
```
To use functions such as `setInterval()`, for example if you need to delay the shot for a second to allow an animation to finish running, return a promise:

    shot-scraper javascript datasette.io "
    new Promise(done => setInterval(
      () => {
        done({
          title: document.title,
          tagline: document.querySelector('.tagline').innerText
        });
      }, 1000
    ));"

You can also save JavaScript to a file and execute it like this:

    shot-scraper javascript datasette.io -i script.js

Or read it from standard input like this:

    echo "document.title" | shot-scraper javascript datasette.io

### Handling JavaScript errors

If a JavaScript error occurs, a stack trace will be written to standard error and the tool will terminate with an exit code of 1.

This can be used to run JavaScript tests in continuous integration environments, by taking advantage of the `throw "error message"` JavaScript statement.

This example [uses GitHub Actions](https://docs.github.com/en/actions/quickstart):

```yaml
- name: Test page title
  run: |-
    shot-scraper javascript datasette.io "
      if (document.title != 'Datasette') {
        throw 'Wrong title detected';
      }"
```

Full `--help` for this command:

<!-- [[[cog
result = runner.invoke(cli.cli, ["javascript", "--help"])
help = result.output.replace("Usage: cli", "Usage: shot-scraper")
cog.out(
    "```\n{}\n```\n".format(help.strip())
)
]]] -->
```
Usage: shot-scraper javascript [OPTIONS] URL [JAVASCRIPT]

  Execute JavaScript against the page and return the result as JSON

  Usage:

      shot-scraper javascript https://datasette.io/ "document.title"

  To return a JSON object, use this:

      "({title: document.title, location: document.location})"

  To use setInterval() or similar, pass a promise:

      "new Promise(done => setInterval(
        () => {
          done({
            title: document.title,
            h2: document.querySelector('h2').innerHTML
          });
        }, 1000
      ));"

  If a JavaScript error occurs an exit code of 1 will be returned.

Options:
  -i, --input FILENAME   Read input JavaScript from this file
  -a, --auth FILENAME    Path to JSON authentication context file
  -o, --output FILENAME  Save output JSON to this file
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
  -a, --auth FILENAME    Path to JSON authentication context file
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

Some of the tests exercise the CLI utility directly. Run those like so:

    tests/run_examples.sh
