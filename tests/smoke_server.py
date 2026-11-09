"""Explicit integration check: start, health-check, stop, then repeat."""
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = ROOT / "docs" / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    with (evidence / "local-server-smoke.log").open("w") as log:
        for attempt in range(2):
            process = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
                 "--server.headless=true", "--server.address=127.0.0.1",
                 "--server.port=18522", "--browser.gatherUsageStats=false"],
                cwd=ROOT, stdout=log, stderr=log,
            )
            try:
                for _ in range(60):
                    if process.poll() is not None:
                        raise RuntimeError("Server exited; see docs/evidence/local-server-smoke.log")
                    try:
                        with urllib.request.urlopen(
                            "http://127.0.0.1:18522/_stcore/health", timeout=1
                        ) as response:
                            assert response.status == 200
                            assert response.read() == b"ok"
                        break
                    except OSError:
                        time.sleep(0.2)
                else:
                    raise RuntimeError("Server health timed out")
                print(f"Launch {attempt + 1}: HTTP 200, health ok")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise
                print(f"Stopped process; exit {process.returncode}")
            assert process.returncode == 0


if __name__ == "__main__":
    main()
