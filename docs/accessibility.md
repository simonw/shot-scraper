(accessibility)=

# Dumping out an accessibility tree

The `shot-scraper accessibility` command dumps out the Chromium accessibility tree for the provided URL, as JSON:
```bash
shot-scraper accessibility https://datasette.io/
```
Use `-o filename.json` to write the output to a file instead of displaying it.

Add `--javascript SCRIPT` to execute custom JavaScript before taking the snapshot.

## `shot-scraper accessibility --help`

Full `--help` for this command:

<!-- [[[cog
import cog
from shot_scraper import cli
from click.testing import CliRunner
runner = CliRunner()
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
  --timeout INTEGER      Wait this many milliseconds before failing
  --log-console          Write console.log() to stderr
  --fail                 Fail with an error code if a page returns an HTTP error
  --skip                 Skip pages that return HTTP errors
  --bypass-csp           Bypass Content-Security-Policy
  --auth-password TEXT   Password for HTTP Basic authentication
  --auth-username TEXT   Username for HTTP Basic authentication
  --help                 Show this message and exit.
```
<!-- [[[end]]] -->
