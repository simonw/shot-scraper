# Dumping the HTML of a page

The `shot-scraper html` command dumps out the final HTML of a page after all JavaScript has run.

    shot-scraper html https://datasette.io/

Use `-o filename.html` to write the output to a file instead of displaying it.

    shot-scraper html https://datasette.io/ -o index.html

Add `--javascript SCRIPT` to execute custom JavaScript before taking the HTML snapshot.

    shot-scraper html https://datasette.io/ \
      --javascript "document.querySelector('h1').innerText = 'Hello, world!'"

## Retrieving the HTML for a specific element

You can use the `-s SELECTOR` option to capture just the HTML for one specific element on the page, identified using a CSS selector:

    shot-scraper html https://datasette.io/ -s h1

This outputs:

    <h1>
      <img class="datasette-logo" src="/static/datasette-logo.svg" alt="Datasette">
    </h1>

## `shot-scraper html --help`

Full `--help` for this command:

<!-- [[[cog
import cog
from shot_scraper import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["html", "--help"])
help = result.output.replace("Usage: cli", "Usage: shot-scraper")
cog.out(
    "```\n{}\n```\n".format(help.strip())
)
]]] -->
```
Usage: shot-scraper html [OPTIONS] URL

  Output the final HTML of the specified page

  Usage:

      shot-scraper html https://datasette.io/

  Use -o to specify a filename:

      shot-scraper html https://datasette.io/ -o index.html

Options:
  -a, --auth FILENAME             Path to JSON authentication context file
  -o, --output FILE
  -j, --javascript TEXT           Execute this JS prior to saving the HTML
  -s, --selector TEXT             Return outerHTML of first element matching
                                  this CSS selector
  --wait INTEGER                  Wait this many milliseconds before taking the
                                  snapshot
  --log-console                   Write console.log() to stderr
  -b, --browser [chromium|firefox|webkit|chrome|chrome-beta]
                                  Which browser to use
  -B, --browser-args TEXT         Additional arguments to pass to the browser
  --user-agent TEXT               User-Agent header to use
  --fail                          Fail with an error code if a page returns an
                                  HTTP error
  --skip                          Skip pages that return HTTP errors
  --bypass-csp                    Bypass Content-Security-Policy
  --silent                        Do not output any messages
  --help                          Show this message and exit.
```
<!-- [[[end]]] -->
