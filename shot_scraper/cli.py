import base64
import secrets
import socket
import subprocess
import sys
import textwrap
import time
import json
import os
import pathlib
import urllib.parse
import zipfile
from runpy import run_module
from click_default_group import DefaultGroup
import yaml
import click
from playwright.sync_api import sync_playwright, Error, TimeoutError


from shot_scraper.video import (
    ClickAction,
    FillAction,
    JavascriptAction,
    OpenAction,
    PauseAction,
    PressAction,
    PythonAction,
    ScreenshotAction,
    ShAction,
    ScrollAction,
    StoryboardError,
    TypeAction,
    WaitForAction,
    WaitForUrlAction,
    load_storyboard,
)
from shot_scraper.utils import (
    filename_for_url,
    filename_for_har_entry,
    load_github_script,
    url_or_file_path,
)

BROWSERS = ("chromium", "firefox", "webkit", "chrome", "chrome-beta")


def console_log(msg):
    click.echo(msg, err=True)


def browser_option(fn):
    click.option(
        "--browser",
        "-b",
        default="chromium",
        type=click.Choice(BROWSERS, case_sensitive=False),
        help="Which browser to use",
    )(fn)
    return fn


def browser_args_option(fn):
    click.option(
        "browser_args",
        "--browser-arg",
        multiple=True,
        help="Additional arguments to pass to the browser",
    )(fn)
    return fn


def user_agent_option(fn):
    click.option("--user-agent", help="User-Agent header to use")(fn)
    return fn


def log_console_option(fn):
    click.option("--log-console", is_flag=True, help="Write console.log() to stderr")(
        fn
    )
    return fn


def silent_option(fn):
    click.option("--silent", is_flag=True, help="Do not output any messages")(fn)
    return fn


def skip_fail_options(fn):
    click.option("--skip", is_flag=True, help="Skip pages that return HTTP errors")(fn)
    click.option(
        "--fail",
        is_flag=True,
        help="Fail with an error code if a page returns an HTTP error",
    )(fn)
    return fn


def bypass_csp_option(fn):
    click.option("--bypass-csp", is_flag=True, help="Bypass Content-Security-Policy")(
        fn
    )
    return fn


def http_auth_options(fn):
    click.option("--auth-username", help="Username for HTTP Basic authentication")(fn)
    click.option("--auth-password", help="Password for HTTP Basic authentication")(fn)
    return fn


def skip_or_fail(response, skip, fail):
    if skip and fail:
        raise click.ClickException("--skip and --fail cannot be used together")
    if str(response.status)[0] in ("4", "5"):
        if skip:
            click.echo(
                f"{response.status} error for {response.url}, skipping",
                err=True,
            )
            # Exit with a 0 status code
            raise SystemExit
        elif fail:
            raise click.ClickException(f"{response.status} error for {response.url}")


def scale_factor_options(fn):
    click.option(
        "--retina",
        is_flag=True,
        help="Use device scale factor of 2. Cannot be used together with '--scale-factor'.",
    )(fn)
    click.option(
        "--scale-factor",
        type=float,
        help="Device scale factor. Cannot be used together with '--retina'.",
    )(fn)
    return fn


def normalize_scale_factor(retina, scale_factor):
    if retina and scale_factor:
        raise click.ClickException(
            "--retina and --scale-factor cannot be used together"
        )
    if scale_factor is not None and scale_factor <= 0.0:
        raise click.ClickException("--scale-factor must be positive")
    if retina:
        scale_factor = 2
    return scale_factor


def reduced_motion_option(fn):
    click.option(
        "--reduced-motion",
        is_flag=True,
        help="Emulate 'prefers-reduced-motion' media feature",
    )(fn)
    return fn


def javascript_file_option(fn):
    click.option(
        "--javascript-file",
        help=(
            "Read JavaScript to execute from this file, use - for stdin "
            "or gh:username/script to load from "
            "github.com/username/shot-scraper-scripts/script.js"
        ),
    )(fn)
    return fn


def _load_javascript_source(source):
    "Load JavaScript from a file path, '-' for stdin or gh:username/script"
    if source.startswith("gh:"):
        try:
            return load_github_script(source[3:])
        except ValueError as ex:
            raise click.ClickException(str(ex))
    if source == "-":
        return sys.stdin.read()
    try:
        with open(source, "r") as f:
            return f.read()
    except Exception as e:
        raise click.ClickException(f"Failed to read file '{source}': {e}")


def _resolve_javascript(javascript, javascript_file):
    if javascript and javascript_file:
        raise click.ClickException(
            "Cannot use both javascript and javascript-file"
        )
    if javascript_file:
        return _load_javascript_source(javascript_file)
    return javascript


@click.group(
    cls=DefaultGroup,
    default="shot",
    default_if_no_args=True,
    context_settings=dict(help_option_names=["--help"]),
)
@click.version_option()
def cli():
    "Tools for taking automated screenshots"
    pass


