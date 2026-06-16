(storyboard)=

# Recording storyboard videos

The `shot-scraper storyboard` command records a WebM video from a YAML storyboard.

Storyboards describe the video as a sequence of scenes. Each scene can open a page,
wait for content, perform actions and then hold on the final frame for a moment.

Create a file called `storyboard.yml` like this:

```yaml
output: demo.webm
url: https://example.com/

viewport:
  width: 1280
  height: 720

scenes:
- name: Landing page
  wait_for: h1
  hold: 1

- name: Open more information
  do:
  - click: "a[href='/more']"
  - wait_for: h1
  hold: 2
```

Then run:

```bash
shot-scraper storyboard storyboard.yml
```

This opens the starting URL, records the scenes and writes the video to
`demo.webm`.

Use `-o` or `--output` to override the output filename:

```bash
shot-scraper storyboard storyboard.yml -o alternate.webm
```

## Storyboard structure

A storyboard file is a YAML mapping with these keys:

`output`
: Filename for the recorded WebM video. This can be omitted if `-o` is used.

`url`
: Starting URL for the video. This can be an `http://` or `https://` URL, a bare
  domain or a path to a local HTML file.

`viewport`
: Optional browser viewport size. Defaults to `1280` by `720`.

`cursor`
: Set to `true` to show a cursor dot and click rings in the video. This can
  also be a mapping of cursor options.

`javascript`
: Optional JavaScript to run in the initial page after `url:`, `wait:`,
  `wait_for:` and `wait_for_url:` have completed, before scenes start. This runs
  inside the current Playwright page context.

`scenes`
: A list of scenes to record.

## Cursor and click visualization

Playwright videos do not show the system cursor. Add `cursor: true` to inject a
visible cursor dot and click rings into the page while recording:

```yaml
output: demo.webm
url: https://example.com/
cursor: true

scenes:
- name: Open menu
  do:
  - click: "button[aria-label='Menu']"
  hold: 1
```

You can also configure the cursor:

```yaml
cursor:
  visible: true
  clicks: true
  color: "#ff4f00"
  size: 18
  click_size: 44
```

Set `visible: false` to show click rings without the cursor dot.

## Scenes

Each scene can use these keys:

`name`
: Optional label used in progress messages.

`open`
: Navigate to a URL at the start of the scene. Relative URLs are resolved against
  the current page URL.

`wait_for`
: Wait for a selector before running the scene actions. This uses Playwright
  locator syntax, so CSS selectors and selectors such as `text=Welcome` are
  both supported.

`wait_for_url`
: Wait for the page URL to match a string, glob or regular expression supported
  by Playwright.

`do`
: A list of actions to run.

`hold`
: Seconds to pause after the scene actions complete. This is useful for making
  the resulting video easier to watch.

Example:

```yaml
scenes:
- name: Search
  open: /search
  wait_for: "#q"
  do:
  - type:
      into: "#q"
      text: "shot-scraper"
      delay: 40
  - press: Enter
  - wait_for: ".results"
  hold: 1.5
```

Use `javascript:` or `js:` inside `do:` to run code in the current Playwright
page context. Unlike `sh:` and `python:`, this executes in the browser page, so
it can read and modify the DOM, `localStorage` and other browser APIs:

```yaml
scenes:
- name: Highlight the first result
  open: http://localhost:8000/search
  wait_for: ".result"
  do:
  - javascript: |
      document.querySelector(".result").style.outline = "4px solid red";
      localStorage.setItem("storyboard-mode", "demo");
  - screenshot: highlighted-result.png
```

There is no scene-level `javascript:` key. To run page JavaScript during a scene,
put it inside the scene's `do:` list.

## Actions

Actions are single-key mappings in a scene's `do` list.

### click

Click a selector:

```yaml
- click: "button[aria-label='Menu']"
```

You can also provide click options:

```yaml
- click:
    selector: "button[aria-label='Menu']"
    button: left
    count: 2
```

### type

Type text into an input or textarea:

```yaml
- type:
    into: "#search"
    text: "datasette"
    delay: 50
```

`delay` is optional and sets the milliseconds between keystrokes.

