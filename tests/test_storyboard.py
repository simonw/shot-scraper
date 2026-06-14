from io import StringIO

import pytest

from shot_scraper.storyboard import (
    ClickAction,
    FillAction,
    OpenAction,
    PressAction,
    ScrollAction,
    StoryboardError,
    TypeAction,
    WaitForAction,
    load_storyboard,
)


def parse_storyboard(yaml):
    return load_storyboard(StringIO(yaml))


def test_load_storyboard_normalizes_actions():
    storyboard = parse_storyboard(
        """
output: demo.webm
url: https://example.com/
viewport:
  width: 640
  height: 360
wait: 0.25
scenes:
- name: Search
  do:
  - click: "#search"
  - fill:
      into: "#search"
      text: "shot-scraper"
  - press: Enter
  - type:
      selector: "#search"
      text: " demos"
      delay: 10
  - scroll:
      y: 200
      duration: 0.1
  - wait_for: ".results"
  - open: /results
"""
    )

    assert storyboard.output == "demo.webm"
    assert storyboard.url == "https://example.com/"
    assert storyboard.viewport_size() == {"width": 640, "height": 360}
    assert storyboard.wait == 0.25
    actions = storyboard.scenes[0].do
    assert isinstance(actions[0], ClickAction)
    assert actions[0].selector == "#search"
    assert isinstance(actions[1], FillAction)
    assert actions[1].target_selector == "#search"
    assert isinstance(actions[2], PressAction)
    assert actions[2].key == "Enter"
    assert isinstance(actions[3], TypeAction)
    assert actions[3].target_selector == "#search"
    assert actions[3].delay == 10
    assert isinstance(actions[4], ScrollAction)
    assert actions[4].y == 200
    assert actions[4].duration == 0.1
    assert isinstance(actions[5], WaitForAction)
    assert actions[5].selector == ".results"
    assert isinstance(actions[6], OpenAction)
    assert actions[6].url == "/results"


def test_load_storyboard_defaults_viewport():
    storyboard = parse_storyboard(
        """
output: demo.webm
url: https://example.com/
scenes:
- name: Home
"""
    )

    assert storyboard.viewport_size() == {"width": 1280, "height": 720}


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
    ),
)
def test_load_storyboard_validation_errors(yaml, expected):
    with pytest.raises(StoryboardError) as ex:
        parse_storyboard(yaml)

    assert str(ex.value) == expected
