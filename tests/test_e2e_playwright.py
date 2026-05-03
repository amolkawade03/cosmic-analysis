import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_port(port: int, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.25)
    raise TimeoutError(f"Streamlit did not start on port {port}")


@pytest.mark.e2e
def test_streamlit_dashboard_renders_core_sections():
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ROOT / "app.py"),
            "--server.headless=true",
            "--server.address=127.0.0.1",
            f"--server.port={port}",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_port(port)
        with sync_playwright() as p:
            launch_kwargs = {"headless": True}
            if Path("/usr/bin/chromium").exists():
                launch_kwargs["executable_path"] = "/usr/bin/chromium"
            browser = p.chromium.launch(**launch_kwargs)
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded")
            page.get_by_text("Cosmic Analysis").first.wait_for(timeout=30000)
            page.get_by_text("Panchangam + Muhurta + Birth-Chart alignment dashboard").first.wait_for(timeout=30000)
            page.get_by_text("Daily alignment").first.wait_for(timeout=30000)
            page.get_by_text("Best Muhurta Windows").first.wait_for(timeout=30000)
            page.get_by_text("Tithi").first.wait_for(timeout=30000)
            browser.close()
    except PlaywrightTimeoutError as exc:
        stdout = process.stdout.read() if process.stdout else ""
        pytest.fail(f"Dashboard did not render expected content: {exc}\n{stdout[-3000:]}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
