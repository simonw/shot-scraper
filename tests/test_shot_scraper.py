import pathlib
from unittest.mock import patch, MagicMock
import textwrap
from click.testing import CliRunner
import pytest
from shot_scraper.cli import cli
import zipfile
import json


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
        yaml = textwrap.dedent(
            """
        - url: https://www.example.com/
          output: example.jpg
        - url: https://www.google.com/
          output: google.jpg
        """
        ).strip()
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
            + (f"  output: index.png\n" if record_shots else "")
            + f"- url: {http_server.base_url}/two.html\n"
            + (f"  output: two.png\n" if record_shots else "")
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
