"""Spoken narration for ``shot-scraper video`` storyboards.

A storyboard scene may carry a ``say:`` line. When any scene does,
``shot-scraper video ... --mp4`` produces a *narrated* MP4:

1.  Each ``say:`` line is synthesized to speech offline with Kokoro (via the
    ``kokoro-onnx`` package, CPU-only), and its real duration is measured with
    ``ffprobe``.
2.  A trailing ``pause`` is appended to that scene, long enough to hold the
    frame for the whole spoken line, so narration is never clipped by the next
    scene. This is *audio-led*: the video timing is derived from the measured
    speech, so the two cannot drift apart.
3.  After the silent video is recorded, each clip is laid onto a full-length
    silent bed at its computed start offset (ffmpeg ``adelay``/``amix``) and
    muxed into the MP4.

``kokoro-onnx`` and ``soundfile`` are optional; install them with
``pip install shot-scraper[narrate]``. ``ffmpeg``/``ffprobe`` must be on PATH
(the same requirement as ``--mp4``). Nothing here touches a GPU.
"""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# Kokoro's native output sample rate.
KOKORO_SAMPLE_RATE = 24000

# Where model files are cached / downloaded to when not supplied explicitly.
KOKORO_MODEL_BASE = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
)
KOKORO_MODEL_NAME = "kokoro-v1.0.onnx"
KOKORO_VOICES_NAME = "voices-v1.0.bin"

# Common locations for a *system* espeak-ng library + its data. kokoro-onnx
# bundles espeakng-loader, but that prebuilt dylib has a data path baked in at
# build time that often does not exist locally ("phontab: No such file or
# directory"). A system espeak-ng (brew on macOS, apt on Linux) has a correct,
# self-consistent data path, so we prefer it when present.
_ESPEAK_LIB_CANDIDATES = [
    "/opt/homebrew/lib/libespeak-ng.dylib",  # macOS arm64 (brew)
    "/usr/local/lib/libespeak-ng.dylib",  # macOS x86_64 (brew)
    "/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1",  # Debian/Ubuntu
    "/usr/lib/libespeak-ng.so.1",  # other Linux
    "/usr/lib/aarch64-linux-gnu/libespeak-ng.so.1",  # arm64 Linux
]
_ESPEAK_DATA_CANDIDATES = [
    "/opt/homebrew/share/espeak-ng-data",
    "/usr/local/share/espeak-ng-data",
    "/usr/share/espeak-ng-data",
    "/usr/lib/x86_64-linux-gnu/espeak-ng-data",
    "/usr/lib/aarch64-linux-gnu/espeak-ng-data",
]


class NarrationError(Exception):
    """Raised for any narration setup or synthesis failure."""


@dataclass
class NarrationLine:
    """One synthesized ``say:`` line, placed on the final video timeline."""

    name: str
    wav: Path
    duration: float  # measured length of the spoken audio, seconds
    start: float  # offset into the final video where the line begins speaking
    mid: float  # midpoint of the line (handy for a verification still)


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, text=True, capture_output=True)


def probe_duration(path: Path) -> float:
    """Return the duration of an audio/video file in seconds via ffprobe."""
    try:
        result = _run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ]
        )
    except FileNotFoundError:
        raise NarrationError(
            "ffprobe is not installed or not on PATH (needed for narration)."
        )
    except subprocess.CalledProcessError as ex:
        raise NarrationError(f"ffprobe failed for {path}: {ex.stderr or ex.stdout}")
    return float(result.stdout.strip())


def default_model_dir() -> Path:
    root = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(root) / "shot-scraper" / "kokoro"


def _ensure_model_files(model: Path, voices: Path) -> None:
    """Download the Kokoro model/voices if absent (idempotent, best-effort)."""
    for path, name in ((model, KOKORO_MODEL_NAME), (voices, KOKORO_VOICES_NAME)):
        if path.exists() and path.stat().st_size > 0:
            continue
        url = f"{KOKORO_MODEL_BASE}/{name}"
        path.parent.mkdir(parents=True, exist_ok=True)
        sys.stderr.write(f"Downloading Kokoro model {name} -> {path} ...\n")
        try:
            urllib.request.urlretrieve(url, path)
        except Exception as exc:
            raise NarrationError(
                f"Failed to download {name} from {url}: {exc}\n"
                "Download it manually and pass narration model:/voices: paths."
            ) from exc


def _find_system_espeak():
    """Return (lib_path, data_path) for a usable system espeak-ng, or None."""
    lib = next((p for p in _ESPEAK_LIB_CANDIDATES if Path(p).exists()), None)
    data = next(
        (p for p in _ESPEAK_DATA_CANDIDATES if Path(p, "phontab").exists()), None
    )
    if lib and data:
        return lib, data
    return None


