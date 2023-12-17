(screenshots)=

# Taking a screenshot

To take a screenshot of a web page and write it to `datasette-io.png` run this:

    shot-scraper https://datasette.io/

If a file called `datasette-io.png` already exists the filename `datasette-io.1.png` will be used instead.

You can use the `-o` option to specify a filename:

    shot-scraper https://datasette.io/ -o datasette.png

Use `-o -` to write the PNG image to standard output:

    shot-scraper https://datasette.io/ -o - > datasette.png

If you omit the protocol `http://` will be added automatically, and any redirects will be followed:

    shot-scraper datasette.io -o datasette.png

## Adjusting the browser width and height

The browser window used to take the screenshots defaults to 1280px wide and 780px tall.

You can adjust these with the `--width` and `--height` options (`-w` and `-h` for short):

    shot-scraper https://datasette.io/ -o small.png --width 400 --height 800

If you provide both options, the resulting screenshot will be of that size. If you omit `--height` a full page length screenshot will be produced (the default).

## Screenshotting a specific area with CSS selectors

To take a screenshot of a specific element on the page, use `--selector` or `-s` with its CSS selector:

    shot-scraper https://simonwillison.net/ -s '#bighead'

This produces `simonwillison-net.png` containing this image:

<img src="https://raw.githubusercontent.com/simonw/shot-scraper-screenshot/main/shot-selector.png" alt="Just the header section from my blog">

When using `--selector` the height and width, if provided, will set the size of the browser window when the page is loaded but the resulting screenshot will still be the same dimensions as the element on the page.

You can pass `--selector` multiple times. The resulting screenshot will cover the smallest area of the page that contains all of the elements you specified, for example:

    shot-scraper https://simonwillison.net/ \
      -s '#bighead' -s .overband \
      -o bighead-multi-selector.png

To capture a rectangle around every element that matches a CSS selector, use `--selector-all`:

    shot-scraper https://simonwillison.net/ \
      --selector-all '.day' \
      -o just-the-day-boxes.png

You can add `--padding 20` to add 20px of padding around the elements when the shot is taken.

## Specifying elements using JavaScript filters

The `--js-selector` and `--js-selector-all` options can be used to use JavaScript expressions to select elements that cannot be targetted just using CSS selectors.

The options should be passed JavaScript expression that operates on the `el` variable, returning `true` if that element should be included in the screenshot selection.

To take a screenshot of the first paragraph on the page that contains the text "shot-scraper" you could run the following:

    shot-scraper https://github.com/simonw/shot-scraper \
      --js-selector 'el.tagName == "P" && el.innerText.includes("shot-scraper")'

The `el.tagName == "P"` part is needed here because otherwise the `<html>` element on the page will be the first to match the expression.

The generated JavaScript that will be executed on the page looks like this:
```javascript
Array.from(document.getElementsByTagName('*')).find(
  el => el.tagName == "P" && el.innerText.includes("shot-scraper")
).classList.add("js-selector-a1f5ba0fc4a4317e58a3bd11a0f16b96");
```
The `--js-selector-all` option will select all matching elements, in a similar fashion to the `--selector-all` option described above.

## Waiting for a delay

Sometimes a page will not have completely loaded before a screenshot is taken. You can use `--wait X` to wait the specified number of milliseconds after the page load event has fired before taking the screenshot:

    shot-scraper https://simonwillison.net/ --wait 2000

## Waiting until a specific condition

In addition to waiting a specific amount of time, you can also wait until a JavaScript expression returns true using the `--wait-for expression` option.

This example takes the screenshot the moment a `<div>` with an ID of `content` becomes available in the DOM:

    shot-scraper https://.../ \
      --wait-for 'document.querySelector("div#content")'

## Executing custom JavaScript

