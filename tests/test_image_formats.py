from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from shot_scraper.cli import cli


@pytest.fixture
def image_runner():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("page.html").write_text(
            '<html><body style="margin: 0">'
            '<div id="target" style="width: 100px; height: 60px; '
            'background: linear-gradient(to right, red, blue)">Screenshot</div>'
            "</body></html>"
        )
        yield runner


def assert_image_format(content, image_format, lossless=None):
    if image_format == "png":
        assert content.startswith(b"\x89PNG\r\n\x1a\n")
    elif image_format == "jpeg":
        assert content.startswith(b"\xff\xd8\xff")
        assert content.endswith(b"\xff\xd9")
    else:
        assert content[:4] == b"RIFF"
        assert content[8:12] == b"WEBP"
        # Read RIFF chunks instead of searching the compressed image payload.
        chunks = []
        offset = 12
        while offset + 8 <= len(content):
            chunks.append(content[offset : offset + 4])
            size = int.from_bytes(content[offset + 4 : offset + 8], "little")
            offset += 8 + size + (size % 2)
        if lossless is not None:
            assert (b"VP8L" if lossless else b"VP8 ") in chunks


@pytest.mark.parametrize(
    "output,options,image_format,lossless",
    [
        ("image.webp", [], "webp", True),
        ("image.WEBP", ["--quality", "80"], "webp", False),
        ("image.png", ["--format", "WeBp"], "webp", True),
        ("image.webp", ["--format", "png"], "png", None),
        ("image.webp", ["--format", "jpeg"], "jpeg", None),
        ("image.png", [], "png", None),
        ("image.jpg", [], "jpeg", None),
        ("image.jpeg", [], "jpeg", None),
        ("image.png", ["--quality", "80"], "jpeg", None),
    ],
)
def test_shot_file_format(image_runner, output, options, image_format, lossless):
    result = image_runner.invoke(
        cli, ["page.html", "-o", output, "--width", "120", *options]
    )
    assert result.exit_code == 0, result.output
    assert_image_format(Path(output).read_bytes(), image_format, lossless)


@pytest.mark.parametrize(
    "options,output,image_format,lossless",
    [
        ([], "page-html.png", "png", None),
        (["--format", "webp"], "page-html.webp", "webp", True),
        (["--format", "jpeg"], "page-html.jpg", "jpeg", None),
        (["--quality", "0"], "page-html.jpg", "jpeg", None),
        (
            ["--format", "webp", "--quality", "0"],
            "page-html.webp",
            "webp",
            False,
        ),
    ],
)
def test_shot_automatic_filename(image_runner, options, output, image_format, lossless):
    result = image_runner.invoke(cli, ["page.html", "--width", "120", *options])
    assert result.exit_code == 0, result.output
    assert_image_format(Path(output).read_bytes(), image_format, lossless)


@pytest.mark.parametrize(
    "quality,selector,lossless", [(None, None, True), (80, "#target", False)]
)
def test_webp_stdout(image_runner, quality, selector, lossless):
    options = [] if quality is None else ["--quality", str(quality)]
    if selector:
        options.extend(["--selector", selector])
    result = image_runner.invoke(
        cli,
        [
            "page.html",
            "--format",
            "webp",
            "-o",
            "-",
            "--width",
            "120",
            *options,
        ],
    )
    assert result.exit_code == 0, result.output
    assert_image_format(result.stdout_bytes, "webp", lossless)
    assert sorted(path.name for path in Path().iterdir()) == ["page.html"]


def test_multi_image_formats(image_runner):
    shots = [
        {"output": "page.webp"},
        {"output": "lossless.webp", "quality": 100},
        {"output": "lossy.webp", "quality": 80},
        {"output": "minimum.webp", "quality": 0},
        {"output": "selector.webp", "selector": "#target", "quality": 80},
        {"output": "explicit.png", "format": "WEBP", "selector": "#target"},
        {"output": "png.webp", "format": "png"},
        {"output": "legacy.png", "quality": 80},
        {"format": "webp"},
        {"format": "jpeg"},
        {},
    ]
    Path("shots.yml").write_text(
        yaml.safe_dump([{"url": "page.html", "width": 120, **shot} for shot in shots])
    )
    result = image_runner.invoke(cli, ["multi", "shots.yml"])
    assert result.exit_code == 0, result.output

    for output, lossless in (
        ("page.webp", True),
        ("lossless.webp", True),
        ("lossy.webp", False),
        ("minimum.webp", False),
        ("selector.webp", False),
        ("explicit.png", True),
    ):
        assert_image_format(Path(output).read_bytes(), "webp", lossless)
    assert_image_format(Path("png.webp").read_bytes(), "png")
    assert_image_format(Path("legacy.png").read_bytes(), "jpeg")

    # Local URLs may include the absolute file path in multi's generated name.
    for suffix, image_format in (("webp", "webp"), ("jpg", "jpeg"), ("png", "png")):
        generated = list(Path().glob(f"*page-html.{suffix}"))
        assert len(generated) == 1
        assert_image_format(generated[0].read_bytes(), image_format)


@pytest.mark.parametrize(
    "options,error",
    [
        (["--quality", "-1"], "0<=x<=100"),
        (["--quality", "101"], "0<=x<=100"),
        (["--quality", "80.5"], "integer"),
        (["--format", "png", "--quality", "0"], "quality"),
        (["--format", "gif"], "Invalid value for '--format'"),
    ],
)
def test_invalid_cli_format_options(image_runner, mocker, options, error):
    playwright = mocker.patch("shot_scraper.cli.sync_playwright")
    result = image_runner.invoke(cli, ["page.html", *options])
    assert result.exit_code != 0
    assert error in result.output
    playwright.assert_not_called()


@pytest.mark.parametrize(
    "options,error",
    [
        ({"quality": -1}, "quality"),
        ({"quality": 101}, "quality"),
        ({"quality": 80.5}, "quality"),
        ({"quality": "80"}, "quality"),
        ({"quality": True}, "quality"),
        ({"format": "png", "quality": 0}, "quality"),
        ({"format": "gif"}, "format"),
        ({"format": ["webp"]}, "format"),
    ],
)
def test_invalid_yaml_format_options(image_runner, mocker, options, error):
    mocker.patch("shot_scraper.cli.sync_playwright")
    context = mocker.MagicMock()
    mocker.patch(
        "shot_scraper.cli._browser_context",
        return_value=(context, mocker.MagicMock()),
    )
    Path("shots.yml").write_text(
        yaml.safe_dump([{"url": "page.html", "output": "image.webp", **options}])
    )
    result = image_runner.invoke(cli, ["multi", "shots.yml"])
    assert result.exit_code != 0
    assert error in result.output
    context.new_page.assert_not_called()
    assert not Path("image.webp").exists()
