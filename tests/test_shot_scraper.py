from click.testing import CliRunner
import pytest
import textwrap
from shot_scraper.cli import cli


def test_version():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert result.output.startswith("cli, version ")


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