You can use custom JavaScript to modify the page after it has loaded (after the 'onload' event has fired) but before the screenshot is taken using the `--javascript` option:

    shot-scraper https://simonwillison.net/ \
      -o simonwillison-pink.png \
      --javascript "document.body.style.backgroundColor = 'pink';"

## Using JPEGs instead of PNGs

Screenshots default to PNG. You can save as a JPEG by specifying a `-o` filename that ends with `.jpg`.

You can also use `--quality X` to save as a JPEG with the specified quality, in order to reduce the filesize. 80 is a good value to use here:

    shot-scraper https://simonwillison.net/ \
      -h 800 -o simonwillison.jpg --quality 80
    % ls -lah simonwillison.jpg
    -rw-r--r--@ 1 simon  staff   168K Mar  9 13:53 simonwillison.jpg

## Retina images

The `--retina` option sets a device scale factor of 2. This means that an image will have its resolution effectively doubled, emulating the display of images on [retina](https://en.wikipedia.org/wiki/Retina_display) or higher pixel density screens.

    shot-scraper https://simonwillison.net/ -o simon.png \
      --width 400 --height 600 --retina

This example will produce an image that is 800px wide and 1200px high.

## Transparent background

The `--omit-background` option instructs the browser to ignore the default background, allowing for the capture of a page with a transparent background. Does not work with JPG images or when `quality` is set.

    shot-scraper https://simonwillison.net/ -o simon.png \
      --width 400 --height 600 --omit-background

## Interacting with the page

Sometimes it's useful to be able to manually interact with a page before the screenshot is captured.

Add the `--interactive` option to open a browser window that you can interact with. Then hit `<enter>` in the terminal when you are ready to take the shot and close the window.

    shot-scraper https://simonwillison.net/ -o after-interaction.png \
      --height 800 --interactive

This will output:

    Hit <enter> to take the shot and close the browser window:
      # And after you hit <enter>...
    Screenshot of 'https://simonwillison.net/' written to 'after-interaction.png'

## Logging all requests

It can sometimes be useful to see a list of all of the requests that the browser made while it was rendering a page.

Use `--log-requests` to output newline-delimited JSON representing each request, including requests for images and other assets.

Pass `-` to output the list to standard output, or use a filename to write to a file on disk.

The output looks like this:
```
% shot-scraper http://datasette.io/ --log-requests -
{"method": "GET", "url": "http://datasette.io/", "status": 302, "size": null, "timing": {"startTime": 1663211674984.7068, "domainLookupStart": 0.698, "domainLookupEnd": 1.897, "connectStart": 1.897, "secureConnectionStart": -1, "connectEnd": 18.726, "requestStart": 18.86, "responseStart": 99.75, "responseEnd": 101.75000000162981}}
{"method": "GET", "url": "https://datasette.io/", "status": 200, "size": 34592, "timing": {"startTime": 1663211675085.51, "domainLookupStart": 0.187, "domainLookupEnd": 0.197, "connectStart": 0.197, "secureConnectionStart": 15.719, "connectEnd": 63.854, "requestStart": 64.098, "responseStart": 390.231, "responseEnd": 399.268}}
{"method": "GET", "url": "https://datasette.io/static/site.css", "status": 200, "size": 3952, "timing": {"startTime": 1663211675486.027, "domainLookupStart": -1, "domainLookupEnd": -1, "connectStart": -1, "secureConnectionStart": -1, "connectEnd": -1, "requestStart": 0.408, "responseStart": 99.407, "responseEnd": 100.433}}
...
```
Note that the `size` field here will be the size of the response in bytes, but in some circumstances this will not be available and it will be returned as `"size": null`.

## Browser arguments

Additional arguments to pass to the browser instance. The list of Chromium flags can be found [here](https://peter.sh/experiments/chromium-command-line-switches/).

For example, to remove font render hinting:

    shot-scraper https://simonwillison.net/ -o no-hinting.png \
      --height 800 --browser-args "--font-render-hinting=none"

To add multiple arguments, add `--browser-args` for each argument:

    shot-scraper https://simonwillison.net/ -o no-hinting-no-gpu.png \
      --height 800 --browser-args "--font-render-hinting=none" --browser-args "--disable-gpu"

## Taking screenshots of local HTML files

You can pass the path to an HTML file on disk to take a screenshot of that rendered file:

    shot-scraper index.html -o index.png

CSS and images referenced from that file using relative paths will also be included.

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

If you see errors relating to CSP headers such as "Failed to fetch dynamically imported module" you can work around them using {ref}`the --bypass-csp option<bypass-csp>`.

## Viewing console.log() output

Almost all of the `shot-scraper` commands accept a `--log-console` option, which will cause them to output any calls to `console.log()` to standard error while the command is running.

This includes both `console.log()` calls in the existing page JavaScript, as well as any calls to that method that you include in your own custom JavaScript.

For example, running `--log-console` while taking a screenshot of the Facebook homepage will show this warning message, which Facebook logs to the developer tools console to help protect people from social engineering attacks:

```
% shot-scraper shot facebook.com --log-console

 .d8888b.  888                       888
d88P  Y88b 888                       888
Y88b.      888                       888    This is a browser feature intended for
 "Y888b.   888888  .d88b.  88888b.   888    developers. If someone told you to copy-paste
    "Y88b. 888    d88""88b 888 "88b  888    something here to enable a Facebook feature
      "888 888    888  888 888  888  Y8P    or "hack" someone's account, it is a
Y88b  d88P Y88b.  Y88..88P 888 d88P         scam and will give them access to your
 "Y8888P"   "Y888  "Y88P"  88888P"   888    Facebook account.
                           888
                           888
                           888

See https://www.facebook.com/selfxss for more information.

Screenshot of 'http://facebook.com' written to 'facebook-com.png'
```

## `shot-scraper shot --help`

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
  -a, --auth FILENAME             Path to JSON authentication context file
  -w, --width INTEGER             Width of browser window, defaults to 1280
  -h, --height INTEGER            Height of browser window and shot - defaults
                                  to the full height of the page
  -o, --output FILE
  -s, --selector TEXT             Take shot of first element matching this CSS
                                  selector
  --selector-all TEXT             Take shot of all elements matching this CSS
                                  selector
  --js-selector TEXT              Take shot of first element matching this JS
                                  (el) expression
  --js-selector-all TEXT          Take shot of all elements matching this JS
                                  (el) expression
  -p, --padding INTEGER           When using selectors, add this much padding in
                                  pixels
  -j, --javascript TEXT           Execute this JS prior to taking the shot
  --retina                        Use device scale factor of 2
  --omit-background               Omit the default browser background from the
                                  shot, making it possible take advantage of
                                  transparence. Does not work with JPEGs or when
                                  using --quality.
  --quality INTEGER               Save as JPEG with this quality, e.g. 80
  --wait INTEGER                  Wait this many milliseconds before taking the
                                  screenshot
  --wait-for TEXT                 Wait until this JS expression returns true
  --timeout INTEGER               Wait this many milliseconds before failing
  -i, --interactive               Interact with the page in a browser before
                                  taking the shot
  --devtools                      Interact mode with developer tools
  --log-requests FILENAME         Log details of all requests to this file
  --log-console                   Write console.log() to stderr
  -b, --browser [chromium|firefox|webkit|chrome|chrome-beta]
                                  Which browser to use
  -B, --browser-args TEXT         Additional arguments to pass to the browser
  --user-agent TEXT               User-Agent header to use
  --reduced-motion                Emulate 'prefers-reduced-motion' media feature
  --fail                          Fail with an error code if a page returns an
                                  HTTP error
  --skip                          Skip pages that return HTTP errors
  --bypass-csp                    Bypass Content-Security-Policy
  --silent                        Do not output any messages
  --help                          Show this message and exit.
```
<!-- [[[end]]] -->