@cli.command()
@click.argument("url")  # TODO: validate with custom type
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option(
    "-w",
    "--width",
    type=int,
    help="Width of browser window, defaults to 1280",
    default=1280,
)
@click.option(
    "-h",
    "--height",
    type=int,
    help="Height of browser window and shot - defaults to the full height of the page",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=True, writable=True, dir_okay=False, allow_dash=True),
)
@click.option(
    "selectors",
    "-s",
    "--selector",
    help="Take shot of first element matching this CSS selector",
    multiple=True,
)
@click.option(
    "selectors_all",
    "--selector-all",
    help="Take shot of all elements matching this CSS selector",
    multiple=True,
)
@click.option(
    "js_selectors",
    "--js-selector",
    help="Take shot of first element matching this JS (el) expression",
    multiple=True,
)
@click.option(
    "js_selectors_all",
    "--js-selector-all",
    help="Take shot of all elements matching this JS (el) expression",
    multiple=True,
)
@click.option(
    "-p",
    "--padding",
    type=int,
    help="When using selectors, add this much padding in pixels",
    default=0,
)
@click.option("-j", "--javascript", help="Execute this JS prior to taking the shot")
@javascript_file_option
@scale_factor_options
@click.option(
    "--omit-background",
    is_flag=True,
    help="Omit the default browser background from the shot, making it possible take advantage of transparency. Does not work with JPEGs or when using --quality.",
)
@click.option("--quality", type=int, help="Save as JPEG with this quality, e.g. 80")
@click.option(
    "--wait", type=int, help="Wait this many milliseconds before taking the screenshot"
)
@click.option("--wait-for", help="Wait until this JS expression returns true")
@click.option(
    "--timeout",
    type=int,
    help="Wait this many milliseconds before failing",
)
@click.option(
    "-i",
    "--interactive",
    is_flag=True,
    help="Interact with the page in a browser before taking the shot",
)
@click.option(
    "--devtools",
    is_flag=True,
    help="Interact mode with developer tools",
)
@click.option(
    "--log-requests",
    type=click.File("w"),
    help="Log details of all requests to this file",
)
@log_console_option
@browser_option
@browser_args_option
@user_agent_option
@reduced_motion_option
@skip_fail_options
@bypass_csp_option
@silent_option
@http_auth_options
def shot(
    url,
    auth,
    output,
    width,
    height,
    selectors,
    selectors_all,
    js_selectors,
    js_selectors_all,
    padding,
    javascript,
    javascript_file,
    retina,
    scale_factor,
    omit_background,
    quality,
    wait,
    wait_for,
    timeout,
    interactive,
    devtools,
    log_requests,
    log_console,
    browser,
    browser_args,
    user_agent,
    reduced_motion,
    skip,
    fail,
    bypass_csp,
    silent,
    auth_username,
    auth_password,
):
    """
    Take a single screenshot of a page or portion of a page.

    Usage:

        shot-scraper www.example.com

    This will write the screenshot to www-example-com.png

    Use "-o" to write to a specific file:

        shot-scraper https://www.example.com/ -o example.png

    You can also pass a path to a local file on disk:

        shot-scraper index.html -o index.png

    Using "-o -" will output to standard out:

        shot-scraper https://www.example.com/ -o - > example.png

    Use -s to take a screenshot of one area of the page, identified using
    one or more CSS selectors:

        shot-scraper https://simonwillison.net -s '#bighead'
    """
    javascript = _resolve_javascript(javascript, javascript_file)
    if output is None:
        ext = "jpg" if quality else None
        output = filename_for_url(url, ext=ext, file_exists=os.path.exists)

    scale_factor = normalize_scale_factor(retina, scale_factor)

    shot = {
        "url": url,
        "selectors": selectors,
        "selectors_all": selectors_all,
        "js_selectors": js_selectors,
        "js_selectors_all": js_selectors_all,
        "javascript": javascript,
        "width": width,
        "height": height,
        "quality": quality,
        "wait": wait,
        "wait_for": wait_for,
        "timeout": timeout,
        "padding": padding,
        "omit_background": omit_background,
        "scale_factor": scale_factor,
    }
    interactive = interactive or devtools
    with sync_playwright() as p:
        use_existing_page = False
        context, browser_obj = _browser_context(
            p,
            auth,
            interactive=interactive,
            devtools=devtools,
            scale_factor=scale_factor,
            browser=browser,
            browser_args=browser_args,
            user_agent=user_agent,
            timeout=timeout,
            reduced_motion=reduced_motion,
            bypass_csp=bypass_csp,
            auth_username=auth_username,
            auth_password=auth_password,
        )
        if interactive or devtools:
            use_existing_page = True
            page = context.new_page()
            if width or height:
                page.set_viewport_size(_get_viewport(width, height))
            page.goto(url)
            context = page
            click.echo(
                "Hit <enter> to take the shot and close the browser window:", err=True
            )
            input()
        try:
            if output == "-":
                shot = take_shot(
                    context,
                    shot,
                    return_bytes=True,
                    use_existing_page=use_existing_page,
                    log_requests=log_requests,
                    log_console=log_console,
                    silent=silent,
                )
                sys.stdout.buffer.write(shot)
            else:
                shot["output"] = str(output)
                shot = take_shot(
                    context,
                    shot,
                    use_existing_page=use_existing_page,
                    log_requests=log_requests,
                    log_console=log_console,
                    skip=skip,
                    fail=fail,
                    silent=silent,
                )
        except TimeoutError as e:
            raise click.ClickException(str(e))
        browser_obj.close()


def _browser_context(
    p,
    auth,
    interactive=False,
    devtools=False,
    scale_factor=None,
    browser="chromium",
    browser_args=None,
    user_agent=None,
    timeout=None,
    reduced_motion=False,
    bypass_csp=False,
    auth_username=None,
    auth_password=None,
    record_har_path=None,
    record_video_dir=None,
    record_video_size=None,
    viewport=None,
):
    # Playwright 1.58 removed the `devtools` launch option. Emulate the
    # previous behavior for Chromium by passing the corresponding flag.
    args = list(browser_args or [])
    browser_kwargs = dict(headless=not interactive, args=args)
    if browser == "chromium":
        if devtools and "--auto-open-devtools-for-tabs" not in args:
            args.append("--auto-open-devtools-for-tabs")
        browser_obj = p.chromium.launch(**browser_kwargs)
    elif browser == "firefox":
        browser_obj = p.firefox.launch(**browser_kwargs)
    elif browser == "webkit":
        browser_obj = p.webkit.launch(**browser_kwargs)
    else:
        browser_kwargs["channel"] = browser
        if devtools and "--auto-open-devtools-for-tabs" not in args:
            args.append("--auto-open-devtools-for-tabs")
        browser_obj = p.chromium.launch(**browser_kwargs)
    context_args = {}
    if auth:
        context_args["storage_state"] = json.load(auth)
    if scale_factor:
        context_args["device_scale_factor"] = scale_factor
    if reduced_motion:
        context_args["reduced_motion"] = "reduce"
    if user_agent is not None:
        context_args["user_agent"] = user_agent
    if bypass_csp:
        context_args["bypass_csp"] = bypass_csp
    if auth_username and auth_password:
        context_args["http_credentials"] = {
            "username": auth_username,
            "password": auth_password,
        }
    if record_har_path:
        context_args["record_har_path"] = record_har_path
    if record_video_dir:
        context_args["record_video_dir"] = record_video_dir
    if record_video_size:
        context_args["record_video_size"] = record_video_size
    if viewport:
        context_args["viewport"] = viewport
    context = browser_obj.new_context(**context_args)
    if timeout:
        context.set_default_timeout(timeout)
    return context, browser_obj


@cli.command()
@click.argument("storyboard_file", type=click.File(mode="r"))
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=True, writable=True, dir_okay=False, allow_dash=False),
    help="Output video filename (.webm), overriding output: in the storyboard",
)
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option(
    "--timeout",
    type=int,
    help="Wait this many milliseconds before failing",
)
@browser_option
@browser_args_option
@user_agent_option
@reduced_motion_option
@log_console_option
@skip_fail_options
@bypass_csp_option
@silent_option
@http_auth_options
@click.option(
    "leave_server",
    "--leave-server",
    is_flag=True,
    help="Leave servers running when script finishes",
)
@click.option(
    "--mp4",
    is_flag=True,
    help="Also convert the recorded WebM video to MP4 using ffmpeg",
)
def video(
    storyboard_file,
    output,
    auth,
    timeout,
    browser,
    browser_args,
    user_agent,
    reduced_motion,
    log_console,
    skip,
    fail,
    bypass_csp,
    silent,
    auth_username,
    auth_password,
    leave_server,
    mp4,
):
    """
    Record a WebM video from a YAML storyboard.

    Common usage:

    \b
        shot-scraper video storyboard.yml
        shot-scraper video storyboard.yml -o demo.webm --mp4

    A storyboard is a YAML mapping with an output filename, a starting URL (or
    an opening scene), and a list of scenes. Each scene can wait, run commands,
    run browser actions, and pause between steps.

    Example storyboard.yml:

    \b
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

    \b
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

    \b
        name: Label shown in progress output.
        open: URL/path to open at the start of this scene.
        wait_for: Selector to wait for.
        wait_for_url: URL pattern to wait for.
        sh: Shell command string or argument list to run before actions.
        python: Python code to run before actions.
        do: List of browser/page actions.

    Actions for a scene's do: list:

    \b
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

    \b
    For full YAML syntax documentation, see:
    https://shot-scraper.datasette.io/en/stable/video.html
    """
    try:
        storyboard_config = load_storyboard(storyboard_file)
    except StoryboardError as ex:
        raise click.ClickException(str(ex))
    if output:
        storyboard_config = storyboard_config.model_copy(update={"output": output})
    try:
        _record_storyboard(
            storyboard_config,
            auth=auth,
            timeout=timeout,
            browser=browser,
            browser_args=browser_args,
            user_agent=user_agent,
            reduced_motion=reduced_motion,
            log_console=log_console,
            skip=skip,
            fail=fail,
            bypass_csp=bypass_csp,
            silent=silent,
            auth_username=auth_username,
            auth_password=auth_password,
            leave_server=leave_server,
        )
        if mp4:
            _convert_video_to_mp4(storyboard_config.output, silent=silent)
    except TimeoutError as e:
        raise click.ClickException(str(e))


