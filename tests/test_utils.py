import pytest
from shot_scraper.utils import (
    filename_for_url,
    extension_for_content_type,
    filename_for_har_entry,
)


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


@pytest.mark.parametrize(
    "content_type,expected",
    (
        ("text/html", "html"),
        ("text/html; charset=utf-8", "html"),
        ("text/css", "css"),
        ("application/javascript", "js"),
        ("text/javascript", "js"),
        ("application/json", "json"),
        ("image/png", "png"),
        ("image/jpeg", "jpg"),
        ("image/gif", "gif"),
        ("image/webp", "webp"),
        ("image/svg+xml", "svg"),
        ("application/pdf", "pdf"),
        ("text/plain", "txt"),
        ("application/xml", "xml"),
        ("text/xml", "xml"),
        ("font/woff2", "woff2"),
        ("font/woff", "woff"),
        ("application/font-woff", "woff"),
        ("application/octet-stream", None),
        ("", None),
        (None, None),
    ),
)
def test_extension_for_content_type(content_type, expected):
    assert extension_for_content_type(content_type) == expected


@pytest.mark.parametrize(
    "url,content_type,existing_files,expected",
    (
        # URL has extension that matches content-type
        ("https://example.com/style.css", "text/css", [], "example-com-style.css"),
        # URL has extension that matches content-type (with charset)
        ("https://example.com/page.html", "text/html; charset=utf-8", [], "example-com-page.html"),
        # URL has no extension, use content-type
        ("https://example.com/api/data", "application/json", [], "example-com-api-data.json"),
        # URL has no extension and no content-type, use .bin
        ("https://example.com/api/data", None, [], "example-com-api-data.bin"),
        # URL has wrong extension, use content-type
        ("https://example.com/image.php", "image/png", [], "example-com-image-php.png"),
        # Handle duplicate files
        ("https://example.com/style.css", "text/css", ["example-com-style.css"], "example-com-style.1.css"),
        # Complex URL path
        ("https://example.com/assets/v1/icons/logo.svg", "image/svg+xml", [], "example-com-assets-v1-icons-logo.svg"),
        # Query string should be stripped, and matching extension is not duplicated
        ("https://example.com/image.png?v=123", "image/png", [], "example-com-image.png"),
    ),
)
def test_filename_for_har_entry(url, content_type, existing_files, expected):
    assert filename_for_har_entry(url, content_type, file_exists=lambda s: s in existing_files) == expected
