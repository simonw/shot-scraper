(har)=

# Saving a web page to an HTTP Archive

An HTTP Archive file captures the full details of a series of HTTP requests and responses as JSON.

The `shot-scraper har` command can save a `*.har.zip` file that contains both that JSON data and the content of any assets that were loaded by the page.
```bash
shot-scraper har https://datasette.io/
```
This will save to `datasette-io.har`. You can use `-o` to specify a filename:
```bash
shot-scraper har https://datasette.io/tutorials/learn-sql \
  -o learn-sql.har
```
A `.har` file is JSON. You can view it using the [Google HAR Analyzer](https://toolbox.googleapps.com/apps/har_analyzer/) tool.

HTTP Archives can also be created as `.har.zip` files. These have a slightly different format: the `har.har` JSON does not include the full content of the responses, which is instead stored as separate files inside the `.zip`.

To create one of these, either add the `--zip` flag:

```bash
shot-scraper har https://datasette.io/ --zip
```
Or specify a filename that ends in `.har.zip`:
```bash
shot-scraper har https://datasette.io/ -o datasette-io.har.zip
```

You can view the contents of a HAR zip file using `unzip -l`:
```bash
unzip -l datasette-io.har.zip
```
```
Archive:  datasette-io.har.zip
  Length      Date    Time    Name
---------  ---------- -----   ----
    39067  02-13-2025 10:33   41824dbd0c51f584faf0e2c4e88de01b8a5dcdcd.html
     4052  02-13-2025 10:33   34972651f161f0396c697c65ef9aaeb2c9ac50c4.css
     2501  02-13-2025 10:33   9f612e71165058f0046d8bf8fec12af7eb15f39d.css
    10916  02-13-2025 10:33   2737174596eafba6e249022203c324605f023cdd.svg
     5557  02-13-2025 10:33   427504aa6ef5a8786f90fb2de636133b3fc6d1fe.js
     1393  02-13-2025 10:33   25c68a82b654c9d844c604565dab4785161ef697.js
     1170  02-13-2025 10:33   31c073551ef5c84324073edfc7b118f81ce9a7d2.svg
     1158  02-13-2025 10:33   1e0c64af7e6a4712f5e7d1917d9555bbc3d01f7a.svg
     1161  02-13-2025 10:33   ec8282b36a166d63fae4c04166bb81f945660435.svg
     3373  02-13-2025 10:33   5f85a11ef89c0e3f237c8e926c1cb66727182102.svg
     1134  02-13-2025 10:33   3b9d8109b919dfe9393dab2376fe03267dadc1f1.svg
    31670  02-13-2025 10:33   469f0d28af6c026dcae8c81731e2b0484aeac92c.jpeg
     1157  02-13-2025 10:33   b7786336bfce38a9677d26dc9ef468bb1ed45e19.svg
    50494  02-13-2025 10:33   har.har
---------                     -------
   154803                     14 files
```

You can record multiple pages to a single HTTP Archive using the {ref}`shot-scraper multi --har option<multi-har>`.

## Extracting resources from HAR files

Use the `--extract` or `-x` option to automatically extract all resources from the HAR file into a directory:

```bash
shot-scraper har https://datasette.io/ --extract
```
This will create both `datasette-io.har` and a `datasette-io/` directory containing all resources with meaningful filenames derived from their URLs.

The extracted files use extensions based on their content-type. For example, a request to `/api/data` that returns JSON will be saved with a `.json` extension.

You can combine this with `--zip`:
```bash
shot-scraper har https://datasette.io/ --extract --zip
```
This creates `datasette-io.har.zip` and extracts resources to the `datasette-io/` directory.

## `shot-scraper har --help`

Full `--help` for this command:

<!-- [[[cog
import cog
from shot_scraper import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["har", "--help"])
help = result.output.replace("Usage: cli", "Usage: shot-scraper")
cog.out(
    "```\n{}\n```\n".format(help.strip())
)
]]] -->
```
Usage: shot-scraper har [OPTIONS] URL

  Record a HAR file for the specified page

  Usage:

      shot-scraper har https://datasette.io/

  This defaults to saving to datasette-io.har - use -o to specify a different
  filename:

      shot-scraper har https://datasette.io/ -o trace.har

  Use --zip to save as a .har.zip file instead, or specify a filename ending in
  .har.zip

  Use --extract / -x to also extract all resources from the HAR into a
  directory. With -x, you can specify a base path and the .har extension will be
  added automatically:

      shot-scraper har https://datasette.io/ -x -o /tmp/datasette

  This creates /tmp/datasette.har and extracts resources to /tmp/datasette/

Options:
  -z, --zip              Save as a .har.zip file
  -x, --extract          Extract resources from the HAR file into a directory
  -a, --auth FILENAME    Path to JSON authentication context file
  -o, --output FILE      HAR filename
  --wait INTEGER         Wait this many milliseconds before taking the
                         screenshot
  --wait-for TEXT        Wait until this JS expression returns true
  -j, --javascript TEXT  Execute this JavaScript on the page
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
