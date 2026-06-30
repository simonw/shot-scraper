import pathlib
import sys
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import textwrap
from click.testing import CliRunner
import pytest
import shot_scraper.cli as cli_module
from shot_scraper.cli import cli
import zipfile
import json
from conftest import find_free_port


def test_version():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert result.output.startswith("cli, version ")


SERVER_YAML = """
- server: python -m http.server 9023
- url: http://localhost:9023/
  output: output.png
""".strip()

SERVER_YAML2 = """
- server:
  - python
  - -m
  - http.server
  - 9023
- url: http://localhost:9023/
  output: output.png
""".strip()

COMMANDS_YAML = """
- sh: echo "hello world" > index.html
- sh:
  - touch
  - touched.html
- python: |
    content = open("index.html").read()
    open("index.html", "w").write(content.upper())
"""


@pytest.mark.parametrize("yaml", (SERVER_YAML, SERVER_YAML2))
def test_multi_server(yaml):
    runner = CliRunner()
    with runner.isolated_filesystem():
        open("server.yaml", "w").write(yaml)
        result = runner.invoke(cli, ["multi", "server.yaml"])
        assert result.exit_code == 0, result.output
        assert pathlib.Path("output.png").exists()


def test_multi_commands():
    runner = CliRunner()
    with runner.isolated_filesystem():
        yaml_file = "commands.yaml"
        open(yaml_file, "w").write(COMMANDS_YAML)
        result = runner.invoke(cli, ["multi", yaml_file], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert pathlib.Path("touched.html").exists()
        assert pathlib.Path("index.html").exists()
        assert open("index.html").read().strip() == "HELLO WORLD"


@pytest.mark.parametrize(
    ("yaml", "expected"),
    (
        (
            """
- sh: exit 3
- sh: touch should-not-run
""".strip(),
            "Error: sh command exited with status 3\n",
        ),
        (
            """
- python: |
    raise SystemExit(4)
- sh: touch should-not-run
""".strip(),
            "Error: python code exited with status 4\n",
        ),
    ),
)
def test_multi_commands_fail_on_non_zero_exit(yaml, expected):
    runner = CliRunner()
    with runner.isolated_filesystem():
        yaml_file = "commands.yaml"
        open(yaml_file, "w").write(yaml)
        result = runner.invoke(cli, ["multi", yaml_file])
        assert result.exit_code == 1
        assert result.output == expected
        assert not pathlib.Path("should-not-run").exists()


@pytest.mark.parametrize("input", ("key: value", "This is a string", "3.55"))
def test_multi_error_on_non_list(input):
    runner = CliRunner()
    result = runner.invoke(cli, ["multi", "-"], input=input)
    assert result.exit_code == 1
    assert result.output == "Error: YAML file must contain a list\n"


@pytest.mark.parametrize(
    "args,expected_shot_count",
    (
        ([], 2),
        (["--no-clobber"], 1),
        (["-n"], 1),
    ),
)
def test_multi_noclobber(mocker, args, expected_shot_count):
    take_shot = mocker.patch("shot_scraper.cli.take_shot")
    runner = CliRunner()
    with runner.isolated_filesystem():
        yaml = textwrap.dedent("""
        - url: https://www.example.com/
          output: example.jpg
        - url: https://www.google.com/
          output: google.jpg
        """).strip()
        open("shots.yaml", "w").write(yaml)
        open("example.jpg", "wb").write(b"")
        result = runner.invoke(cli, ["multi", "shots.yaml"] + args, input=yaml)
        assert result.exit_code == 0, str(result.exception)
        assert take_shot.call_count == expected_shot_count


TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Test title</title>
</head>
<body>
<h1>Test</h1>
<p>Paragraph 1</p>
</body>
</html>
"""


@pytest.mark.parametrize(
    "args,expected",
    (
        (["document.title"], '"Test title"\n'),
        (["document.title", "-r"], "Test title"),
        (["document.title", "--raw"], "Test title"),
        (["4 * 5"], "20\n"),
        (["4 * 5", "--raw"], "20"),
    ),
)
def test_javascript(args, expected):
    runner = CliRunner()
    with runner.isolated_filesystem():
        open("index.html", "w").write(TEST_HTML)
        result = runner.invoke(cli, ["javascript", "index.html"] + args)
        assert result.exit_code == 0, str(result.exception)
        assert result.output == expected


def test_javascript_input_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        open("index.html", "w").write(TEST_HTML)
        open("script.js", "w").write("document.title")
        result = runner.invoke(cli, ["javascript", "index.html", "-i", "script.js"])
        assert result.exit_code == 0, str(result.exception)
        assert result.output == '"Test title"\n'


def test_javascript_input_github():
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b"document.title"
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value = mock_response
    mock_context = MagicMock()
    mock_context.return_value = mock_urlopen

    runner = CliRunner()
    with patch("urllib.request.urlopen", mock_context):
        with runner.isolated_filesystem():
            open("index.html", "w").write(TEST_HTML)
            result = runner.invoke(
                cli, ["javascript", "index.html", "-i", "gh:simonw/title"]
            )
            assert result.exit_code == 0, str(result.exception)
            assert result.output == '"Test title"\n'
            mock_context.assert_called_once_with(
                "https://raw.githubusercontent.com/simonw/shot-scraper-scripts/main/title.js"
            )


@pytest.mark.parametrize(
    "args,expected",
    (
        ([], TEST_HTML),
        (
            ["-j", "document.body.removeChild(document.querySelector('h1'))"],
            (
                "<!DOCTYPE html><html><head><title>Test title</title></head>"
                "<body><p>Paragraph 1</p></body></html>"
            ),
        ),
        (
            [
                "-j",
                "document.querySelector('h1').innerText = navigator.userAgent",
                "--user-agent",
                "boo",
            ],
            (
                "<!DOCTYPE html><html><head><title>Test title</title></head>"
                "<body><h1>boo</h1><p>Paragraph 1</p></body></html>"
            ),
        ),
        (
            [
                "-s",
                "h1",
            ],
            ("<h1>Test</h1>"),
        ),
    ),
)
def test_html(args, expected):
    runner = CliRunner()
    with runner.isolated_filesystem():
        open("index.html", "w").write(TEST_HTML)
        result = runner.invoke(cli, ["html", "index.html"] + args)
        assert result.exit_code == 0, result.output
        # Whitespace is not preserved
        assert result.output.replace("\n", "") == expected.replace("\n", "")


@pytest.mark.parametrize(
    "yaml,expected",
    (
        ("", "Error: Storyboard YAML file cannot be empty\n"),
        ("- output: demo.webm", "Error: Storyboard YAML file must contain a mapping\n"),
        (
            "url: https://example.com/\nscenes:\n- name: one\n",
            "Error: Storyboard must define output: or use --output\n",
        ),
        (
            "output: demo.webm\nurl: https://example.com/\n",
            "Error: Storyboard must define a non-empty scenes: list\n",
        ),
        (
            "output: demo.webm\nscenes:\n- name: one\n",
            "Error: Storyboard must define url: or open: in the first scene\n",
        ),
        (
            """output: demo.webm
url: https://example.com/
scenes:
- do:
  - fill:
      into: "#q"
""",
            "Error: scenes.0.do.0.fill.text: Field required\n",
        ),
        (
            """output: demo.webm
url: https://example.com/
scenes:
- name: one
  banana: true
""",
            "Error: scenes.0.banana: Extra inputs are not permitted\n",
        ),
    ),
)
def test_video_validation(yaml, expected):
    runner = CliRunner()
    result = runner.invoke(cli, ["video", "-"], input=yaml)
    assert result.exit_code == 1
    assert result.output == expected


def test_video_help_documents_storyboard_format():
    runner = CliRunner()
    result = runner.invoke(cli, ["video", "--help"])
    assert result.exit_code == 0
    assert "Example storyboard.yml:" in result.output
    assert (
        "      output: demo.webm\n"
        "      url: https://shot-scraper.datasette.io/en/stable/"
    ) in result.output
    assert "      - name: Open installation docs" in result.output
    assert (
        "        - click: \".sidebar-tree a[href='installation.html']\""
        in result.output
    )
    assert "        - wait_for: 'h1:has-text(\"Installation\")'" in result.output
    assert "      - name: Search the docs" in result.output
    assert '        - click: "input.sidebar-search"' in result.output
    assert "Top-level YAML keys:" in result.output
    assert "Scene YAML keys:" in result.output
    assert "Actions for a scene's do: list:" in result.output
    assert '      - click: "selector"' in result.output
    assert (
        '      - type: {into: "selector", text: "value", delay_ms: 25}' in result.output
    )
    assert "  --mp4" in result.output
    assert "\b" not in result.output


def test_video_records_video():
    runner = CliRunner()
    port = find_free_port()
    with runner.isolated_filesystem():
        pathlib.Path("index.html").write_text("""<!DOCTYPE html>
<html>
<body style="min-height: 1600px">
    <h1>Home</h1>
    <a id="more" href="/more.html">More</a>
</body>
</html>""")
        pathlib.Path("more.html").write_text("""<!DOCTYPE html>
<html>
<body style="min-height: 1600px">
    <h1 id="more-heading">More information</h1>
    <input id="search">
    <p class="ready">Ready</p>
</body>
</html>""")
        pathlib.Path("storyboard.yml").write_text(f"""
output: demo.webm
server:
- {sys.executable}
- -m
- http.server
- {port}
url: http://localhost:{port}/
cursor: true
viewport:
  width: 640
  height: 360
scenes:
  - name: Home
    sh: echo "scene shell" > scene-shell.txt
    python: |
      open("scene-python.txt", "w").write("scene python")
    wait_for: "#shot-scraper-cursor"
    do:
      - wait_for: "#more"
      - pause: 0.1
  - name: Details
    do:
      - click: "#more"
      - wait_for: "#more-heading"
      - fill:
          into: "#search"
          text: "shot-scraper"
      - press:
          selector: "#search"
          key: "Control+A"
      - type:
          into: "#search"
          text: "storyboard"
          delay_ms: 5
      - screenshot: details.png
      - screenshot:
          output: heading.png
          selector: "#more-heading"
      - sh: echo "action shell" > action-shell.txt
      - python: |
          open("action-python.txt", "w").write("action python")
      - scroll:
          y: 200
          duration: 0.05
      - js: document.body.dataset.storyboard = "yes"
      - pause: 0.1
""".strip())
        result = runner.invoke(cli, ["video", "storyboard.yml"])
        assert result.exit_code == 0, result.output
        assert "Recording video to 'demo.webm'" in result.output
        assert "Scene 1: Home" in result.output
        assert "Scene 2: Details" in result.output
        assert "Video written to 'demo.webm'" in result.output
        video = pathlib.Path("demo.webm")
        assert video.exists()
        assert video.stat().st_size > 0
        for filename in ("details.png", "heading.png"):
            screenshot = pathlib.Path(filename)
            assert screenshot.exists()
            assert screenshot.stat().st_size > 0
        assert pathlib.Path("scene-shell.txt").read_text().strip() == "scene shell"
        assert pathlib.Path("scene-python.txt").read_text() == "scene python"
        assert pathlib.Path("action-shell.txt").read_text().strip() == "action shell"
        assert pathlib.Path("action-python.txt").read_text() == "action python"


@pytest.mark.parametrize(
    ("output_filename", "mp4_filename"),
    (
        ("demo.webm", "demo.mp4"),
        ("recording.video", "recording.mp4"),
        ("demo", "demo.mp4"),
    ),
)
def test_video_mp4_converts_webm_after_recording(mocker, output_filename, mp4_filename):
    runner = CliRunner()
    events = []

    def record_storyboard(storyboard_config, **kwargs):
        events.append(("record", storyboard_config.output))
        pathlib.Path(storyboard_config.output).write_bytes(b"webm")

    def run_ffmpeg(args, **kwargs):
        events.append(("ffmpeg", args, kwargs))
        assert pathlib.Path(args[3]).exists()
        pathlib.Path(args[-1]).write_bytes(b"mp4")
        return cli_module.subprocess.CompletedProcess(args, 0)

    mocker.patch.object(cli_module, "_record_storyboard", side_effect=record_storyboard)
    mocker.patch.object(cli_module.subprocess, "run", side_effect=run_ffmpeg)

    with runner.isolated_filesystem():
        pathlib.Path("storyboard.yml").write_text("""
output: {output_filename}
url: https://example.com/
scenes:
- name: One
  do:
  - pause: 0.1
""".format(output_filename=output_filename).strip())
        result = runner.invoke(cli, ["video", "storyboard.yml", "--mp4"])

        assert result.exit_code == 0, result.output
        assert pathlib.Path(output_filename).read_bytes() == b"webm"
        assert pathlib.Path(mp4_filename).read_bytes() == b"mp4"
        assert events == [
            ("record", output_filename),
            (
                "ffmpeg",
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    output_filename,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    mp4_filename,
                ],
                {"check": True, "capture_output": True, "text": True},
            ),
        ]
        assert f"MP4 written to '{mp4_filename}'" in result.output


def test_video_mp4_missing_ffmpeg_leaves_webm(mocker):
    runner = CliRunner()

    def record_storyboard(storyboard_config, **kwargs):
        pathlib.Path(storyboard_config.output).write_bytes(b"webm")

    mocker.patch.object(cli_module, "_record_storyboard", side_effect=record_storyboard)
    mocker.patch.object(
        cli_module.subprocess,
        "run",
        side_effect=FileNotFoundError("ffmpeg"),
    )

    with runner.isolated_filesystem():
        pathlib.Path("storyboard.yml").write_text("""
output: demo.webm
url: https://example.com/
scenes:
- name: One
  do:
  - pause: 0.1
""".strip())
        result = runner.invoke(cli, ["video", "storyboard.yml", "--mp4"])

        assert result.exit_code == 1
        assert pathlib.Path("demo.webm").read_bytes() == b"webm"
        assert not pathlib.Path("demo.mp4").exists()
        assert (
            "Error: WebM was created, but MP4 conversion failed: ffmpeg is not "
            "installed or not on PATH\n"
        ) in result.output


def test_video_starts_screencast_after_initial_navigation(mocker):
    events = []

    class FakeScreencast:
        def start(self, path, size):
            events.append(("start", path, size))

        def stop(self):
            events.append("stop")

    class FakePage:
        screencast = FakeScreencast()

        def __init__(self):
            self.closed = False

        def set_viewport_size(self, viewport):
            events.append(("viewport", viewport))

        def is_closed(self):
            return self.closed

        def close(self):
            events.append("page.close")
            self.closed = True

    class FakeContext:
        def __init__(self, page):
            self.page = page

        def new_page(self):
            return self.page

        def close(self):
            events.append("context.close")

    class FakeBrowser:
        def close(self):
            events.append("browser.close")

    class FakePlaywright:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            pass

    fake_page = FakePage()
    fake_context = FakeContext(fake_page)
    fake_browser = FakeBrowser()
    browser_context = mocker.patch.object(
        cli_module,
        "_browser_context",
        return_value=(fake_context, fake_browser),
    )
    mocker.patch.object(cli_module, "sync_playwright", return_value=FakePlaywright())
    mocker.patch.object(
        cli_module,
        "_storyboard_goto",
        side_effect=lambda *args, **kwargs: events.append("goto"),
    )
    mocker.patch.object(
        cli_module,
        "_run_storyboard_scene",
        side_effect=lambda *args, **kwargs: events.append("scene"),
    )

    storyboard_config = SimpleNamespace(
        output="demo.webm",
        url="https://example.com/",
        sh=None,
        python=None,
        server=None,
        cursor=None,
        wait=None,
        wait_for=None,
        wait_for_url=None,
        javascript=None,
        scenes=[SimpleNamespace(name="Scene")],
        viewport_size=lambda: {"width": 640, "height": 360},
    )

    cli_module._record_storyboard(storyboard_config, silent=True)

    assert events[:4] == [
        ("viewport", {"width": 640, "height": 360}),
        "goto",
        ("start", "demo.webm", {"width": 640, "height": 360}),
        "scene",
    ]
    assert "stop" in events
    assert browser_context.call_args.kwargs["viewport"] == {
        "width": 640,
        "height": 360,
    }


def test_video_runs_top_level_setup_before_server(mocker):
    events = []

    class FakeScreencast:
        def start(self, path, size):
            events.append(("start", path, size))

        def stop(self):
            events.append("stop")

    class FakePage:
        screencast = FakeScreencast()

        def __init__(self):
            self.closed = False

        def set_viewport_size(self, viewport):
            events.append(("viewport", viewport))

        def is_closed(self):
            return self.closed

        def close(self):
            events.append("page.close")
            self.closed = True

    class FakeContext:
        def __init__(self, page):
            self.page = page

        def new_page(self):
            return self.page

        def close(self):
            events.append("context.close")

    class FakeBrowser:
        def close(self):
            events.append("browser.close")

    class FakePlaywright:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            pass

    class FakeServerProcess:
        def kill(self):
            events.append("server.kill")

    fake_page = FakePage()
    fake_context = FakeContext(fake_page)
    fake_browser = FakeBrowser()
    mocker.patch.object(
        cli_module,
        "_browser_context",
        return_value=(fake_context, fake_browser),
    )
    mocker.patch.object(cli_module, "sync_playwright", return_value=FakePlaywright())
    mocker.patch.object(
        cli_module,
        "_run_sh_command",
        side_effect=lambda command: events.append(("sh", command)),
    )
    mocker.patch.object(
        cli_module,
        "_run_python_code",
        side_effect=lambda code: events.append(("python", code)),
    )
    mocker.patch.object(
        cli_module,
        "_start_server",
        side_effect=lambda server: (
            events.append(("server", server)) or (FakeServerProcess(), server)
        ),
    )
    mocker.patch.object(
        cli_module.time,
        "sleep",
        side_effect=lambda seconds: events.append(("sleep", seconds)),
    )
    mocker.patch.object(
        cli_module,
        "_run_storyboard_scene",
        side_effect=lambda *args, **kwargs: events.append("scene"),
    )

    storyboard_config = SimpleNamespace(
        output="demo.webm",
        url=None,
        sh="setup shell",
        python="setup python",
        server="serve",
        cursor=None,
        wait=None,
        wait_for=None,
        wait_for_url=None,
        javascript=None,
        scenes=[SimpleNamespace(name="Scene")],
        viewport_size=lambda: {"width": 640, "height": 360},
    )

    cli_module._record_storyboard(storyboard_config, silent=True)

    assert events[:4] == [
        ("sh", "setup shell"),
        ("python", "setup python"),
        ("server", "serve"),
        ("sleep", 1),
    ]
    assert "scene" in events
    assert events[-1] == "server.kill"


@pytest.mark.parametrize(
    "command,args,expected",
    [
        (
            "shot",
            ["--retina", "--scale-factor", 3],
            "Error: --retina and --scale-factor cannot be used together\n",
        ),
        (
            "multi",
            ["--retina", "--scale-factor", 3],
            "Error: --retina and --scale-factor cannot be used together\n",
        ),
        (
            "shot",
            ["--scale-factor", 0],
            "Error: --scale-factor must be positive\n",
        ),
        (
            "multi",
            ["--scale-factor", 0],
            "Error: --scale-factor must be positive\n",
        ),
        (
            "shot",
            ["--scale-factor", -3],
            "Error: --scale-factor must be positive\n",
        ),
        (
            "multi",
            ["--scale-factor", -3],
            "Error: --scale-factor must be positive\n",
        ),
    ],
)
def test_error_on_invalid_scale_factors(command, args, expected):
    runner = CliRunner()
    result = runner.invoke(cli, [command, "-"] + args)
    assert result.exit_code == 1
    assert result.output == expected


@pytest.mark.parametrize(
    "args,expect_zip",
    (
        ([], False),
        (["--zip"], True),
        (["--output", "output.har"], False),
        (["-o", "output.har"], False),
        (["--output", "output.har.zip"], True),
        (["-o", "output.har.zip"], True),
    ),
)
def test_har(http_server, args, expect_zip):
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Should be no files
        here = pathlib.Path(".")
        assert list(here.glob("*.*")) == []
        result = runner.invoke(cli, ["har", http_server.base_url] + args)
        assert result.exit_code == 0
        # HAR file should have been created
        if expect_zip:
            files = here.glob("*.har.zip")
        else:
            files = here.glob("*.har")
        har_files = list(files)
        # Should have created exactly one .har file
        assert len(har_files) == 1
        if expect_zip:
            with zipfile.ZipFile(har_files[0]) as zip_file:
                file_list = zip_file.namelist()
                assert any(".html" in file for file in file_list)
                assert "har.har" in file_list
                with zip_file.open("har.har") as har_file:
                    har_content = json.loads(har_file.read())
        else:
            with open(har_files[0]) as har_file:
                har_content = json.load(har_file)
        # HAR should have expected shape
        assert "log" in har_content
        assert "entries" in har_content["log"]
        # Verify entries is a non-empty list
        assert isinstance(har_content["log"]["entries"], list)
        assert len(har_content["log"]["entries"]) > 0


@pytest.mark.parametrize(
    "args,expect_zip,record_shots",
    (
        (["--har"], False, True),
        (["--har-zip"], True, True),
        (["--har-file", "output.har"], False, True),
        (["--har-file", "output.har.zip"], True, True),
        # And one where we don't record the shots:
        (["--har"], False, False),
    ),
)
def test_multi_har(http_server, args, expect_zip, record_shots):
    runner = CliRunner()
    (http_server.base_dir / "two.html").write_text("<h1>Two</h1>")
    with runner.isolated_filesystem():
        pathlib.Path("shots.yml").write_text(
            f"- url: {http_server.base_url}/\n"
            + ("  output: index.png\n" if record_shots else "")
            + f"- url: {http_server.base_url}/two.html\n"
            + ("  output: two.png\n" if record_shots else "")
        )
        # Should be no files
        here = pathlib.Path(".")
        files = [str(p) for p in here.glob("*.*")]
        assert files == ["shots.yml"]
        result = runner.invoke(cli, ["multi", "shots.yml"] + args)
        assert result.exit_code == 0
        if record_shots:
            assert result.output.startswith("Screenshot of 'http://localhost")
        else:
            assert result.output.startswith("Skipping screenshot of 'http://localhost")
        assert "Wrote to HAR file:" in result.output
        assert (".har.zip" in result.output) == expect_zip
        # HAR file should have been created
        if expect_zip:
            files = here.glob("*.har.zip")
        else:
            files = here.glob("*.har")
        har_files = list(files)
        # Should have created exactly one .har file
        assert len(har_files) == 1
        assert bool(zipfile.is_zipfile(har_files[0])) == expect_zip
        shot_files = list(here.glob("*.png"))
        num_shots = len(shot_files)
        if record_shots:
            assert num_shots == 2
        else:
            assert num_shots == 0


@pytest.mark.parametrize(
    "args,expect_zip",
    (
        (["--extract"], False),
        (["-x"], False),
        (["--extract", "--zip"], True),
        (["-x", "-z"], True),
        (["--extract", "-o", "output.har"], False),
        (["-x", "-o", "output.har.zip"], True),
        (["--extract", "-o", "basepath"], False),  # base path without extension
        (["-x", "-z", "-o", "basepath"], True),  # base path with zip
    ),
)
def test_har_extract(http_server, args, expect_zip):
    """Test that --extract creates a directory with HAR resources."""
    runner = CliRunner()
    # Create additional files on the server with different content types
    (http_server.base_dir / "style.css").write_text("body { color: red; }")
    (http_server.base_dir / "script.js").write_text("console.log('hello');")
    # Create an HTML file that references the CSS and JS
    (http_server.base_dir / "page.html").write_text("""<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="style.css">
    <script src="script.js"></script>
</head>
<body>Hello</body>
</html>""")
    with runner.isolated_filesystem():
        here = pathlib.Path(".")
        result = runner.invoke(cli, ["har", f"{http_server.base_url}/page.html"] + args)
        assert result.exit_code == 0, result.output

        # HAR file should have been created
        if expect_zip:
            har_files = list(here.glob("*.har.zip"))
        else:
            har_files = list(here.glob("*.har"))
        assert len(har_files) == 1
        har_file = har_files[0]

        # Extract directory should have been created
        if expect_zip:
            extract_dir_name = str(har_file.name).replace(".har.zip", "")
        else:
            extract_dir_name = str(har_file.name).replace(".har", "")
        extract_dir = here / extract_dir_name
        assert extract_dir.exists(), f"Extract directory {extract_dir} should exist"
        assert extract_dir.is_dir(), f"{extract_dir} should be a directory"

        # Should contain extracted files
        extracted_files = list(extract_dir.glob("*"))
        assert len(extracted_files) >= 1, "Should have extracted at least one file"

        # Check that at least the main HTML file was extracted
        html_files = list(extract_dir.glob("*.html"))
        assert len(html_files) >= 1, "Should have extracted at least one HTML file"


def test_har_extract_filenames(http_server):
    """Test that extracted files have correct names based on URLs."""
    runner = CliRunner()
    (http_server.base_dir / "api").mkdir()
    (http_server.base_dir / "api" / "data.json").write_text('{"key": "value"}')
    # Create an HTML page that loads the JSON
    (http_server.base_dir / "loader.html").write_text(
        '<html><script src="api/data.json"></script></html>'
    )
    with runner.isolated_filesystem():
        here = pathlib.Path(".")
        result = runner.invoke(
            cli,
            [
                "har",
                f"{http_server.base_url}/loader.html",
                "--extract",
                "-o",
                "test.har",
            ],
        )
        assert result.exit_code == 0, result.output

        extract_dir = here / "test"
        assert extract_dir.exists()

        extracted_files = list(extract_dir.glob("*"))
        assert len(extracted_files) >= 1
        # The /api/data.json file should be extracted with derived name
        file_names = [f.name for f in extracted_files]
        assert any(
            "api-data" in name for name in file_names
        ), f"Expected api-data in {file_names}"


def test_har_extract_content_type_extension(http_server):
    """Test that extracted files have correct extension based on content-type."""
    runner = CliRunner()
    # Create an HTML file that will be served with text/html content-type
    (http_server.base_dir / "test-page.html").write_text(
        "<html><body>Test page</body></html>"
    )
    with runner.isolated_filesystem():
        here = pathlib.Path(".")
        result = runner.invoke(
            cli,
            [
                "har",
                f"{http_server.base_url}/test-page.html",
                "--extract",
                "-o",
                "test.har",
            ],
        )
        assert result.exit_code == 0, result.output

        extract_dir = here / "test"
        assert extract_dir.exists()

        # The file should have .html extension based on content-type text/html
        html_files = list(extract_dir.glob("*.html"))
        assert (
            len(html_files) >= 1
        ), f"Should have .html file, got: {list(extract_dir.glob('*'))}"
