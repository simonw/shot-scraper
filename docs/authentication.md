# Websites that need authentication

If you want to take screenshots of a site that has some form of authentication, you will first need to authenticate with that website manually.

You can do that using the `shot-scraper auth` command:

    shot-scraper auth \
      https://datasette-auth-passwords-demo.datasette.io/-/login \
      auth.json

(For this demo, use username = `root` and password = `password!`)

This will open a browser window on your computer showing the page you specified.

You can then sign in using that browser window - including 2FA or CAPTCHAs or other more complex form of authentication.

When you are finished, hit `<enter>` at the `shot-scraper` command-line prompt. The browser will close and the authentication credentials (usually cookies) for that browser session will be written out to the `auth.json` file.

To take authenticated screenshots you can then use the `-a` or `--auth` options to point to the JSON file that you created:

    shot-scraper https://datasette-auth-passwords-demo.datasette.io/ \
      -a auth.json -o authed.png

## `shot-scraper auth --help`

Full `--help` for `shot-scraper auth`:

<!-- [[[cog
import cog
from shot_scraper import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["auth", "--help"])
help = result.output.replace("Usage: cli", "Usage: shot-scraper")
cog.out(
    "```\n{}\n```\n".format(help.strip())
)
]]] -->
```
Usage: shot-scraper auth [OPTIONS] URL CONTEXT_FILE

  Open a browser so user can manually authenticate with the specified site, then
  save the resulting authentication context to a file.

  Usage:

      shot-scraper auth https://github.com/ auth.json

Options:
  -b, --browser [chromium|firefox|webkit|chrome|chrome-beta]
                                  Which browser to use
  -B, --browser-args TEXT         Additional arguments to pass to the browser
  --user-agent TEXT               User-Agent header to use
  --devtools                      Open browser DevTools
  --log-console                   Write console.log() to stderr
  --help                          Show this message and exit.
```
<!-- [[[end]]] -->