def _convert_video_to_mp4(output, silent=False):
    mp4_output = str(pathlib.Path(output).with_suffix(".mp4"))
    args = [
        "ffmpeg",
        "-y",
        "-i",
        output,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        mp4_output,
    ]
    try:
        subprocess.run(args, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise click.ClickException(
            "WebM was created, but MP4 conversion failed: ffmpeg is not installed "
            "or not on PATH"
        )
    except subprocess.CalledProcessError as ex:
        reason = (ex.stderr or ex.stdout or "").strip()
        if not reason:
            reason = f"ffmpeg exited with status {ex.returncode}"
        raise click.ClickException(
            f"WebM was created, but MP4 conversion failed: {reason}"
        )
    if not silent:
        click.echo(f"MP4 written to '{mp4_output}'", err=True)
    return mp4_output


@cli.command()
@click.argument("config", type=click.File(mode="r"))
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@scale_factor_options
@click.option(
    "--timeout",
    type=int,
    help="Wait this many milliseconds before failing",
)
# Hidden because will be removed if I release shot-scraper 2.0
# See https://github.com/simonw/shot-scraper/issues/103
@click.option(
    "--fail-on-error", is_flag=True, help="Fail noisily on error", hidden=True
)
@click.option(
    "noclobber",
    "-n",
    "--no-clobber",
    is_flag=True,
    help="Skip images that already exist",
)
@click.option(
    "outputs",
    "-o",
    "--output",
    help="Just take shots matching these output files",
    multiple=True,
)
@browser_option
@browser_args_option
@user_agent_option
@reduced_motion_option
@log_console_option
@skip_fail_options
@silent_option
@http_auth_options
@click.option(
    "leave_server",
    "--leave-server",
    is_flag=True,
    help="Leave servers running when script finishes",
)
@click.option(
    "--har",
    is_flag=True,
    help="Save all requests to trace.har file",
)
@click.option(
    "--har-zip",
    is_flag=True,
    help="Save all requests to trace.har.zip file",
)
@click.option(
    "--har-file",
    type=click.Path(file_okay=True, writable=True, dir_okay=False),
    help="Path to HAR file to save all requests",
)
def multi(
    config,
    auth,
    retina,
    scale_factor,
    timeout,
    fail_on_error,
    noclobber,
    outputs,
    browser,
    browser_args,
    user_agent,
    reduced_motion,
    log_console,
    skip,
    fail,
    silent,
    auth_username,
    auth_password,
    leave_server,
    har,
    har_zip,
    har_file,
):
    """
    Take multiple screenshots, defined by a YAML file

    Usage:

        shot-scraper multi config.yml

    Where config.yml contains configuration like this:

    \b
        - output: example.png
          url: http://www.example.com/

    \b
    For full YAML syntax documentation, see:
    https://shot-scraper.datasette.io/en/stable/multi.html
    """
    if (har or har_zip) and not har_file:
        har_file = filename_for_url(
            "trace", ext="har.zip" if har_zip else "har", file_exists=os.path.exists
        )

    scale_factor = normalize_scale_factor(retina, scale_factor)
    shots = yaml.safe_load(config)

    # Special case: if we are recording a har_file output can be blank to skip a shot
    if har_file:
        for shot in shots:
            if not shot.get("output"):
                shot["skip_shot"] = True

    server_processes = []
    server_needs_ready_check = False
    if shots is None:
        shots = []
    if not isinstance(shots, list):
        raise click.ClickException("YAML file must contain a list")
    with sync_playwright() as p:
        context, browser_obj = _browser_context(
            p,
            auth,
            scale_factor=scale_factor,
            browser=browser,
            browser_args=browser_args,
            user_agent=user_agent,
            timeout=timeout,
            reduced_motion=reduced_motion,
            auth_username=auth_username,
            auth_password=auth_password,
            record_har_path=har_file or None,
        )
        try:
            for shot in shots:
                if (
                    noclobber
                    and shot.get("output")
                    and pathlib.Path(shot["output"]).exists()
                ):
                    continue
                if outputs and shot.get("output") and shot.get("output") not in outputs:
                    continue
                # Run "sh" key
                if shot.get("sh"):
                    _run_sh_command(shot["sh"])
                # And "python" key
                if shot.get("python"):
                    _run_python_code(shot["python"])
                if "server" in shot:
                    # Start that subprocess and remember the pid
                    server_processes.append(_start_server(shot["server"]))
                    server_needs_ready_check = True
                if "url" in shot:
                    if server_needs_ready_check:
                        _wait_for_server(
                            server_processes,
                            url_or_file_path(shot["url"], _check_and_absolutize),
                        )
                        server_needs_ready_check = False
                    try:
                        take_shot(
                            context,
                            shot,
                            log_console=log_console,
                            skip=skip,
                            fail=fail,
                            silent=silent,
                        )
                    except TimeoutError as e:
                        if fail or fail_on_error:
                            raise click.ClickException(str(e))
                        else:
                            click.echo(str(e), err=True)
                            continue
        finally:
            context.close()
            browser_obj.close()
            if server_processes:
                _cleanup_servers(server_processes, leave_server)
            if har_file and not silent:
                click.echo(f"Wrote to HAR file: {har_file}", err=True)


@cli.command()
@click.argument("url")
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option(
    "-o",
    "--output",
    type=click.File("w"),
    default="-",
)
@click.option("-j", "--javascript", help="Execute this JS prior to taking the snapshot")
@javascript_file_option
@click.option(
    "--timeout",
    type=int,
    help="Wait this many milliseconds before failing",
)
@log_console_option
@skip_fail_options
@bypass_csp_option
@http_auth_options
def accessibility(
    url,
    auth,
    output,
    javascript,
    javascript_file,
    timeout,
    log_console,
    skip,
    fail,
    bypass_csp,
    auth_username,
    auth_password,
):
    """
    Dump the Chromium accessibility tree for the specifed page

    Usage:

        shot-scraper accessibility https://datasette.io/
    """
    javascript = _resolve_javascript(javascript, javascript_file)
    url = url_or_file_path(url, _check_and_absolutize)
    with sync_playwright() as p:
        context, browser_obj = _browser_context(
            p,
            auth,
            timeout=timeout,
            bypass_csp=bypass_csp,
            auth_username=auth_username,
            auth_password=auth_password,
        )
        page = context.new_page()
        if log_console:
            page.on("console", console_log)
        response = page.goto(url)
        skip_or_fail(response, skip, fail)
        if javascript:
            _evaluate_js(page, javascript)
        snapshot = page.locator("body").aria_snapshot()
        browser_obj.close()
    # aria_snapshot() returns YAML, parse it for JSON output
    output.write(json.dumps(yaml.safe_load(snapshot), indent=4))
    output.write("\n")


@cli.command()
@click.argument("url")
@click.option("zip_", "-z", "--zip", is_flag=True, help="Save as a .har.zip file")
@click.option(
    "extract",
    "-x",
    "--extract",
    is_flag=True,
    help="Extract resources from the HAR file into a directory",
)
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=True, dir_okay=False, writable=True, allow_dash=False),
    help="HAR filename",
)
@click.option(
    "--wait", type=int, help="Wait this many milliseconds before taking the screenshot"
)
@click.option("--wait-for", help="Wait until this JS expression returns true")
@click.option("-j", "--javascript", help="Execute this JavaScript on the page")
@javascript_file_option
@click.option(
    "--timeout",
    type=int,
    help="Wait this many milliseconds before failing",
)
@log_console_option
@skip_fail_options
@bypass_csp_option
@http_auth_options
def har(
    url,
    zip_,
    extract,
    auth,
    output,
    wait,
    wait_for,
    timeout,
    javascript,
    javascript_file,
    log_console,
    skip,
    fail,
    bypass_csp,
    auth_username,
    auth_password,
):
    """
    Record a HAR file for the specified page

    Usage:

        shot-scraper har https://datasette.io/

    This defaults to saving to datasette-io.har - use -o to specify a different filename:

        shot-scraper har https://datasette.io/ -o trace.har

    Use --zip to save as a .har.zip file instead, or specify a filename ending in .har.zip

    Use --extract / -x to also extract all resources from the HAR into a directory.
    With -x, you can specify a base path and the .har extension will be added automatically:

        shot-scraper har https://datasette.io/ -x -o /tmp/datasette

    This creates /tmp/datasette.har and extracts resources to /tmp/datasette/
    """
    javascript = _resolve_javascript(javascript, javascript_file)
    if output is None:
        output = filename_for_url(
            url, ext="har.zip" if zip_ else "har", file_exists=os.path.exists
        )
    elif extract and not (output.endswith(".har") or output.endswith(".har.zip")):
        # When -x is used with -o that lacks .har extension, treat as base path
        output = output + (".har.zip" if zip_ else ".har")

    url = url_or_file_path(url, _check_and_absolutize)
    with sync_playwright() as p:
        context, browser_obj = _browser_context(
            p,
            auth,
            timeout=timeout,
            bypass_csp=bypass_csp,
            auth_username=auth_username,
            auth_password=auth_password,
            record_har_path=str(output),
        )
        page = context.new_page()
        if log_console:
            page.on("console", console_log)
        response = page.goto(url)
        skip_or_fail(response, skip, fail)
        if wait:
            time.sleep(wait / 1000)

        if javascript:
            _evaluate_js(page, javascript)

        if wait_for:
            page.wait_for_function(wait_for)

        context.close()
        browser_obj.close()

    if extract:
        _extract_har_resources(output)


