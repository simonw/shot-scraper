(video)=

# Recording videos

The `shot-scraper video` command records a WebM video from a YAML storyboard.

Storyboards describe the video as a sequence of scenes. Each scene can open a page, wait for content, perform actions and pause between steps.

Create a file called `storyboard.yml` like this:

```yaml
output: demo.webm
url: https://shot-scraper.datasette.io/en/stable/

viewport:
  width: 1280
  height: 720

cursor: true
wait_for: "text=Quick start"

scenes:
- name: Documentation home
  do:
  - pause: 1

- name: Open installation docs
  do:
  - click: ".sidebar-tree a[href='installation.html']"
  - wait_for: 'h1:has-text("Installation")'
  - screenshot: installation.png
  - pause: 1

- name: Search the docs
  do:
  - click: "input.sidebar-search"
  - type:
      into: "input.sidebar-search"
      text: "authentication"
      delay_ms: 25
  - press:
      selector: "input.sidebar-search"
      key: Enter
  - wait_for: "text=Search Results"
  - pause: 2
```

Then run:

```bash
shot-scraper video storyboard.yml
```

This opens the starting URL, records the scenes and writes the video to `demo.webm`.

Use `-o` or `--output` to override the output filename:

```bash
shot-scraper video storyboard.yml -o alternate.webm
```

Use `--mp4` to also convert the recorded WebM video to MP4 using `ffmpeg`. The WebM is still written first, then the MP4 is written using the same filename with the extension replaced by `.mp4`:

```bash
shot-scraper video storyboard.yml --mp4
```

If `ffmpeg` is not installed, the WebM file is still created but the command exits with a non-zero status and an error explaining that the MP4 was not created.

## Storyboard structure

A storyboard file is a YAML mapping with these keys:

`output`
: Filename for the recorded WebM video. This can be omitted if `-o` is used.

  ```yaml
  output: demo.webm
  ```

`url`
: Starting URL for the video. This can be an `http://` or `https://` URL, a bare domain or a path to a local HTML file.

  ```yaml
  url: https://shot-scraper.datasette.io/en/stable/
  ```

`sh`
: Optional shell command to run before `server:` starts and before the browser opens. If both top-level `sh:` and `python:` are present, `sh:` runs first. This can be a string, which is run through the shell, or a list of arguments, which is run directly.

  ```yaml
  sh: |
    set -e
    echo "Preparing storyboard files"
    date > /tmp/storyboard-started.txt
  ```

  The shell process must exit with status `0`. For multi-line `sh: |` blocks, use `set -e` if you want the shell to stop at the first failing command.

`python`
: Optional Python code to run before `server:` starts and before the browser opens. If both top-level `sh:` and `python:` are present, `python:` runs after `sh:`.

  ```yaml
  python: |
    from pathlib import Path
    root = Path("/tmp/demo-root")
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_text("<h1>Local demo</h1>")
  ```

If a `sh:` or `python:` command exits with a non-zero status, `shot-scraper video` stops and exits with an error.

`server`
: Optional command to run as a server for the duration of the storyboard recording. This can be a string, which is run through the shell, or a list of arguments, which is run directly. See {ref}`Running a server for the duration of the storyboard<video-server>` for more details.

  ```yaml
  server: python -m http.server 8000
  ```

  ```yaml
  server:
  - python
  - -m
  - http.server
  - 8000
  ```

`viewport`
: Optional browser viewport size. Defaults to `1280` by `720`. Use a mapping with `width` and `height` values:

  ```yaml
  viewport:
    width: 1440
    height: 900
  ```

`cursor`
: Set to `true` to show a cursor dot and click rings in the video. Set to `false` or omit it to leave the cursor hidden. Use a mapping to configure the cursor:

  ```yaml
  cursor:
    visible: true
    clicks: true
    color: "#ff4f00"
    size: 18
    click_size: 44
  ```

  `visible` shows or hides the cursor dot. `clicks` shows or hides click rings. `color` is a CSS color for the cursor and rings. `size` is the cursor dot diameter in pixels. `click_size` is the click ring diameter in pixels.

