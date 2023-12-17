# Scraping pages using JavaScript

The `shot-scraper javascript` command can be used to execute JavaScript directly against a page and return the result as JSON.

This command doesn't produce a screenshot, but has interesting applications for scraping.

To retrieve a string title of a document:

    shot-scraper javascript https://datasette.io/ "document.title"

This returns a JSON string:
```json
"Datasette: An open source multi-tool for exploring and publishing data"
```
To return a raw string instead, use the `-r` or `--raw` options:

    shot-scraper javascript https://datasette.io/ "document.title" -r

Output:

    Datasette: An open source multi-tool for exploring and publishing data

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
## Running more than one statement

You can use `() => { ... }` function syntax to run multiple statements, returning a result at the end of your function.

This example raises an error if no paragraphs are found.

```bash
shot-scraper javascript https://www.example.com/ "
() => {
  var paragraphs = document.querySelectorAll('p');
  if (paragraphs.length == 0) {
    throw 'No paragraphs found';
  }
  return Array.from(paragraphs, el => el.innerText);
}"
```

## Using async/await

You can pass an `async` function if you want to use `await`, including to import modules from external URLs. This example loads the [Readability.js](https://github.com/mozilla/readability) library from [Skypack](https://www.skypack.dev/) and uses it to extract the core content of a page:

```
shot-scraper javascript \
  https://simonwillison.net/2022/Mar/14/scraping-web-pages-shot-scraper/ "
async () => {
  const readability = await import('https://cdn.skypack.dev/@mozilla/readability');
  return (new readability.Readability(document)).parse();
}"
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

(bypass-csp)=
## Bypassing Content Security Policy headers

Some websites use [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) (CSP) headers to prevent additional JavaScript from executing on the page, as a security measure.

When using `shot-scraper` this can prevent some JavaScript features from working. You might see error messages that look like this:
```bash
shot-scraper javascript github.com "
  async () => {
    await import('https://cdn.jsdelivr.net/npm/left-pad/+esm');
    return 'content-security-policy ignored' }
"
```
Output:
```
Error: TypeError: Failed to fetch dynamically imported module:
https://cdn.jsdelivr.net/npm/left-pad/+esm
```
You can use the `--bypass-csp` option to have `shot-scraper` run the browser in a mode that ignores these headers:
```bash
shot-scraper javascript github.com "
  async () => {
    await import('https://cdn.jsdelivr.net/npm/left-pad/+esm');
    return 'content-security-policy ignored' }
" --bypass-csp
```
Output:
```
"content-security-policy ignored"
```

## Running JavaScript from a file

You can also save JavaScript to a file and execute it like this:

    shot-scraper javascript datasette.io -i script.js

Or read it from standard input like this:

    echo "document.title" | shot-scraper javascript datasette.io

## Using this for automated tests

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

## Example: Extracting page content with Readability.js

[Readability.js](https://github.com/mozilla/readability) is "a standalone version of the readability library used for Firefox Reader View." It lets you parse the content on a web page and extract just the title, content, byline and some other key metadata.

The following recipe imports the library from the [Skypack CDN](https://www.skypack.dev/), runs it against the current page and returns the results to the console as JSON:

```bash
shot-scraper javascript https://simonwillison.net/2022/Mar/24/datasette-061/ "
async () => {
  const readability = await import('https://cdn.skypack.dev/@mozilla/readability');
  return (new readability.Readability(document)).parse();
}"
```
The output looks like this:
```json
{
    "title": "Datasette 0.61: The annotated release notes",
    "byline": null,
    "dir": null,
    "lang": "en-gb",
    "content": "<div id=\"readability-page-1\" class=\"page\"><div id=\"primary\">\n\n\n\n\n<p>I released ... <this is a very long string>",
    "length": 8625,
    "excerpt": "I released Datasette 0.61 this morning\u2014closely followed by 0.61.1 to fix a minor bug. Here are the annotated release notes. In preparation for Datasette 1.0, this release includes two potentially \u2026",
    "siteName": null
}
```
See [Extracting web page content using Readability.js and shot-scraper](https://til.simonwillison.net/shot-scraper/readability) for more.

## shot-scraper javascript \-\-help

Full `--help` for this command:

<!-- [[[cog
import cog
from shot_scraper import cli
from click.testing import CliRunner
runner = CliRunner()
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
  -i, --input FILENAME            Read input JavaScript from this file
  -a, --auth FILENAME             Path to JSON authentication context file
  -o, --output FILENAME           Save output JSON to this file
  -r, --raw                       Output JSON strings as raw text
  -b, --browser [chromium|firefox|webkit|chrome|chrome-beta]
                                  Which browser to use
  -B, --browser-args TEXT         Additional arguments to pass to the browser
  --user-agent TEXT               User-Agent header to use
  --reduced-motion                Emulate 'prefers-reduced-motion' media feature
  --log-console                   Write console.log() to stderr
  --fail                          Fail with an error code if a page returns an
                                  HTTP error
  --skip                          Skip pages that return HTTP errors
  --bypass-csp                    Bypass Content-Security-Policy
  --help                          Show this message and exit.
```
<!-- [[[end]]] -->