def _extract_har_resources(har_path):
    """Extract resources from a HAR file into a directory."""
    har_path = pathlib.Path(har_path)

    # Determine if it's a zip file
    is_zip = zipfile.is_zipfile(har_path)

    # Determine extract directory name (parallel to har file)
    if str(har_path).endswith(".har.zip"):
        extract_dir = har_path.parent / har_path.name.replace(".har.zip", "")
    else:
        extract_dir = har_path.parent / har_path.name.replace(".har", "")

    # Create the extract directory
    extract_dir.mkdir(exist_ok=True)

    # Track existing files to handle duplicates
    existing_files = set()

    def file_exists_in_dir(filename):
        return filename in existing_files

    # Load the HAR data (and keep zip file open if needed)
    if is_zip:
        with zipfile.ZipFile(har_path) as zf:
            with zf.open("har.har") as har_file:
                har_data = json.load(har_file)

            # Extract each entry (with zip file open for _file references)
            for entry in har_data.get("log", {}).get("entries", []):
                _extract_har_entry(
                    entry, extract_dir, existing_files, file_exists_in_dir, zf
                )
    else:
        with open(har_path) as har_file:
            har_data = json.load(har_file)

        # Extract each entry
        for entry in har_data.get("log", {}).get("entries", []):
            _extract_har_entry(
                entry, extract_dir, existing_files, file_exists_in_dir, None
            )

    click.echo(f"Extracted resources to: {extract_dir}", err=True)


def _extract_har_entry(entry, extract_dir, existing_files, file_exists_fn, zip_file):
    """Extract a single HAR entry to the extract directory."""
    request = entry.get("request", {})
    response = entry.get("response", {})
    content = response.get("content", {})

    url = request.get("url", "")
    if not url:
        return

    # Get content-type from response headers
    content_type = None
    for header in response.get("headers", []):
        if header.get("name", "").lower() == "content-type":
            content_type = header.get("value", "")
            break

    # Get the content - either from text field or from _file reference in zip
    text = content.get("text", "")
    encoding = content.get("encoding", "")
    file_ref = content.get("_file", "")

    data = None

    if file_ref and zip_file:
        # Content is stored as a separate file in the zip
        try:
            with zip_file.open(file_ref) as f:
                data = f.read()
        except KeyError:
            pass
    elif text:
        # Decode the content from text field
        if encoding == "base64":
            try:
                data = base64.b64decode(text)
            except Exception:
                return
        else:
            data = text.encode("utf-8")

    if not data:
        return

    # Generate filename
    filename = filename_for_har_entry(url, content_type, file_exists=file_exists_fn)
    existing_files.add(filename)

    # Write the file
    file_path = extract_dir / filename
    file_path.write_bytes(data)


@cli.command()
@click.argument("url")
@click.argument("javascript", required=False)
@click.option(
    "-i",
    "--input",
    default="-",
    help=(
        "Read input JavaScript from this file or use gh:username/script "
        "to load from github.com/username/shot-scraper-scripts/script.js"
    ),
)
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option(
    "-w",
    "--width",
    type=int,
    help="Width of browser window, defaults to 1280",
    default=1280,
)
@click.option(
    "-h",
    "--height",
    type=int,
    help="Height of browser window, defaults to 720",
)
@click.option(
    "-o",
    "--output",
    type=click.File("w"),
    default="-",
    help="Save output JSON to this file",
)
@click.option(
    "-r",
    "--raw",
    is_flag=True,
    help="Output JSON strings as raw text",
)
@browser_option
@browser_args_option
@user_agent_option
@reduced_motion_option
@log_console_option
@skip_fail_options
@bypass_csp_option
@http_auth_options
def javascript(
    url,
    javascript,
    input,
    auth,
    width,
    height,
    output,
    raw,
    browser,
    browser_args,
    user_agent,
    reduced_motion,
    log_console,
    skip,
    fail,
    bypass_csp,
    auth_username,
    auth_password,
):
    """
    Execute JavaScript against the page and return the result as JSON

    Usage:

        shot-scraper javascript https://datasette.io/ "document.title"

    To return a JSON object, use this:

        "({title: document.title, location: document.location})"

    To use setInterval() or similar, pass a promise:

    \b
        "new Promise(done => setInterval(
          () => {
            done({
              title: document.title,
              h2: document.querySelector('h2').innerHTML
            });
          }, 1000
        ));"

    If a JavaScript error occurs an exit code of 1 will be returned.
    """
    if not javascript:
        javascript = _load_javascript_source(input)

    url = url_or_file_path(url, _check_and_absolutize)
    with sync_playwright() as p:
        context, browser_obj = _browser_context(
            p,
            auth,
            browser=browser,
            browser_args=browser_args,
            user_agent=user_agent,
            reduced_motion=reduced_motion,
            bypass_csp=bypass_csp,
            auth_username=auth_username,
            auth_password=auth_password,
        )
        page = context.new_page()
        if log_console:
            page.on("console", console_log)
        viewport = _get_viewport(width, height)
        if viewport:
            page.set_viewport_size(viewport)
        response = page.goto(url)
        skip_or_fail(response, skip, fail)
        result = _evaluate_js(page, javascript)
        browser_obj.close()
    if raw:
        output.write(str(result))
        return
    output.write(json.dumps(result, indent=4, default=str))
    output.write("\n")