### fill

Fill a field immediately:

```yaml
- fill:
    into: "#email"
    text: "demo@example.com"
```

### press

Press a key:

```yaml
- press: Enter
```

Or focus a selector before pressing the key:

```yaml
- press:
    selector: "#search"
    key: Enter
```

### scroll

Scroll by a number of pixels:

```yaml
- scroll:
    y: 800
    duration: 1.2
```

Use `to` to scroll an element into view:

```yaml
- scroll:
    to: "#pricing"
    duration: 1
```

### pause

Pause for a number of seconds:

```yaml
- pause: 0.5
```

### wait_for

Wait for a selector:

```yaml
- wait_for: ".loaded"
```

### wait_for_url

Wait for the current URL:

```yaml
- wait_for_url: "**/pricing"
```

### open

Navigate during a scene:

```yaml
- open: /pricing
```

### screenshot

Take a screenshot during the storyboard:

```yaml
- screenshot: step-2.png
```

Screenshot a specific element:

```yaml
- screenshot:
    output: form.png
    selector: "#signup-form"
```

Use `full_page` to capture the full page instead of just the current viewport:

```yaml
- screenshot:
    output: full-page.png
    full_page: true
```

### javascript

Run JavaScript in the current Playwright page context:

```yaml
- javascript: |
    document.querySelector("h1").style.outline = "4px solid red";
```

The shorter `js` key is also supported:

```yaml
- js: window.scrollTo(0, 0)
```

Use top-level `javascript:` for JavaScript that should run once after the
initial page has loaded and before scenes start:

```yaml
output: demo.webm
url: http://localhost:8000/
javascript: |
  localStorage.setItem("theme", "dark");
  document.documentElement.dataset.storyboard = "true";

scenes:
- name: Page with prepared browser state
  wait_for: h1
  do:
  - js: document.querySelector("h1").textContent = "Storyboard demo";
  hold: 1
```

## Complete example

This example records a short product walkthrough:

```yaml
output: signup-demo.webm
url: https://app.example.com/

viewport:
  width: 1440
  height: 900

scenes:
- name: Home page
  wait_for: "text=Get started"
  hold: 1

- name: Open signup form
  do:
  - click: "text=Get started"
  - wait_for: "#email"
  - screenshot: signup-form.png
  hold: 0.5

- name: Complete signup
  do:
  - fill:
      into: "#email"
      text: "demo@example.com"
  - type:
      into: "#name"
      text: "Demo User"
      delay: 40
  - click: "button[type=submit]"
  - wait_for: "text=Welcome"
  hold: 2
```

## Command options

`shot-scraper storyboard` supports the same browser selection, authentication,
console logging, timeout, CSP bypass and HTTP Basic authentication options as
the other browser-based commands.

Use `--silent` to hide progress messages.

## `shot-scraper storyboard --help`

Full `--help` for this command:

```
Usage: shot-scraper storyboard [OPTIONS] STORYBOARD_FILE

  Record a WebM video from a YAML storyboard.

  Usage:

      shot-scraper storyboard storyboard.yml

  The storyboard file should define output, url and scenes. Use -o to override
  the output filename from the YAML file.

Options:
  -o, --output FILE               Output video filename (.webm), overriding
                                  output: in the storyboard
  -a, --auth FILENAME             Path to JSON authentication context file
  --timeout INTEGER               Wait this many milliseconds before failing
  -b, --browser [chromium|firefox|webkit|chrome|chrome-beta]
                                  Which browser to use
  --browser-arg TEXT              Additional arguments to pass to the browser
  --user-agent TEXT               User-Agent header to use
  --reduced-motion                Emulate 'prefers-reduced-motion' media feature
  --log-console                   Write console.log() to stderr
  --fail                          Fail with an error code if a page returns an
                                  HTTP error
  --skip                          Skip pages that return HTTP errors
  --bypass-csp                    Bypass Content-Security-Policy
  --silent                        Do not output any messages
  --auth-password TEXT            Password for HTTP Basic authentication
  --auth-username TEXT            Username for HTTP Basic authentication
  --help                          Show this message and exit.
```