def load_kokoro(model: Path | None = None, voices: Path | None = None):
    """Load a Kokoro synthesizer, downloading the model files if needed."""
    try:
        from kokoro_onnx import Kokoro
    except ImportError as exc:
        raise NarrationError(
            "Narration needs the 'kokoro-onnx' package. Install the extra with:\n"
            "  pip install shot-scraper[narrate]\n"
            "(also requires espeak-ng: 'brew install espeak-ng' on macOS, "
            "'sudo apt-get install espeak-ng' on Debian/Ubuntu)."
        ) from exc

    model = Path(model) if model else default_model_dir() / KOKORO_MODEL_NAME
    voices = Path(voices) if voices else default_model_dir() / KOKORO_VOICES_NAME
    _ensure_model_files(model, voices)

    # Force CPU: never contend with a GPU that may be busy.
    os.environ.setdefault("ONNX_PROVIDER", "CPUExecutionProvider")

    espeak = _find_system_espeak()
    if espeak:
        from kokoro_onnx import EspeakConfig

        lib, data = espeak
        return Kokoro(
            str(model),
            str(voices),
            espeak_config=EspeakConfig(lib_path=lib, data_path=data),
        )

    sys.stderr.write(
        "WARNING: no system espeak-ng found; relying on the bundled loader, "
        "which may fail. Install espeak-ng if synthesis errors.\n"
    )
    return Kokoro(str(model), str(voices))


def synth_line(kokoro, text: str, voice: str, speed: float, out_path: Path) -> None:
    try:
        import soundfile as sf
    except ImportError as exc:
        raise NarrationError(
            "Narration needs 'soundfile'. Install with: pip install shot-scraper[narrate]"
        ) from exc

    samples, sample_rate = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
    sf.write(str(out_path), samples, sample_rate)


def plan_narration(storyboard, audio_dir: Path, narrator=None) -> list[NarrationLine]:
    """Synthesize every scene ``say:`` line and append frame-holding pauses.

    Mutates each narrated scene's ``do`` list in place (appending a ``pause``
    action sized to hold the frame for the whole spoken line) and returns the
    timeline placement of each line. ``storyboard.scenes`` must already be the
    validated pydantic model. Pass ``narrator`` to reuse a loaded Kokoro (tests
    inject a fake); otherwise one is loaded from the storyboard's narration
    options.
    """
    from .video import PauseAction  # local import to avoid a cycle

    opts = storyboard.narration
    audio_dir.mkdir(parents=True, exist_ok=True)
    if narrator is None:
        narrator = load_kokoro(opts.model, opts.voices)

    lines: list[NarrationLine] = []
    cursor = 0.0  # running position in the final video, seconds
    for index, scene in enumerate(storyboard.scenes):
        allowance = (
            scene.action_allowance
            if scene.action_allowance is not None
            else opts.action_allowance
        )
        if scene.say:
            wav = audio_dir / f"{index:02d}.wav"
            synth_line(narrator, scene.say, opts.voice, opts.speed, wav)
            duration = probe_duration(wav)
            # Timeline within the scene:
            #   [actions ~allowance] [lead settle] [speak duration] [buffer]
            start = cursor + allowance + opts.lead
            hold = opts.lead + duration + opts.buffer
            lines.append(
                NarrationLine(
                    name=scene.name or f"Scene {index + 1}",
                    wav=wav,
                    duration=round(duration, 3),
                    start=round(start, 3),
                    mid=round(start + duration / 2, 3),
                )
            )
            scene.do.append(PauseAction(action="pause", seconds=round(hold, 3)))
            cursor += allowance + hold
        else:
            explicit_pause = sum(
                action.seconds
                for action in scene.do
                if isinstance(action, PauseAction)
            )
            cursor += allowance + explicit_pause
    return lines


def mux_narration(video: Path, output: Path, lines: list[NarrationLine]) -> None:
    """Mix each narration clip onto the recorded video at its start offset."""
    if not lines:
        raise NarrationError("mux_narration called with no narration lines")
    video_dur = probe_duration(video)

    inputs: list[str] = ["-i", str(video)]
    filters: list[str] = []
    labels: list[str] = []
    for i, line in enumerate(lines):
        inputs += ["-i", str(line.wav)]
        delay_ms = int(round(line.start * 1000))
        end = line.start + line.duration
        if end > video_dur + 0.05:
            sys.stderr.write(
                f"WARNING: narration line {i} ('{line.name}') ends at {end:.1f}s "
                f"but the video is only {video_dur:.1f}s — it will be cut off. "
                "Increase that scene's action_allowance or shorten the line.\n"
            )
        # Audio stream index is i + 1 (0 is the video).
        filters.append(f"[{i + 1}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
        labels.append(f"[a{i}]")

    mix = "".join(labels) + f"amix=inputs={len(labels)}:normalize=0[aout]"
    filter_complex = ";".join(filters + [mix])
    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            str(output),
        ]
    )
    try:
        _run(cmd)
    except FileNotFoundError:
        raise NarrationError("ffmpeg is not installed or not on PATH.")
    except subprocess.CalledProcessError as ex:
        raise NarrationError(f"ffmpeg mux failed: {ex.stderr or ex.stdout}")