@cli.command()
@click.argument("url")
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=True, writable=True, dir_okay=False, allow_dash=True),
)
@click.option("-j", "--javascript", help="Execute this JS prior to creating the PDF")
@javascript_file_option
@click.option(
    "--wait", type=int, help="Wait this many milliseconds before taking the screenshot"
)
@click.option("--wait-for", help="Wait until this JS expression returns true")
@click.option(
    "--timeout",
    type=int,
    help="Wait this many milliseconds before failing",
)
@click.option(
    "--media-screen", is_flag=True, help="Use screen rather than print styles"
)
@click.option("--landscape", is_flag=True, help="Use landscape orientation")
@click.option(
    "--format",
    "format_",
    type=click.Choice(
        [
            "Letter",
            "Legal",
            "Tabloid",
            "Ledger",
            "A0",
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
            "A6",
        ],
        case_sensitive=False,
    ),
    help="Which standard paper size to use",
)
@click.option("--width", help="PDF width including units, e.g. 10cm")
@click.option("--height", help="PDF height including units, e.g. 10cm")
@click.option(
    "--scale",
    type=click.FloatRange(min=0.1, max=2.0),
    help="Scale of the webpage rendering",
)
@click.option("--print-background", is_flag=True, help="Print background graphics")
@log_console_option
@skip_fail_options
@bypass_csp_option
@silent_option
@http_auth_options
def pdf(
    url,
    auth,
    output,
    javascript,
    javascript_file,
    wait,
    wait_for,
    timeout,
    media_screen,
    landscape,
    format_,
    width,
    height,
    scale,
    print_background,
    log_console,
    skip,
    fail,
    bypass_csp,
    silent,
    auth_username,
    auth_password,
):
    """
    Create a PDF of the specified page

    Usage:

        shot-scraper pdf https://datasette.io/

    Use -o to specify a filename:

        shot-scraper pdf https://datasette.io/ -o datasette.pdf

    You can pass a path to a file instead of a URL:

        shot-scraper pdf invoice.html -o invoice.pdf
    """
    javascript = _resolve_javascript(javascript, javascript_file)
    url = url_or_file_path(url, _check_and_absolutize)
    if output is None:
        output = filename_for_url(url, ext="pdf", file_exists=os.path.exists)
    with sync_playwright() as p:
        context, browser_obj = _browser_context(
            p,
            auth,
            bypass_csp=bypass_csp,
            auth_username=auth_username,
            auth_password=auth_password,
            timeout=timeout,
        )
        page = context.new_page()
        if log_console:
            page.on("console", console_log)
        response = page.goto(url)
        skip_or_fail(response, skip, fail)
        if wait:
            time.sleep(wait / 1000)
        if javascript:
            _evaluate_js(page, javascript)
        if wait_for:
            page.wait_for_function(wait_for)

        kwargs = {
            "landscape": landscape,
            "format": format_,
            "width": width,
            "height": height,
            "scale": scale,
            "print_background": print_background,
        }
        if output != "-":
            kwargs["path"] = output

        if media_screen:
            page.emulate_media(media="screen")

        pdf = page.pdf(**kwargs)

        if output == "-":
            sys.stdout.buffer.write(pdf)
        elif not silent:
            click.echo(f"PDF of '{url}' written to '{output}'", err=True)

        browser_obj.close()


@cli.command()
@click.argument("url")
@click.option(
    "-a",
    "--auth",
    type=click.File("r"),
    help="Path to JSON authentication context file",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=True, writable=True, dir_okay=False, allow_dash=True),
    default="-",
)
@click.option("-j", "--javascript", help="Execute this JS prior to saving the HTML")
@javascript_file_option
@click.option(
    "-s",
    "--selector",
    help="Return outerHTML of first element matching this CSS selector",
)
@click.option(
    "--wait", type=int, help="Wait this many milliseconds before taking the snapshot"
)
@log_console_option
@browser_option
@browser_args_option
@user_agent_option
@skip_fail_options
@bypass_csp_option
@silent_option
@http_auth_options
def html(
    url,
    auth,
    output,
    javascript,
    javascript_file,
    selector,
    wait,
    log_console,
    browser,
    browser_args,
    user_agent,
    skip,
    fail,
    bypass_csp,
    silent,
    auth_username,
    auth_password,
):
    """
    Output the final HTML of the specified page

    Usage:

        shot-scraper html https://datasette.io/

    Use -o to specify a filename:

        shot-scraper html https://datasette.io/ -o index.html
    """
    javascript = _resolve_javascript(javascript, javascript_file)
    url = url_or_file_path(url, _check_and_absolutize)
    if output is None:
        output = filename_for_url(url, ext="html", file_exists=os.path.exists)
    with sync_playwright() as p:
        context, browser_obj = _browser_context(
            p,
            auth,
            browser=browser,
            browser_args=browser_args,
            user_agent=user_agent,
            bypass_csp=bypass_csp,
            auth_username=auth_username,
            auth_password=auth_password,
        )
        page = context.new_page()
        if log_console:
            page.on("console", console_log)
        response = page.goto(url)
        skip_or_fail(response, skip, fail)
        if wait:
            time.sleep(wait / 1000)
        if javascript:
            _evaluate_js(page, javascript)

        if selector:
            html = page.query_selector(selector).evaluate("el => el.outerHTML")
        else:
            html = page.content()

        if output == "-":
            sys.stdout.write(html)
        else:
            open(output, "w").write(html)
            if not silent:
                click.echo(
                    f"HTML snapshot of '{url}' written to '{output}'",
                    err=True,
                )

        browser_obj.close()


@cli.command()
@click.option(
    "--browser",
    "-b",
    default="chromium",
    type=click.Choice(BROWSERS, case_sensitive=False),
    help="Which browser to install",
)
def install(browser):
    """
    Install the Playwright browser needed by this tool.

    Usage:

        shot-scraper install

    Or for browsers other than the Chromium default:

        shot-scraper install -b firefox
    """
    sys.argv = ["playwright", "install", browser]
    run_module("playwright", run_name="__main__")


