from io import StringIO

import pytest
from click.testing import CliRunner

from shot_scraper.cli import cli
from shot_scraper.video import (
    ClickAction,
    ExpectAction,
    ExpectGoneAction,
    FillAction,
    OpenAction,
    PressAction,
    ScreenshotAction,
    ShAction,
    ScrollAction,
    StoryboardError,
    TypeAction,
    WaitForAction,
    PythonAction,
    load_storyboard,
)


def parse_storyboard(yaml):
    return load_storyboard(StringIO(yaml))


def test_load_storyboard_normalizes_actions():
    storyboard = parse_storyboard("""
output: demo.webm
sh: echo "top level" > top-level.txt
python: |
  open("top-level-python.txt", "w").write("ok")
server:
- python
- -m
- http.server
- 8000
url: https://example.com/
viewport:
  width: 640
  height: 360
wait: 0.25
scenes:
- name: Search
  sh: echo "scene" > scene.txt
  python: |
    open("scene-python.txt", "w").write("ok")
  do:
  - click: "#search"
  - fill:
      into: "#search"
      text: "shot-scraper"
  - press: Enter
  - type:
      selector: "#search"
      text: " demos"
      delay_ms: 10
  - scroll:
      y: 200
      duration: 0.1
  - wait_for: ".results"
  - open: /results
  - screenshot: results.png
  - screenshot:
      output: result-heading.png
      selector: h1
  - sh: echo "action" > action.txt
  - python: |
      open("action-python.txt", "w").write("ok")
""")

    assert storyboard.output == "demo.webm"
    assert storyboard.sh == 'echo "top level" > top-level.txt'
    assert storyboard.python == 'open("top-level-python.txt", "w").write("ok")\n'
    assert storyboard.server == ["python", "-m", "http.server", 8000]
    assert storyboard.url == "https://example.com/"
    assert storyboard.viewport_size() == {"width": 640, "height": 360}
    assert storyboard.wait == 0.25
    actions = storyboard.scenes[0].do
    assert storyboard.scenes[0].sh == 'echo "scene" > scene.txt'
    assert storyboard.scenes[0].python == 'open("scene-python.txt", "w").write("ok")\n'
    assert isinstance(actions[0], ClickAction)
    assert actions[0].selector == "#search"
    assert isinstance(actions[1], FillAction)
    assert actions[1].target_selector == "#search"
    assert isinstance(actions[2], PressAction)
    assert actions[2].key == "Enter"
    assert isinstance(actions[3], TypeAction)
    assert actions[3].target_selector == "#search"
    assert actions[3].delay_ms == 10
    assert isinstance(actions[4], ScrollAction)
    assert actions[4].y == 200
    assert actions[4].duration == 0.1
    assert isinstance(actions[5], WaitForAction)
    assert actions[5].selector == ".results"
    assert isinstance(actions[6], OpenAction)
    assert actions[6].url == "/results"
    assert isinstance(actions[7], ScreenshotAction)
    assert actions[7].output == "results.png"
    assert actions[7].selector is None
    assert isinstance(actions[8], ScreenshotAction)
    assert actions[8].output == "result-heading.png"
    assert actions[8].selector == "h1"
    assert isinstance(actions[9], ShAction)
    assert actions[9].command == 'echo "action" > action.txt'
    assert isinstance(actions[10], PythonAction)
    assert actions[10].code == 'open("action-python.txt", "w").write("ok")\n'


def test_load_storyboard_defaults_viewport():
    storyboard = parse_storyboard("""
output: demo.webm
url: https://example.com/
scenes:
- name: Home
""")

    assert storyboard.viewport_size() == {"width": 1280, "height": 720}


def test_load_storyboard_cursor_true_uses_defaults():
    storyboard = parse_storyboard("""
output: demo.webm
url: https://example.com/
cursor: true
scenes:
- name: Home
""")

    assert storyboard.cursor.visible is True
    assert storyboard.cursor.clicks is True
    assert storyboard.cursor.color == "#ff4f00"
    assert storyboard.cursor.size == 18
    assert storyboard.cursor.click_size == 44


