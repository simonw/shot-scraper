# Taking multiple screenshots

You can configure multiple screenshots using a YAML file. Create a file called `shots.yml` that looks like this:

```yaml
- output: example.com.png
  url: http://www.example.com/
- output: w3c.org.png
  url: https://www.w3.org/
```
Then run the tool like so:

    shot-scraper multi shots.yml

This will create two image files, `www-example-com.png` and `w3c.org.png`, containing screenshots of those two URLs.

Use `-` to pass in YAML from standard input:

    echo "- url: http://www.example.com" | shot-scraper multi -

If you run the tool with the `-n` or `--no-clobber` option any shots where the output file aleady exists will be skipped.

You can specify a subset of screenshots to take by specifying output files that you would like to create. For example, to take just the shots of `one.png` and `three.png` that are defined in `shots.yml` run this:

    shot-scraper multi shots.yml -o one.png -o three.png

The `url:` can be set to a path to a file on disk as well:

```yaml
- output: index.png
  url: index.html
```

Use the `--scale-factor` option to capture all screenshots at a specific scale factor, which effectively simulates different device pixel ratios. This setting is useful for testing high-definition displays or emulating screens with various pixel densities.

For example, setting `--scale-factor 3` results in screenshots with a CSS pixel ratio of 3, which is ideal for emulating a high-resolution display, such as Apple's iPhone 12 screens.

To take screenshots with a scale factor of 3 (tripled resolution), run the following command:

    shot-scraper multi shots.yml --scale-factor 3

This will multiply both the width and height of all screenshots by 3, resulting in images with a higher level of detail, suitable for scenarios where you need to capture the screen as it would appear on a high-DPI display.

Use `--retina` to take all screenshots at retina resolution instead, doubling the dimensions of the files:

    shot-scraper multi shots.yml --retina

Note: The `--retina` option should not be used in conjunction with the `--scale-factor` flag as they are mutually exclusive. If both are provided, the command will raise an error to prevent conflicts.

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

You can use `selector_all:` to capture every element matching a selector, or `selectors_all:` to pass a list of such selectors:

```yaml
- output: selectors-all.png
  url: https://simonwillison.net/
  selectors_all:
  - .day
  - .entry:nth-of-type(1)
  padding: 20
```

The `--js-selector` and `--js-selector-all` options can be provided using the `js_selector:`, `js_selectors:`, `js_selector_all:` and `js_selectors_all:` keys:

```yaml
- output: js-selector-all.png
  url: https://github.com/simonw/shot-scraper
  js_selector: |-
    el.tagName == "P" && el.innerText.includes("shot-scraper")
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

You can include desired `height`, `width`, `quality`, `wait` and `wait_for` options on each item as well:

```yaml
- output: simon-narrow.jpg
  url: https://simonwillison.net/
  width: 400
  height: 800
  quality: 80
  wait: 500
  wait_for: document.querySelector('#bighead')
```

## Running a server for the duration of the session

If you need to run a server for the duration of the `shot-scraper multi` session you can specify that using a `server:` block, like this:
```yaml
- server: python -m http.server 8000
```
The `server:` key also accepts a list of arguments:
```yaml
- server:
  - python
  - -m
  - http.server
  - 8000
```
With that server configured, you can now take screenshots of `http://localhost:8000/` and any other URLs hosted by that server:
```yaml
- output: index.png
  url: http://localhost:8000/
```
The server process will be automatically terminated when the `shot-scraper multi` command completes, unless you pass the `--leave-server` option to `shot-scraper multi` in which case it will be left running - you can terminate it using `kill PID` with the PID displayed in the console output.

## Running custom code between steps

If you are taking screenshots of a single application, you may find it useful to run additional steps between shots that modify that application in some way.

You can do that using the `sh:` or `python:` keys. These can specify shell commands or Python code to run before taking the screenshot:

```yaml
- sh: echo "Hello from shell" > index.html
  output: from-shell.png
  url: http://localhost:8000/
```
You can also specify a list of shell arguments like this:
```yaml
- sh:
  - curl
  - -o
  - index.html
  - https://www.example.com/
  output: example.png
  url: http://localhost:8000/
```
If you specify these steps without a `url:` key they will still execute as individual task executions, without also taking a screenshot:
```yaml
- sh: echo "hello world" > index.html
- python: |
    content = open("index.html").read()
    open("index.html", "w").write(content.upper())
```

## `shot-scraper multi --help`

Full `--help` for this command:

<!-- [[[cog
import cog
from shot_scraper import cli
from click.testing import CliRunner
runner = CliRunner()
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

  For full YAML syntax documentation, see:
  https://shot-scraper.datasette.io/en/stable/multi.html

Options:
  -a, --auth FILENAME             Path to JSON authentication context file
  --scale-factor FLOAT            Device scale factor. Cannot be used together
                                  with '--retina'.
  --retina                        Use device scale factor of 2. Cannot be used
                                  together with '--scale-factor'.
  --timeout INTEGER               Wait this many milliseconds before failing
  -n, --no-clobber                Skip images that already exist
  -o, --output TEXT               Just take shots matching these output files
  -b, --browser [chromium|firefox|webkit|chrome|chrome-beta]
                                  Which browser to use
  --browser-arg TEXT              Additional arguments to pass to the browser
  --user-agent TEXT               User-Agent header to use
  --reduced-motion                Emulate 'prefers-reduced-motion' media feature
  --log-console                   Write console.log() to stderr
  --fail                          Fail with an error code if a page returns an
                                  HTTP error
  --skip                          Skip pages that return HTTP errors
  --silent                        Do not output any messages
  --auth-password TEXT            Password for HTTP Basic authentication
  --auth-username TEXT            Username for HTTP Basic authentication
  --leave-server                  Leave servers running when script finishes
  --har                           Save all requests to trace.har file
  --har-zip                       Save all requests to trace.har.zip file
  --har-file FILE                 Path to HAR file to save all requests
  --help                          Show this message and exit.
```
<!-- [[[end]]] -->