@cli.command()
@click.argument("url")
@click.argument(
    "context_file",
    type=click.Path(file_okay=True, writable=True, dir_okay=False, allow_dash=True),
)
@browser_option
@browser_args_option
@user_agent_option
@click.option("--devtools", is_flag=True, help="Open browser DevTools")
@log_console_option
def auth(url, context_file, browser, browser_args, user_agent, devtools, log_console):
    """
    Open a browser so user can manually authenticate with the specified site,
    then save the resulting authentication context to a file.

    Usage:

        shot-scraper auth https://github.com/ auth.json
    """
    with sync_playwright() as p:
        context, browser_obj = _browser_context(
            p,
            auth=None,
            interactive=True,
            devtools=devtools,
            browser=browser,
            browser_args=browser_args,
            user_agent=user_agent,
        )
        context = browser_obj.new_context()
        page = context.new_page()
        if log_console:
            page.on("console", console_log)
        page.goto(url)
        click.echo("Hit <enter> after you have signed in:", err=True)
        input()
        context_state = context.storage_state()
    context_json = json.dumps(context_state, indent=2) + "\n"
    if context_file == "-":
        click.echo(context_json)
    else:
        with open(context_file, "w") as fp:
            fp.write(context_json)
        # chmod 600 to avoid other users on the shared machine reading it
        pathlib.Path(context_file).chmod(0o600)


def _check_and_absolutize(filepath):
    try:
        path = pathlib.Path(filepath)
        if path.exists():
            return path.absolute()
        return False
    except OSError:
        # On Windows, instantiating a Path object on `http://` or `https://` will raise an exception
        return False


def _run_sh_command(sh):
    try:
        if isinstance(sh, str):
            subprocess.run(sh, shell=True, check=True)
        elif isinstance(sh, list):
            subprocess.run(list(map(str, sh)), check=True)
        else:
            raise click.ClickException("- sh: must be a string or list")
    except FileNotFoundError as ex:
        raise click.ClickException(f"sh command failed: {ex}") from ex
    except subprocess.CalledProcessError as ex:
        raise click.ClickException(
            f"sh command exited with status {ex.returncode}"
        ) from ex


def _run_python_code(code):
    try:
        subprocess.run([sys.executable, "-c", code], check=True)
    except subprocess.CalledProcessError as ex:
        raise click.ClickException(
            f"python code exited with status {ex.returncode}"
        ) from ex


def _start_server(server):
    if isinstance(server, str):
        proc = subprocess.Popen(server, shell=True)
    elif isinstance(server, list):
        proc = subprocess.Popen(map(str, server))
    else:
        raise click.ClickException("server: must be a string or list")
    return proc, server


SERVER_READY_TIMEOUT = 30.0


def _wait_for_server(server_processes, url, timeout=SERVER_READY_TIMEOUT):
    """
    Wait until the host:port of url accepts TCP connections.

    Raises ClickException if a server process exits with a non-zero code
    while waiting. Returns after timeout seconds even if the port never
    opens, so that navigating to the URL can report its own error.
    """
    bits = urllib.parse.urlparse(url)
    if bits.scheme not in ("http", "https") or not bits.hostname:
        # Nothing to poll - fall back to the old fixed delay
        time.sleep(1)
        return
    port = bits.port or (443 if bits.scheme == "https" else 80)
    deadline = time.monotonic() + timeout
    while True:
        for process, details in server_processes:
            returncode = process.poll()
            if returncode:
                raise click.ClickException(
                    f"server: process exited with code {returncode}: {details}"
                )
        try:
            with socket.create_connection((bits.hostname, port), timeout=1):
                return
        except OSError:
            if time.monotonic() >= deadline:
                return
            time.sleep(0.05)


def _cleanup_servers(server_processes, leave_server):
    if leave_server:
        for process, details in server_processes:
            click.echo(
                f"Leaving server PID: {process.pid} details: {details}",
                err=True,
            )
    else:
        for process, _ in server_processes:
            process.kill()


def _record_storyboard(
    storyboard_config,
    auth=None,
    timeout=None,
    browser="chromium",
    browser_args=None,
    user_agent=None,
    reduced_motion=False,
    log_console=False,
    skip=False,
    fail=False,
    bypass_csp=False,
    silent=False,
    auth_username=None,
    auth_password=None,
    leave_server=False,
):
    if skip and fail:
        raise click.ClickException("--skip and --fail cannot be used together")

    output = storyboard_config.output
    if not output:
        raise click.ClickException("Storyboard must define output: or use --output")

    viewport = storyboard_config.viewport_size()
    start_url = storyboard_config.url
    server_processes = []

    try:
        if storyboard_config.sh is not None:
            _run_sh_command(storyboard_config.sh)
        if storyboard_config.python is not None:
            _run_python_code(storyboard_config.python)
        if storyboard_config.server is not None:
            server_processes.append(_start_server(storyboard_config.server))
            if start_url:
                _wait_for_server(
                    server_processes, _resolve_storyboard_url(start_url)
                )
            else:
                time.sleep(1)

        with sync_playwright() as p:
            context, browser_obj = _browser_context(
                p,
                auth,
                browser=browser,
                browser_args=browser_args,
                user_agent=user_agent,
                timeout=timeout,
                reduced_motion=reduced_motion,
                bypass_csp=bypass_csp,
                auth_username=auth_username,
                auth_password=auth_password,
                viewport=viewport,
            )
            if storyboard_config.cursor and (
                storyboard_config.cursor.visible or storyboard_config.cursor.clicks
            ):
                context.add_init_script(
                    _storyboard_cursor_script(storyboard_config.cursor)
                )
            page = context.new_page()
            context_closed = False
            recording_started = False
            page.set_viewport_size(viewport)
            if log_console:
                page.on("console", console_log)

            try:
                if not silent:
                    click.echo(f"Recording video to '{output}'", err=True)

                if start_url:
                    _storyboard_goto(
                        page,
                        start_url,
                        skip=skip,
                        fail=fail,
                    )

                if storyboard_config.wait is not None:
                    _storyboard_pause(storyboard_config.wait)
                if storyboard_config.wait_for:
                    _storyboard_wait_for(page, storyboard_config.wait_for)
                if storyboard_config.wait_for_url:
                    page.wait_for_url(storyboard_config.wait_for_url)
                if storyboard_config.javascript:
                    _evaluate_js(page, storyboard_config.javascript)

                page.screencast.start(path=output, size=viewport)
                recording_started = True
                for index, scene in enumerate(storyboard_config.scenes, 1):
                    _run_storyboard_scene(
                        page,
                        scene,
                        index=index,
                        skip=skip,
                        fail=fail,
                        silent=silent,
                    )

                page.screencast.stop()
                recording_started = False
                page.close()
                context.close()
                context_closed = True
            finally:
                if recording_started:
                    try:
                        page.screencast.stop()
                    except Error:
                        pass
                if not page.is_closed():
                    page.close()
                if not context_closed:
                    context.close()
                browser_obj.close()
    finally:
        if server_processes:
            _cleanup_servers(server_processes, leave_server)

    if not silent:
        click.echo(f"Video written to '{output}'", err=True)


def _run_storyboard_scene(page, scene, index, skip=False, fail=False, silent=False):
    name = scene.name or f"Scene {index}"
    if not silent:
        click.echo(f"Scene {index}: {name}", err=True)

    if scene.sh is not None:
        _run_sh_command(scene.sh)
    if scene.python is not None:
        _run_python_code(scene.python)

    if scene.open:
        _storyboard_goto(page, scene.open, skip=skip, fail=fail)
    if scene.wait_for:
        _storyboard_wait_for(page, scene.wait_for)
    if scene.wait_for_url:
        page.wait_for_url(scene.wait_for_url)

    for action_index, action in enumerate(scene.do, 1):
        _run_storyboard_action(page, action, index, action_index, skip=skip, fail=fail)


