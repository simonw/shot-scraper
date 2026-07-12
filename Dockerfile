# Run shot-scraper with only Docker installed on the host: chromium, its system
# libraries, ffmpeg, espeak-ng, the Kokoro narration model and shot-scraper all
# live in the image.
#
#   docker build -t shot-scraper .
#
#   # Screenshot (mount the current directory as /work for inputs/outputs):
#   docker run --rm -v "$PWD:/work" shot-scraper \
#     shot https://example.com/ -o /work/example.png \
#     --browser-arg --no-sandbox --browser-arg --disable-dev-shm-usage
#
#   # Narrated video:
#   docker run --rm -v "$PWD:/work" shot-scraper \
#     video /work/storyboard.yml -o /work/demo.webm --mp4 \
#     --browser-arg --no-sandbox --browser-arg --disable-dev-shm-usage
#
# chromium cannot use its sandbox as root inside a container, and the default
# 64MB /dev/shm is too small, so pass --browser-arg --no-sandbox and
# --browser-arg --disable-dev-shm-usage (shown above). On Linux add
# `--network host` to reach a server on the host's own localhost.
FROM python:3.12-slim

# ffmpeg/ffprobe (--mp4 and narration muxing) and espeak-ng (Kokoro phonemizer).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Install shot-scraper with the narration extra from the build context, then the
# matching Playwright chromium + its system libraries (pinned by shot-scraper's
# own Playwright dependency, so the browser never drifts from the library).
COPY . /src
RUN pip install --no-cache-dir "/src[narrate]"
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install --with-deps chromium \
    && chmod -R a+rx /ms-playwright

# Bake the Kokoro model + voices so narration works fully offline. This matches
# narration.py's default cache location ($XDG_CACHE_HOME/shot-scraper/kokoro).
ENV XDG_CACHE_HOME=/cache
RUN mkdir -p /cache/shot-scraper/kokoro && python - <<'PY'
import pathlib
import urllib.request

base = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
dest = pathlib.Path("/cache/shot-scraper/kokoro")
for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
    urllib.request.urlretrieve(f"{base}/{name}", dest / name)
PY
RUN chmod -R a+rX /cache

WORKDIR /work
ENTRYPOINT ["shot-scraper"]
