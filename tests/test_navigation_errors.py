from pathlib import Path
from unittest.mock import MagicMock

import pytest
import click
from click.testing import CliRunner
from playwright.sync_api import Error, TimeoutError

import shot_scraper.cli as cli_module
from shot_scraper.cli import cli, take_shot


@pytest.mark.parametrize(
    "error",
    [
        Error("net::ERR_NAME_NOT_RESOLVED"),
        Error("net::ERR_CERT_AUTHORITY_INVALID"),
        Error("net::ERR_CONNECTION_REFUSED"),
        TimeoutError("Navigation timed out"),
    ],
)
@pytest.mark.parametrize("skip", [False, True])
def test_navigation_error_skip(error, skip, capsys):
    context = MagicMock()
    page = context.new_page.return_value
    page.goto.side_effect = error
    shot = {"url": "https://example.test/", "output": "unused.png"}
    if skip:
        assert take_shot(context, shot, skip=True) is None
        assert "skipping" in capsys.readouterr().err
        page.close.assert_called_once()
    else:
        with pytest.raises(type(error)) as exc:
            take_shot(context, shot)
        assert exc.value is error
    page.screenshot.assert_not_called()


@pytest.mark.parametrize("operation", ["goto", "evaluate", "screenshot"])
def test_skip_does_not_hide_other_errors(operation):
    context = MagicMock()
    page = context.new_page.return_value
    page.goto.return_value.status = 200
    error = (
        ValueError("invalid navigation argument")
        if operation == "goto"
        else Error("failed")
    )
    getattr(page, operation).side_effect = error
    shot = {"url": "https://example.test/", "output": "unused.png"}
    if operation == "evaluate":
        shot["javascript"] = "1 + 1"
    with pytest.raises(
        click.ClickException if operation == "evaluate" else type(error)
    ):
        take_shot(context, shot, skip=True)


@pytest.mark.parametrize("command", ["shot", "multi"])
@pytest.mark.parametrize("skip", [False, True])
def test_cli_navigation_error(command, skip, monkeypatch):
    original = cli_module._browser_context

    def routed_context(*args, **kwargs):
        context, browser = original(*args, **kwargs)

        def route_request(route):
            if route.request.url.endswith("/bad"):
                route.abort("namenotresolved")
            else:
                route.fulfill(
                    body="<html><body>Offline test</body></html>",
                    content_type="text/html",
                )

        context.route("**/*", route_request)
        return context, browser

    monkeypatch.setattr(cli_module, "_browser_context", routed_context)
    runner = CliRunner()
    with runner.isolated_filesystem():
        if command == "multi":
            Path("shots.yml").write_text(
                "- url: https://example.test/bad\n  output: bad.png\n"
                "- url: https://example.test/good\n  output: good.png\n"
            )
            args = ["multi", "shots.yml"]
        else:
            args = ["https://example.test/bad", "-o", "bad.png"]
        result = runner.invoke(cli, args + (["--skip"] if skip else []))
        assert result.exit_code == (0 if skip else 1), result.output
        assert not Path("bad.png").exists()
        if command == "multi":
            assert Path("good.png").exists() is skip
        if skip:
            assert "skipping" in result.output
        else:
            assert isinstance(result.exception, Error)
            assert "ERR_NAME_NOT_RESOLVED" in str(result.exception)
