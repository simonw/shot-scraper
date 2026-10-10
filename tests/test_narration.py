from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from shot_scraper import narration
from shot_scraper.cli import cli
from shot_scraper.video import PauseAction, Storyboard, StoryboardError, load_storyboard


def _story(scenes, **narration_opts):
    data = {"url": "https://example.com/", "scenes": scenes}
    if narration_opts:
        data["narration"] = narration_opts
    return Storyboard.model_validate(data)


# --- storyboard model ----------------------------------------------------- #


def test_say_field_parses():
    story = _story([{"say": "hello world", "do": []}])
    assert story.has_narration()
    assert story.scenes[0].say == "hello world"


def test_storyboard_without_say_has_no_narration():
    story = _story([{"do": [{"pause": 1}]}])
    assert not story.has_narration()


def test_narration_options_parse():
    story = _story([{"say": "hi", "do": []}], voice="am_adam", speed=1.2, lead=0.2)
    assert story.narration.voice == "am_adam"
    assert story.narration.speed == 1.2
    assert story.narration.lead == 0.2
    # Untouched options keep their defaults
    assert story.narration.buffer == 0.6


def test_unknown_scene_key_still_forbidden():
    import io

    bad = "url: https://example.com/\nscenes:\n- say: hi\n  bogus: 1\n  do: []\n"
    with pytest.raises(StoryboardError):
        load_storyboard(io.StringIO(bad))


# --- planning (synthesis + pause injection + timeline) -------------------- #


def test_plan_narration_injects_pause_and_computes_offsets(mocker, tmp_path):
    mocker.patch("shot_scraper.narration.synth_line")
    mocker.patch("shot_scraper.narration.probe_duration", return_value=2.0)
    story = _story(
        [
            {"name": "one", "say": "first line", "do": [{"click": "#a"}]},
            {"name": "two", "say": "second line", "do": []},
        ]
    )
    lines = narration.plan_narration(story, tmp_path / "audio", narrator=MagicMock())

    assert [line.name for line in lines] == ["one", "two"]
    # hold = lead + duration + buffer = 0.4 + 2.0 + 0.6 = 3.0, appended to each scene
    assert isinstance(story.scenes[0].do[-1], PauseAction)
    assert story.scenes[0].do[-1].seconds == 3.0
    assert isinstance(story.scenes[1].do[-1], PauseAction)
    # scene 0 line starts at allowance + lead = 1.0 + 0.4
    assert lines[0].start == 1.4
    # cursor after scene 0 = allowance + hold = 1.0 + 3.0 = 4.0; scene 1 at +1.4
    assert lines[1].start == 5.4
    assert lines[0].mid == round(1.4 + 2.0 / 2, 3)


def test_plan_narration_per_scene_action_allowance(mocker, tmp_path):
    mocker.patch("shot_scraper.narration.synth_line")
    mocker.patch("shot_scraper.narration.probe_duration", return_value=1.0)
    story = _story([{"say": "x", "action_allowance": 3, "do": []}])
    lines = narration.plan_narration(story, tmp_path / "audio", narrator=MagicMock())
    # start = action_allowance (3) + lead (0.4)
    assert lines[0].start == 3.4


def test_plan_narration_silent_scene_advances_by_pauses(mocker, tmp_path):
    mocker.patch("shot_scraper.narration.synth_line")
    mocker.patch("shot_scraper.narration.probe_duration", return_value=1.0)
    story = _story(
        [
            {"do": [{"pause": 2}]},  # silent: allowance(1) + pause(2) = 3
            {"say": "after", "do": []},
        ]
    )
    lines = narration.plan_narration(story, tmp_path / "audio", narrator=MagicMock())
    # cursor after silent scene = 3.0; line starts at 3.0 + allowance(1) + lead(0.4)
    assert lines[0].start == 4.4


# --- muxing --------------------------------------------------------------- #


def test_mux_narration_builds_ffmpeg_command(mocker, tmp_path):
    run = mocker.patch("shot_scraper.narration._run")
    mocker.patch("shot_scraper.narration.probe_duration", return_value=10.0)
    lines = [
        narration.NarrationLine(
            name="a", wav=tmp_path / "0.wav", duration=2.0, start=1.4, mid=2.4
        )
    ]
    narration.mux_narration(tmp_path / "in.webm", tmp_path / "out.mp4", lines)
    args = run.call_args.args[0]
    assert args[0] == "ffmpeg"
    filter_complex = args[args.index("-filter_complex") + 1]
    assert "adelay=1400|1400" in filter_complex
    assert "amix=inputs=1:normalize=0" in filter_complex
    assert args[-1] == str(tmp_path / "out.mp4")


def test_mux_narration_warns_when_line_overruns_video(mocker, tmp_path, capsys):
    mocker.patch("shot_scraper.narration._run")
    mocker.patch("shot_scraper.narration.probe_duration", return_value=10.0)
    lines = [
        narration.NarrationLine(
            name="tail", wav=tmp_path / "0.wav", duration=5.0, start=8.0, mid=10.5
        )
    ]
    narration.mux_narration(tmp_path / "in.webm", tmp_path / "out.mp4", lines)
    assert "will be cut off" in capsys.readouterr().err


# --- CLI wiring ----------------------------------------------------------- #

STORYBOARD_YAML = "url: https://example.com/\nscenes:\n- say: hello\n  do: []\n"


def test_video_narration_requires_mp4():
    runner = CliRunner()
    with runner.isolated_filesystem():
        open("sb.yml", "w").write(STORYBOARD_YAML)
        result = runner.invoke(cli, ["video", "sb.yml"])
    assert result.exit_code != 0
    assert "--mp4" in result.output


def test_video_narration_error_becomes_clickexception(mocker):
    mocker.patch(
        "shot_scraper.cli.plan_narration",
        side_effect=narration.NarrationError("kokoro-onnx is not installed"),
    )
    runner = CliRunner()
    with runner.isolated_filesystem():
        open("sb.yml", "w").write(STORYBOARD_YAML)
        result = runner.invoke(cli, ["video", "sb.yml", "--mp4"])
    assert result.exit_code != 0
    assert "kokoro-onnx is not installed" in result.output
