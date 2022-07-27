# Saving a web page to PDF

The `shot-scraper pdf` command saves a PDF version of a web page - the equivalent of using `Print -> Save to PDF` in Chromium.

    shot-scraper pdf https://datasette.io/

This will save to `datasette-io.pdf`. You can use `-o` to specify a filename:

    shot-scraper pdf https://datasette.io/tutorials/learn-sql \
      -o learn-sql.pdf

## shot-scraper pdf \-\-help

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
