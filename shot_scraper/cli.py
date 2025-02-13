import click
from click_default_group import DefaultGroup
import json
import os
import pathlib
from playwright.sync_api import sync_playwright, Error, TimeoutError
from runpy import run_module
import secrets
import subprocess
import sys
import textwrap
import time
import yaml

from shot_scraper.utils import filename_for_url, url_or_file_path

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
                "{} error for {}, skipping".format(response.status, response.url),
                err=True,
            )
            # Exit with a 0 status code
            raise SystemExit
        elif fail:
            raise click.ClickException(
                "{} error for {}".format(response.status, response.url)
            )


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
@scale_factor_options
@click.option(
    "--omit-background",
    is_flag=True,
    help="Omit the default browser background from the shot, making it possible take advantage of transparence. Does not work with JPEGs or when using --quality.",
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
):
    browser_kwargs = dict(
        headless=not interactive, devtools=devtools, args=browser_args
    )
    if browser == "chromium":
        browser_obj = p.chromium.launch(**browser_kwargs)
    elif browser == "firefox":
        browser_obj = p.firefox.launch(**browser_kwargs)
    elif browser == "webkit":
        browser_obj = p.webkit.launch(**browser_kwargs)
    else:
        browser_kwargs["channel"] = browser
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
    context = browser_obj.new_context(**context_args)
    if timeout:
        context.set_default_timeout(timeout)
    return context, browser_obj


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
                    sh = shot["sh"]
                    if isinstance(sh, str):
                        subprocess.run(shot["sh"], shell=True)
                    elif isinstance(sh, list):
                        subprocess.run(sh)
                    else:
                        raise click.ClickException("- sh: must be a string or list")
                # And "python" key
                if shot.get("python"):
                    subprocess.run([sys.executable, "-c", shot["python"]])
                if "server" in shot:
                    # Start that subprocess and remember the pid
                    server = shot["server"]
                    proc = None
                    if isinstance(server, str):
                        proc = subprocess.Popen(server, shell=True)
                    elif isinstance(server, list):
                        proc = subprocess.Popen(map(str, server))
                    else:
                        raise click.ClickException("server: must be a string or list")
                    server_processes.append((proc, server))
                    time.sleep(1)
                if "url" in shot:
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
            if leave_server:
                for process, details in server_processes:
                    click.echo(
                        f"Leaving server PID: {process.pid} details: {details}",
                        err=True,
                    )
            else:
                if server_processes:
                    for process, _ in server_processes:
                        process.kill()
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
        snapshot = page.accessibility.snapshot()
        browser_obj.close()
    output.write(json.dumps(snapshot, indent=4))
    output.write("\n")


@cli.command()
@click.argument("url")
@click.option("zip_", "-z", "--zip", is_flag=True, help="Save as a .har.zip file")
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
    auth,
    output,
    timeout,
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
    """
    if output is None:
        output = filename_for_url(
            url, ext="har.zip" if zip_ else "har", file_exists=os.path.exists
        )

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
        context.close()
        browser_obj.close()


@cli.command()
@click.argument("url")
@click.argument("javascript", required=False)
@click.option(
    "-i",
    "--input",
    type=click.File("r"),
    default="-",
    help="Read input JavaScript from this file",
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
        javascript = input.read()
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
@click.option(
    "--wait", type=int, help="Wait this many milliseconds before taking the screenshot"
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
    wait,
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
            click.echo("PDF of '{}' written to '{}'".format(url, output), err=True)

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
                    "HTML snapshot of '{}' written to '{}'".format(url, output),
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
                click.echo(
                    "{} error for {}, skipping".format(response.status, url), err=True
                )
                return
            elif fail:
                raise click.ClickException(
                    "{} error for {}".format(response.status, url)
                )

    if wait:
        time.sleep(wait / 1000)

    javascript = shot.get("javascript")
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
                "Timed out while waiting for element to become available.\n\n{}".format(
                    e
                )
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
                message = "Screenshot of '{}' written to '{}'".format(url, output)

    if not silent:
        click.echo(message, err=True)


def _js_selector_javascript(js_selectors, js_selectors_all):
    extra_selectors = []
    extra_selectors_all = []
    js_blocks = []
    for js_selector in js_selectors:
        klass = "js-selector-{}".format(secrets.token_hex(16))
        extra_selectors.append(".{}".format(klass))
        js_blocks.append(
            textwrap.dedent(
                """
        Array.from(
          document.getElementsByTagName('*')
        ).find(el => {}).classList.add("{}");
        """.format(
                    js_selector, klass
                )
            )
        )
    for js_selector_all in js_selectors_all:
        klass = "js-selector-all-{}".format(secrets.token_hex(16))
        extra_selectors_all.append(".{}".format(klass))
        js_blocks.append(
            textwrap.dedent(
                """
        Array.from(
          document.getElementsByTagName('*')
        ).filter(el => {}).forEach(el => el.classList.add("{}"));
        """.format(
                    js_selector_all, klass
                )
            )
        )
    js_selector_javascript = "() => {" + "\n".join(js_blocks) + "}"
    return js_selector_javascript, extra_selectors, extra_selectors_all


def _selector_javascript(selectors, selectors_all, padding=0):
    selector_to_shoot = "shot-scraper-{}".format(secrets.token_hex(8))
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
