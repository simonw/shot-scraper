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

  https://shot-scraper.datasette.io/en/stable/multi.html

Options:
  -a, --auth FILENAME             Path to JSON authentication context file
  --retina                        Use device scale factor of 2
  --timeout INTEGER               Wait this many milliseconds before failing
  -n, --no-clobber                Skip images that already exist
  -o, --output TEXT               Just take shots matching these output files
  -b, --browser [chromium|firefox|webkit|chrome|chrome-beta]
                                  Which browser to use
  -B, --browser-args TEXT         Additional arguments to pass to the browser
  --user-agent TEXT               User-Agent header to use
  --reduced-motion                Emulate 'prefers-reduced-motion' media feature
  --log-console                   Write console.log() to stderr
  --fail                          Fail with an error code if a page returns an
                                  HTTP error
  --skip                          Skip pages that return HTTP errors
  --silent                        Do not output any messages
  --help                          Show this message and exit.
```
<!-- [[[end]]] -->