def test_load_storyboard_cursor_options():
    storyboard = parse_storyboard("""
output: demo.webm
url: https://example.com/
cursor:
  visible: false
  clicks: true
  color: "#3366ff"
  size: 24
  click_size: 60
scenes:
- name: Home
""")

    assert storyboard.cursor.visible is False
    assert storyboard.cursor.clicks is True
    assert storyboard.cursor.color == "#3366ff"
    assert storyboard.cursor.size == 24
    assert storyboard.cursor.click_size == 60


@pytest.mark.parametrize(
    "yaml,expected",
    (
        ("", "Storyboard YAML file cannot be empty"),
        ("- output: demo.webm", "Storyboard YAML file must contain a mapping"),
        (
            """
output: demo.webm
url: https://example.com/
""",
            "Storyboard must define a non-empty scenes: list",
        ),
        (
            """
output: demo.webm
scenes:
- name: Home
""",
            "Storyboard must define url: or open: in the first scene",
        ),
        (
            """
output: demo.webm
url: https://example.com/
scenes:
- do:
  - fill:
      into: "#search"
""",
            "scenes.0.do.0.fill.text: Field required",
        ),
        (
            """
output: demo.webm
url: https://example.com/
scenes:
- do:
  - magic: "#search"
""",
            "scenes.0.do: Unknown storyboard action: magic",
        ),
        (
            """
output: demo.webm
url: https://example.com/
scenes:
- name: Home
  banana: true
""",
            "scenes.0.banana: Extra inputs are not permitted",
        ),
        (
            """
output: demo.webm
url: https://example.com/
scenes:
- do:
  - expect: {}
""",
            "scenes.0.do.0.expect: expect: needs a selector: and/or text:",
        ),
    ),
)
def test_load_storyboard_validation_errors(yaml, expected):
    with pytest.raises(StoryboardError) as ex:
        parse_storyboard(yaml)

    assert str(ex.value) == expected


def test_load_storyboard_normalizes_expect_actions():
    storyboard = parse_storyboard(
        """
output: demo.webm
url: https://example.com/
scenes:
- do:
  - expect: "#done"
  - expect: { text: "Saved", timeout: 500 }
  - expect_gone: { contains: "Loading" }
"""
    )
    actions = storyboard.scenes[0].do
    assert isinstance(actions[0], ExpectAction)
    assert actions[0].selector == "#done" and actions[0].text is None
    assert isinstance(actions[1], ExpectAction)
    assert actions[1].text == "Saved" and actions[1].timeout == 500
    # `contains:` is an alias for `text:`
    assert isinstance(actions[2], ExpectGoneAction)
    assert actions[2].text == "Loading"


EXPECT_HTML = "<!DOCTYPE html><html><head><title>t</title></head><body><h1 id='h'>Present text</h1></body></html>"


def _record(runner, storyboard):
    open("index.html", "w").write(EXPECT_HTML)
    open("sb.yml", "w").write(storyboard)
    return runner.invoke(cli, ["video", "sb.yml", "--browser-arg", "--no-sandbox"])


def test_expect_passes_when_condition_holds():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = _record(
            runner,
            """
output: demo.webm
url: index.html
scenes:
- do:
  - expect: "#h"
  - expect: { text: "Present text" }
  - expect_gone: { text: "never here" }
  - pause: 0.2
""",
        )
        assert result.exit_code == 0, result.output


def test_expect_fails_recording_when_condition_never_holds():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = _record(
            runner,
            """
output: demo.webm
url: index.html
scenes:
- do:
  - expect: { text: "this is absent", timeout: 800 }
""",
        )
        assert result.exit_code != 0
        assert "expect assertion failed" in result.output


def test_expect_gone_fails_when_target_stays_present():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = _record(
            runner,
            """
output: demo.webm
url: index.html
scenes:
- do:
  - expect_gone: { selector: "#h", timeout: 800 }
""",
        )
        assert result.exit_code != 0
        assert "expect_gone assertion failed" in result.output