def _run_storyboard_action(
    page, action, scene_index, action_index, skip=False, fail=False
):
    if isinstance(action, ClickAction):
        click_kwargs = {}
        if action.button:
            click_kwargs["button"] = action.button
        if action.count:
            click_kwargs["click_count"] = action.count
        page.locator(action.selector).click(**click_kwargs)
    elif isinstance(action, TypeAction):
        type_kwargs = {}
        if action.delay_ms is not None:
            type_kwargs["delay"] = action.delay_ms
        page.locator(action.target_selector).type(action.text, **type_kwargs)
    elif isinstance(action, FillAction):
        page.locator(action.target_selector).fill(action.text)
    elif isinstance(action, PressAction):
        if action.selector:
            page.locator(action.selector).press(action.key)
        else:
            page.keyboard.press(action.key)
    elif isinstance(action, ScrollAction):
        _storyboard_scroll(page, action)
    elif isinstance(action, PauseAction):
        _storyboard_pause(action.seconds)
    elif isinstance(action, WaitForAction):
        _storyboard_wait_for(page, action.selector)
    elif isinstance(action, WaitForUrlAction):
        page.wait_for_url(action.url)
    elif isinstance(action, OpenAction):
        _storyboard_goto(page, action.url, skip=skip, fail=fail)
    elif isinstance(action, JavascriptAction):
        _evaluate_js(page, action.code)
    elif isinstance(action, ScreenshotAction):
        _storyboard_screenshot(page, action)
    elif isinstance(action, ShAction):
        _run_sh_command(action.command)
    elif isinstance(action, PythonAction):
        _run_python_code(action.code)
    else:
        raise click.ClickException(
            f"Unknown storyboard action in scene {scene_index} action {action_index}"
        )


def _storyboard_goto(page, url, skip=False, fail=False):
    resolved_url = _resolve_storyboard_url(url, page.url)
    response = page.goto(resolved_url)
    if response is not None:
        skip_or_fail(response, skip, fail)


def _resolve_storyboard_url(url, base_url=None):
    if not isinstance(url, str):
        raise click.ClickException("URL values must be strings")
    if pathlib.Path(url).exists():
        return url_or_file_path(url, _check_and_absolutize)
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme:
        return url
    if base_url and base_url != "about:blank":
        return urllib.parse.urljoin(base_url, url)
    return url_or_file_path(url, _check_and_absolutize)


def _storyboard_wait_for(page, selector):
    if not isinstance(selector, str):
        raise click.ClickException("wait_for: must be a selector string")
    page.locator(selector).wait_for()


def _storyboard_pause(seconds):
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        raise click.ClickException("pause values must be numbers")
    if seconds < 0:
        raise click.ClickException("pause values must not be negative")
    time.sleep(seconds)


def _storyboard_scroll(page, value):
    duration = value.duration

    if value.to:
        selector = value.to
        if duration:
            page.locator(selector).evaluate(
                "(el) => el.scrollIntoView({behavior: 'smooth', block: 'center'})"
            )
            time.sleep(duration)
        else:
            page.locator(selector).scroll_into_view_if_needed()
        return

    x = value.x
    y = value.y
    if duration:
        page.evaluate(
            """
            ({x, y, duration}) => new Promise(resolve => {
                const startX = window.scrollX;
                const startY = window.scrollY;
                const start = performance.now();
                const durationMs = duration * 1000;
                const ease = t => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
                const step = now => {
                    const progress = Math.min((now - start) / durationMs, 1);
                    window.scrollTo(startX + x * ease(progress), startY + y * ease(progress));
                    if (progress < 1) {
                        requestAnimationFrame(step);
                    } else {
                        resolve();
                    }
                };
                requestAnimationFrame(step);
            })
            """,
            {"x": x, "y": y, "duration": duration},
        )
    else:
        page.evaluate("({x, y}) => window.scrollBy(x, y)", {"x": x, "y": y})


def _storyboard_screenshot(page, action):
    if action.selector:
        page.locator(action.selector).screenshot(path=action.output)
    else:
        page.screenshot(path=action.output, full_page=action.full_page)


def _storyboard_cursor_script(cursor):
    options = json.dumps(
        {
            "visible": cursor.visible,
            "clicks": cursor.clicks,
            "color": cursor.color,
            "size": cursor.size,
            "clickSize": cursor.click_size,
        }
    )
    return f"""
(() => {{
    const options = {options};
    if (window.__shotScraperCursorInstalled) {{
        return;
    }}
    window.__shotScraperCursorInstalled = true;

    function install() {{
        if (!document.body) {{
            requestAnimationFrame(install);
            return;
        }}

        const style = document.createElement("style");
        style.textContent = `
            #shot-scraper-cursor {{
                position: fixed;
                left: 0;
                top: 0;
                width: ${{options.size}}px;
                height: ${{options.size}}px;
                margin-left: ${{-options.size / 2}}px;
                margin-top: ${{-options.size / 2}}px;
                border-radius: 999px;
                background: ${{options.color}};
                border: 2px solid white;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35);
                opacity: 0;
                pointer-events: none;
                z-index: 2147483647;
                transition: left 120ms ease-out, top 120ms ease-out, opacity 120ms ease-out;
            }}
            .shot-scraper-click-ring {{
                position: fixed;
                width: ${{options.clickSize}}px;
                height: ${{options.clickSize}}px;
                margin-left: ${{-options.clickSize / 2}}px;
                margin-top: ${{-options.clickSize / 2}}px;
                border: 3px solid ${{options.color}};
                border-radius: 999px;
                pointer-events: none;
                z-index: 2147483646;
                animation: shot-scraper-click-ring 650ms ease-out forwards;
            }}
            @keyframes shot-scraper-click-ring {{
                from {{
                    opacity: 0.85;
                    transform: scale(0.25);
                }}
                to {{
                    opacity: 0;
                    transform: scale(1.25);
                }}
            }}
        `;
        document.documentElement.appendChild(style);

        let cursor = null;
        if (options.visible) {{
            cursor = document.createElement("div");
            cursor.id = "shot-scraper-cursor";
            document.body.appendChild(cursor);
        }}

        function move(event) {{
            if (!cursor) {{
                return;
            }}
            cursor.style.left = `${{event.clientX}}px`;
            cursor.style.top = `${{event.clientY}}px`;
            cursor.style.opacity = "1";
        }}

        function ring(event) {{
            if (!options.clicks) {{
                return;
            }}
            const el = document.createElement("div");
            el.className = "shot-scraper-click-ring";
            el.style.left = `${{event.clientX}}px`;
            el.style.top = `${{event.clientY}}px`;
            document.body.appendChild(el);
            setTimeout(() => el.remove(), 700);
        }}

        document.addEventListener("mousemove", move, true);
        document.addEventListener("mousedown", event => {{
            move(event);
            ring(event);
        }}, true);
        document.addEventListener("click", move, true);
    }}

    install();
}})();
"""


def _get_viewport(width, height):
    if width or height:
        return {
            "width": width or 1280,
            "height": height or 720,
        }
    else:
        return {}


