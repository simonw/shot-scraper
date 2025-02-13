import pytest
import subprocess
import tempfile
import time
import socket
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from contextlib import closing


@dataclass
class HTTPServer:
    """Container for HTTP server information."""

    base_url: str
    base_dir: Path


def find_free_port():
    """Find an available port by creating a temporary socket."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        return port


@pytest.fixture
def http_server():
    """
    Pytest fixture that starts a Python HTTP server in a subprocess.
    Creates a temporary directory with an index.html file, starts the server
    on an available port, and cleans up afterwards.

    Yields:
        HTTPServer: Object containing server information:
            - base_url: The base URL of the running server
            - base_dir: Path to the temporary directory serving files
    """
    # Find an available port
    port = find_free_port()

    # Create temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)

        # Create index.html
        index_path = base_dir / "index.html"
        index_path.write_text("<html><body>Hello World</body></html>")

        # Start server process in temp directory
        process = subprocess.Popen(
            ["python", "-m", "http.server", str(port)],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to start
        base_url = f"http://localhost:{port}"
        max_retries = 5
        retry_delay = 0.5

        for _ in range(max_retries):
            try:
                with urllib.request.urlopen(base_url) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, ConnectionRefusedError):
                time.sleep(retry_delay)
        else:
            process.terminate()
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"Failed to start HTTP server on port {port}.\n"
                f"stdout: {stdout.decode()}\n"
                f"stderr: {stderr.decode()}"
            )

        try:
            yield HTTPServer(base_url=base_url, base_dir=base_dir)
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=5)  # Wait up to 5 seconds for process to terminate

            # Force kill if still running
            if process.poll() is None:
                process.kill()
                process.wait()
