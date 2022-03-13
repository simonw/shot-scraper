from shot_scraper.utils import filename_for_url
import pytest


@pytest.mark.parametrize(
    "url,ext,expected",
    (
        ("https://datasette.io/", None, "datasette-io.png"),
        ("https://datasette.io/tutorials", "png", "datasette-io-tutorials.png"),
        (
            "https://datasette.io/-/versions.json",
            "jpg",
            "datasette-io---versions-json.jpg",
        ),
        ("/tmp/index.html", "png", "tmp-index-html.png"),
    ),
)
def test_filename_for_url(url, ext, expected):
    assert filename_for_url(url, ext) == expected


@pytest.mark.parametrize(
    "url,existing_files,expected",
    (
        ("https://datasette.io/", [], "datasette-io.png"),
        ("https://datasette.io/", ["datasette-io.png"], "datasette-io.1.png"),
        (
            "https://datasette.io/",
            ["datasette-io.png", "datasette-io.1.png"],
            "datasette-io.2.png",
        ),
    ),
)
def test_filename_for_url_if_exists(url, existing_files, expected):
    assert filename_for_url(url, file_exists=lambda s: s in existing_files) == expected
