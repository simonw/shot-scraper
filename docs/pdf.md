# Saving a web page to PDF

The `shot-scraper pdf` command saves a PDF version of a web page - the equivalent of using `Print -> Save to PDF` in Chromium.

    shot-scraper pdf https://datasette.io/

This will save to `datasette-io.pdf`. You can use `-o` to specify a filename:

    shot-scraper pdf https://datasette.io/tutorials/learn-sql \
      -o learn-sql.pdf

You can pass the path to a local file on disk instead of a URL:

    shot-scraper pdf invoice.html -o invoice.pdf

## `shot-scraper pdf --help`

Full `--help` for this command:

<!-- [[[cog
import cog
from shot_scraper import cli
from click.testing import CliRunner
runner = CliRunner()
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

      shot-scraper pdf https://datasette.io/ -o datasette.pdf

  You can pass a path to a file instead of a URL:

      shot-scraper pdf invoice.html -o invoice.pdf

Options:
  -a, --auth FILENAME             Path to JSON authentication context file
  -o, --output FILE
  -j, --javascript TEXT           Execute this JS prior to creating the PDF
  --wait INTEGER                  Wait this many milliseconds before taking the
                                  screenshot
  --media-screen                  Use screen rather than print styles
  --landscape                     Use landscape orientation
  --format [Letter|Legal|Tabloid|Ledger|A0|A1|A2|A3|A4|A5|A6]
                                  Which standard paper size to use
  --width TEXT                    PDF width including units, e.g. 10cm
  --height TEXT                   PDF height including units, e.g. 10cm
  --scale FLOAT RANGE             Scale of the webpage rendering  [0.1<=x<=2.0]
  --print-background              Print background graphics
  --log-console                   Write console.log() to stderr
  --fail                          Fail with an error code if a page returns an
                                  HTTP error
  --skip                          Skip pages that return HTTP errors
  --silent                        Do not output any messages
  --help                          Show this message and exit.
```
<!-- [[[end]]] -->