`wait`
: Seconds to pause after the starting page has loaded and before recording scenes. Use this when the page needs a fixed amount of time before the first scene starts.

  ```yaml
  wait: 0.5
  ```

`wait_for`
: Selector to wait for after the starting page has loaded and before recording scenes. This uses [Playwright locator syntax](https://playwright.dev/docs/locators#locate-by-css-or-xpath), so CSS selectors and selectors such as `text=Quick start` are supported.

  ```yaml
  wait_for: "text=Quick start"
  ```

`wait_for_url`
: URL string or glob pattern to wait for after the starting page has loaded and before recording scenes.

  ```yaml
  wait_for_url: "**/dashboard"
  ```

`javascript`
: Optional JavaScript to run in the initial page after `url:`, `wait:`, `wait_for:` and `wait_for_url:` have completed, before scenes start. This runs inside the current Playwright page context.

  ```yaml
  javascript: |
    localStorage.setItem("theme", "dark");
    document.documentElement.dataset.storyboard = "true";
  ```

`scenes`
: Required list of scenes to record. If you omit the top-level `url:`, the first scene must define `open:`.

  ```yaml
  scenes:
  - name: Open docs
    open: https://shot-scraper.datasette.io/en/stable/
    wait_for: "text=Quick start"
    do:
    - pause: 1
  ```

## Cursor and click visualization

Playwright videos do not show the system cursor. Add `cursor: true` to inject a visible cursor dot and click rings into the page while recording:

```yaml
output: demo.webm
url: https://shot-scraper.datasette.io/en/stable/
cursor: true

scenes:
- name: Click installation link
  do:
  - click: ".sidebar-tree a[href='installation.html']"
  - wait_for: 'h1:has-text("Installation")'
  - pause: 1
```

You can also configure the cursor using these fields:

```yaml
cursor:
  visible: true
  clicks: true
  color: "#ff4f00"
  size: 18
  click_size: 44
```

`visible` controls whether the cursor dot is shown. `clicks` controls whether click rings are shown. `color` is any CSS color value. `size` is the cursor dot diameter in pixels. `click_size` is the click ring diameter in pixels. Set `visible: false` to show click rings without the cursor dot.

(video-server)=

## Running a server for the duration of the storyboard

If you need to run a server for the duration of the `shot-scraper video` session, specify it using `server:`:

```yaml
output: demo.webm
python: |
  from pathlib import Path
  root = Path("/tmp/demo-root")
  root.mkdir(parents=True, exist_ok=True)
  (root / "index.html").write_text("<h1>Local demo</h1>")
server: python -m http.server 8000 --directory /tmp/demo-root
url: http://localhost:8000/
wait_for: h1

scenes:
- name: Home page
  do:
  - pause: 1
```

The `server:` key also accepts a list of arguments:

```yaml
output: demo.webm
python: |
  from pathlib import Path
  root = Path("/tmp/demo-root")
  root.mkdir(parents=True, exist_ok=True)
  (root / "index.html").write_text("<h1>Local demo</h1>")
server:
- python
- -m
- http.server
- 8000
- --directory
- /tmp/demo-root
url: http://localhost:8000/
wait_for: h1

scenes:
- name: Home page
  do:
  - pause: 1
```

The server process will be automatically terminated when the video command completes, unless you pass `--leave-server`. In that case it will be left running, and the process ID will be displayed in the console output.

## Scenes

Each scene can use these keys:

`name`
: Optional label used in progress messages.

  ```yaml
  name: Search the docs
  ```

`open`
: Navigate to a URL at the start of the scene. Relative URLs are resolved against the current page URL.

  ```yaml
  open: installation.html
  ```

`wait_for`
: Wait for a selector before running the scene actions. This uses [Playwright locator syntax](https://playwright.dev/docs/locators#locate-by-css-or-xpath), so CSS selectors and selectors such as `text=Welcome` are both supported.

  ```yaml
  wait_for: 'h1:has-text("Installation")'
  ```

`wait_for_url`
: Wait for the page URL to match a string or glob pattern supported by Playwright.

  ```yaml
  wait_for_url: "**/installation.html"
  ```

`sh`
: Shell command to run before the scene opens a page or runs actions. This can be a string, which is run through the shell, or a list of arguments, which is run directly.

  ```yaml
  sh: echo "scene" > scene.txt
  ```

`python`
: Python code to run before the scene opens a page or runs actions.

  ```yaml
  python: |
    open("scene.txt", "w").write("ok")
  ```

`do`
: A list of {ref}`actions<video-actions>` to run. Actions run in the order listed, after `sh:`, `python:`, `open:`, `wait_for:` and `wait_for_url:` for the scene. Use a `pause` action at the end of this list to keep recording the final frame for a moment.

  ```yaml
  do:
  - click: ".sidebar-tree a[href='installation.html']"
  - wait_for: 'h1:has-text("Installation")'
  - pause: 1
  ```

Example:

```yaml
scenes:
- name: Search the docs
  open: https://shot-scraper.datasette.io/en/stable/
  wait_for: "input.sidebar-search"
  do:
  - type:
      into: "input.sidebar-search"
      text: "authentication"
      delay_ms: 40
  - press:
      selector: "input.sidebar-search"
      key: Enter
  - wait_for: "text=Search Results"
  - pause: 1.5
```

## Running custom code between steps

Storyboard scenes support the same `sh:` and `python:` keys as `shot-scraper multi`. These commands run before the scene opens a page or runs actions:

```yaml
scenes:
- name: Build local page
  sh: echo "Hello from shell" > index.html
  open: index.html
  do:
  - pause: 1
```

If a scene-level or action-level `sh:` or `python:` command exits with a non-zero status, `shot-scraper video` stops and exits with an error.

You can also specify a list of shell arguments:

```yaml
scenes:
- name: Fetch page
  sh:
  - curl
  - -L
  - -o
  - index.html
  - https://shot-scraper.datasette.io/en/stable/installation.html
  open: index.html
```

Use `python:` to run Python code before a scene:

```yaml
scenes:
- name: Rewrite page
  python: |
    content = open("index.html").read()
    open("index.html", "w").write(content.upper())
  open: index.html
```

For commands between individual browser actions, use `sh:` or `python:` inside the `do:` list:

```yaml
output: demo.webm
python: |
  from pathlib import Path
  root = Path("/tmp/demo-root")
  root.mkdir(parents=True, exist_ok=True)
  (root / "index.html").write_text("<h1>First version</h1>")
server: python -m http.server 8000 --directory /tmp/demo-root
url: http://localhost:8000/
wait_for: 'h1:has-text("First version")'

scenes:
- name: Update then reload
  do:
  - sh: echo "<h1>Updated</h1>" > /tmp/demo-root/index.html
  - open: http://localhost:8000/
  - wait_for: 'h1:has-text("Updated")'
```

Use `javascript:` or `js:` inside `do:` to run code in the current Playwright page context. Unlike `sh:` and `python:`, this executes in the browser page, so it can read and modify the DOM, `localStorage` and other browser APIs:

```yaml
scenes:
- name: Highlight the installation heading
  open: https://shot-scraper.datasette.io/en/stable/installation.html
  wait_for: 'h1:has-text("Installation")'
  do:
  - javascript: |
      document.querySelector("h1").style.outline = "4px solid red";
      localStorage.setItem("storyboard-mode", "demo");
  - screenshot: highlighted-installation.png
```

There is no scene-level `javascript:` key. To run page JavaScript during a scene, put it inside the scene's `do:` list.

(video-actions)=

## Actions

Actions are single-key mappings in a scene's `do` list.

### click

Click a selector. The string form is shorthand for a mapping with `selector:`.

```yaml
- click: "button[aria-label='Menu']"
```

You can also provide click options. `button` can be `left`, `right` or `middle`. `count` is the number of clicks.

```yaml
- click:
    selector: "button[aria-label='Menu']"
    button: left
    count: 2
```

### type

Type text into an input, textarea or focused editable element. Use `into:` or `selector:` to identify the target; both names mean the same thing. `delay_ms` is optional and sets the milliseconds between keystrokes.

```yaml
- type:
    into: "#search"
    text: "datasette"
    delay_ms: 50
```

### fill

Fill a field immediately. Use `into:` or `selector:` to identify the target; both names mean the same thing.

```yaml
- fill:
    into: "#email"
    text: "demo@example.com"
```

### press

Press a key. The string form presses the key using the page keyboard, so it acts on whichever element is currently focused.

```yaml
- press: Enter
```

Use the mapping form to send the key press to a specific selector:

```yaml
- press:
    selector: "#search"
    key: Enter
```

### scroll

Scroll by a number of pixels. The numeric shorthand scrolls vertically by that many pixels:

```yaml
- scroll: 800
```

Use the mapping form for `x`, `y`, `to` and `duration`. `duration` is in seconds and enables smooth scrolling.

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

Wait for a selector using [Playwright locator syntax](https://playwright.dev/docs/locators#locate-by-css-or-xpath). CSS selectors and text selectors such as `text=Search Results` are supported.

```yaml
- wait_for: ".loaded"
```

### wait_for_url

Wait for the current URL to match a string or glob pattern:

```yaml
- wait_for_url: "**/pricing"
```

### open

Navigate during a scene. Relative URLs are resolved against the current page URL.

```yaml
- open: /pricing
```

### screenshot

Take a screenshot during the storyboard. The string form writes a viewport screenshot to that path.

```yaml
- screenshot: step-2.png
```

Use the mapping form for `output`, `selector` and `full_page`. `selector` captures just that element.

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

### sh

Run a shell command. The string form is run through the shell.

```yaml
- sh: echo "Updated" > index.html
```

Provide a list of arguments to run without a shell:

```yaml
- sh:
  - touch
  - updated.html
```

### python

Run Python code using the same Python executable that is running `shot-scraper`:

```yaml
- python: |
    content = open("index.html").read()
    open("index.html", "w").write(content.upper())
```

### javascript

Run JavaScript in the current Playwright page context. This can read and modify the DOM, `localStorage` and other browser APIs:

```yaml
- javascript: |
    document.querySelector("h1").style.outline = "4px solid red";
```

The shorter `js` key is also supported:

```yaml
- js: window.scrollTo(0, 0)
```

Use top-level `javascript:` for JavaScript that should run once after the initial page has loaded and before scenes start:

```yaml
output: demo.webm
url: https://shot-scraper.datasette.io/en/stable/
javascript: |
  document.documentElement.dataset.storyboard = "true";
  document.body.style.backgroundColor = "#fffdf7";

scenes:
- name: Page with prepared browser state
  wait_for: "text=Quick start"
  do:
  - js: document.querySelector("h1").textContent = "Storyboard demo";
  - pause: 1
```

## Complete example

This example records a short walkthrough of the `shot-scraper` documentation site:

```yaml
output: shot-scraper-docs-demo.webm
url: https://shot-scraper.datasette.io/en/stable/

viewport:
  width: 1280
  height: 720

cursor:
  visible: true
  clicks: true
  color: "#ff4f00"
  size: 18
  click_size: 44

wait_for: "text=Quick start"

scenes:
- name: Documentation home
  do:
  - pause: 1

- name: Open installation docs
  do:
  - click: ".sidebar-tree a[href='installation.html']"
  - wait_for: 'h1:has-text("Installation")'
  - screenshot: installation.png
  - pause: 1

- name: Search the docs
  do:
  - click: "input.sidebar-search"
  - type:
      into: "input.sidebar-search"
      text: "authentication"
      delay_ms: 25
  - press:
      selector: "input.sidebar-search"
      key: Enter
  - wait_for: "text=Search Results"
  - js: |
      document.body.style.outline = "4px solid #ff4f00";
  - screenshot: search-results.png
  - pause: 2
```

## Command options

`shot-scraper video` supports the same browser selection, authentication, console logging, timeout, CSP bypass and HTTP Basic authentication options as the other browser-based commands.

Use `--silent` to hide progress messages. Use `--leave-server` to leave a configured `server:` process running after the command finishes.

Use `--mp4` to create an MP4 copy of the recorded WebM video. This requires `ffmpeg` to be installed. The command will then create both a `filename.webm` and `filename.mp4` file.

## `shot-scraper video --help`

Full `--help` for this command:

<!-- [[[cog
import cog
from shot_scraper import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["video", "--help"])
help = result.output.replace("Usage: cli", "Usage: shot-scraper")
cog.out(
    "```\n{}\n```\n".format(help.strip())
)
]]] -->
```
Usage: shot-scraper video [OPTIONS] STORYBOARD_FILE

  Record a WebM video from a YAML storyboard.

  Common usage:

      shot-scraper video storyboard.yml
      shot-scraper video storyboard.yml -o demo.webm --mp4

  A storyboard is a YAML mapping with an output filename, a starting URL (or an
  opening scene), and a list of scenes. Each scene can wait, run commands, run
  browser actions, and pause between steps.

  Example storyboard.yml:

      output: demo.webm
      url: https://shot-scraper.datasette.io/en/stable/
      viewport:
        width: 1280
        height: 720
      cursor: true
      wait_for: "text=Quick start"
      scenes:
      - name: Documentation home
        do:
        - pause: 1
      - name: Open installation docs
        do:
        - click: ".sidebar-tree a[href='installation.html']"
        - wait_for: 'h1:has-text("Installation")'
        - screenshot: installation.png
        - pause: 1
      - name: Search the docs
        do:
        - click: "input.sidebar-search"
        - type:
            into: "input.sidebar-search"
            text: "authentication"
            delay_ms: 25
        - press:
            selector: "input.sidebar-search"
            key: Enter
        - wait_for: "text=Search Results"
        - pause: 2

  Top-level YAML keys:

      output: WebM filename. -o/--output overrides this. With --mp4, an MP4
        is also written using the same filename with the suffix replaced by
        .mp4.
      url: Starting URL, bare domain, or local HTML path. Omit this only if
        the first scene has open:.
      sh: Shell command string or argument list to run before python: and
        server:.
      python: Python code to run after sh: and before server:.
      server: Optional command string or argument list to run while recording.
      viewport: Mapping with width: and height:. Defaults to 1280 by 720.
      cursor: true, false, or a mapping with visible, clicks, color, size and
        click_size.
      wait: Seconds to pause after the starting page loads.
      wait_for: Selector or Playwright text selector to wait for.
      wait_for_url: URL pattern to wait for.
      javascript: JavaScript to run before scene recording starts.
      scenes: Required list of scenes.

  Scene YAML keys:

      name: Label shown in progress output.
      open: URL/path to open at the start of this scene.
      wait_for: Selector to wait for.
      wait_for_url: URL pattern to wait for.
      sh: Shell command string or argument list to run before actions.
      python: Python code to run before actions.
      do: List of browser/page actions.

  Actions for a scene's do: list:

      - click: "selector"
      - click: {selector: "selector", button: right, count: 2}
      - fill: {into: "selector", text: "value"}
      - type: {into: "selector", text: "value", delay_ms: 25}
      - press: {selector: "selector", key: "ControlOrMeta+A"}
      - scroll: {x: 0, y: 500, duration: 0.5}
      - scroll: {to: "selector", duration: 0.5}
      - pause: 1.5
      - wait_for: "selector"
      - wait_for_url: "**/finished"
      - open: "installation.html"
      - js: "document.body.dataset.demo = '1'"
      - screenshot: output.png
      - screenshot: {output: heading.png, selector: "h1"}
      - sh: "echo scene > scene.txt"
      - python: "open('scene.txt', 'w').write('ok')"

  For full YAML syntax documentation, see:
  https://shot-scraper.datasette.io/en/stable/video.html

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
  --leave-server                  Leave servers running when script finishes
  --mp4                           Also convert the recorded WebM video to MP4
                                  using ffmpeg
  --help                          Show this message and exit.
```
<!-- [[[end]]] -->