def take_shot(
    context_or_page,
    shot,
    return_bytes=False,
    use_existing_page=False,
    log_requests=None,
    log_console=False,
    skip=False,
    fail=False,
    silent=False,
):
    url = shot.get("url") or ""
    if not url:
        raise click.ClickException("url is required")

    if skip and fail:
        raise click.ClickException("--skip and --fail cannot be used together")

    url = url_or_file_path(url, file_exists=_check_and_absolutize)

    output = (shot.get("output") or "").strip()
    if not output and not return_bytes:
        output = filename_for_url(url, ext="png", file_exists=os.path.exists)
    quality = shot.get("quality")
    omit_background = shot.get("omit_background")
    wait = shot.get("wait")
    wait_for = shot.get("wait_for")
    padding = shot.get("padding") or 0

    selectors = shot.get("selectors") or []
    selectors_all = shot.get("selectors_all") or []
    js_selectors = shot.get("js_selectors") or []
    js_selectors_all = shot.get("js_selectors_all") or []
    # If a single 'selector' append to 'selectors' array (and 'js_selectors' etc)
    if shot.get("selector"):
        selectors.append(shot["selector"])
    if shot.get("selector_all"):
        selectors_all.append(shot["selector_all"])
    if shot.get("js_selector"):
        js_selectors.append(shot["js_selector"])
    if shot.get("js_selector_all"):
        js_selectors_all.append(shot["js_selector_all"])

    if not use_existing_page:
        page = context_or_page.new_page()
        if log_requests:

            def on_response(response):
                try:
                    body = response.body()
                    size = len(body)
                except Error:
                    size = None
                log_requests.write(
                    json.dumps(
                        {
                            "method": response.request.method,
                            "url": response.url,
                            "status": response.status,
                            "size": size,
                            "timing": response.request.timing,
                        }
                    )
                    + "\n"
                )

            page.on("response", on_response)
    else:
        page = context_or_page

    if log_console:
        page.on("console", console_log)

    viewport = _get_viewport(shot.get("width"), shot.get("height"))
    if viewport:
        page.set_viewport_size(viewport)

    full_page = not shot.get("height")

    if not use_existing_page:
        # Load page and check for errors
        response = page.goto(url)
        # Check if page was a 404 or 500 or other error
        if str(response.status)[0] in ("4", "5"):
            if skip:
                click.echo(f"{response.status} error for {url}, skipping", err=True)
                return
            elif fail:
                raise click.ClickException(f"{response.status} error for {url}")

    if wait:
        time.sleep(wait / 1000)

    javascript = _resolve_javascript(
        shot.get("javascript"), shot.get("javascript_file")
    )
    if javascript:
        _evaluate_js(page, javascript)

    if wait_for:
        page.wait_for_function(wait_for)

    screenshot_args = {}
    if quality:
        screenshot_args.update({"quality": quality, "type": "jpeg"})
    if omit_background:
        screenshot_args.update({"omit_background": True})
    if not return_bytes:
        screenshot_args["path"] = output

    if (
        not selectors
        and not js_selectors
        and not selectors_all
        and not js_selectors_all
    ):
        screenshot_args["full_page"] = full_page

    if js_selectors or js_selectors_all:
        # Evaluate JavaScript adding classes we can select on
        (
            js_selector_javascript,
            extra_selectors,
            extra_selectors_all,
        ) = _js_selector_javascript(js_selectors, js_selectors_all)
        selectors.extend(extra_selectors)
        selectors_all.extend(extra_selectors_all)
        _evaluate_js(page, js_selector_javascript)

    if selectors or selectors_all:
        # Use JavaScript to create a box around those elementsdef
        selector_javascript, selector_to_shoot = _selector_javascript(
            selectors, selectors_all, padding
        )
        _evaluate_js(page, selector_javascript)
        try:
            bytes_ = page.locator(selector_to_shoot).screenshot(**screenshot_args)
        except TimeoutError as e:
            raise click.ClickException(
                f"Timed out while waiting for element to become available.\n\n{e}"
            )
        if return_bytes:
            return bytes_
        else:
            page.locator(selector_to_shoot).screenshot(**screenshot_args)
            message = "Screenshot of '{}' on '{}' written to '{}'".format(
                ", ".join(list(selectors) + list(selectors_all)), url, output
            )
    else:
        if shot.get("skip_shot"):
            message = "Skipping screenshot of '{}'".format(url)
        else:
            # Whole page
            if return_bytes:
                return page.screenshot(**screenshot_args)
            else:
                page.screenshot(**screenshot_args)
                message = f"Screenshot of '{url}' written to '{output}'"

    if not silent:
        click.echo(message, err=True)


def _js_selector_javascript(js_selectors, js_selectors_all):
    extra_selectors = []
    extra_selectors_all = []
    js_blocks = []
    for js_selector in js_selectors:
        klass = f"js-selector-{secrets.token_hex(16)}"
        extra_selectors.append(f".{klass}")
        js_blocks.append(textwrap.dedent(f"""
        Array.from(
          document.getElementsByTagName('*')
        ).find(el => {js_selector}).classList.add("{klass}");
        """))
    for js_selector_all in js_selectors_all:
        klass = f"js-selector-all-{secrets.token_hex(16)}"
        extra_selectors_all.append(f".{klass}")
        js_blocks.append(textwrap.dedent("""
        Array.from(
          document.getElementsByTagName('*')
        ).filter(el => {}).forEach(el => el.classList.add("{}"));
        """.format(js_selector_all, klass)))
    js_selector_javascript = "() => {" + "\n".join(js_blocks) + "}"
    return js_selector_javascript, extra_selectors, extra_selectors_all


def _selector_javascript(selectors, selectors_all, padding=0):
    selector_to_shoot = f"shot-scraper-{secrets.token_hex(8)}"
    selector_javascript = textwrap.dedent(
        """
    new Promise(takeShot => {
        let padding = %s;
        let minTop = 100000000;
        let minLeft = 100000000;
        let maxBottom = 0;
        let maxRight = 0;
        let els = %s.map(s => document.querySelector(s));
        // Add the --selector-all elements
        %s.map(s => els.push(...document.querySelectorAll(s)));
        els.forEach(el => {
            let rect = el.getBoundingClientRect();
            if (rect.top < minTop) {
                minTop = rect.top;
            }
            if (rect.left < minLeft) {
                minLeft = rect.left;
            }
            if (rect.bottom > maxBottom) {
                maxBottom = rect.bottom;
            }
            if (rect.right > maxRight) {
                maxRight = rect.right;
            }
        });
        // Adjust them based on scroll position
        let top = minTop + window.scrollY;
        let bottom = maxBottom + window.scrollY;
        let left = minLeft + window.scrollX;
        let right = maxRight + window.scrollX;
        // Apply padding
        top = top - padding;
        bottom = bottom + padding;
        left = left - padding;
        right = right + padding;
        let div = document.createElement('div');
        div.style.position = 'absolute';
        div.style.top = top + 'px';
        div.style.left = left + 'px';
        div.style.width = (right - left) + 'px';
        div.style.height = (bottom - top) + 'px';
        div.style.maxWidth = 'none';
        div.setAttribute('id', %s);
        document.body.appendChild(div);
        setTimeout(() => {
            takeShot();
        }, 300);
    });
    """
        % (
            padding,
            json.dumps(selectors),
            json.dumps(selectors_all),
            json.dumps(selector_to_shoot),
        )
    )
    return selector_javascript, "#" + selector_to_shoot


def _evaluate_js(page, javascript):
    try:
        return page.evaluate(javascript)
    except Error as error:
        raise click.ClickException(error.message)
