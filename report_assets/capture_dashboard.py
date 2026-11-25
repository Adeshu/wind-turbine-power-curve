import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(r"C:\Users\Ashish\Desktop\SML")
OUT = ROOT / "report_assets" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
PY = ROOT / ".venv" / "Scripts" / "python.exe"
PORT = 8503
URL = f"http://localhost:{PORT}"
LOG = ROOT / "report_assets" / "streamlit_capture.log"

TABS = [
    ("dash_01_overview.png", "Overview"),
    ("dash_02_cleaning.png", "Cleaning & outliers"),
    ("dash_03_power_curve.png", "Power curve"),
    ("dash_04_model_comparison.png", "Model comparison"),
    ("dash_05_diagnostics.png", "Diagnostics"),
    ("dash_06_methodology.png", "Methodology"),
]


def wait_health(timeout=180):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{URL}/_stcore/health", timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("Streamlit server did not become ready")


def stop(proc):
    if proc.poll() is not None:
        return
    subprocess.run(
        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main():
    log_handle = open(LOG, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            str(PY),
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.headless",
            "true",
            "--server.port",
            str(PORT),
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_health()
        print("server ready", flush=True)
        chrome_candidates = sorted(
            (Path(os.environ["LOCALAPPDATA"]) / "ms-playwright").glob(
                "chromium-*/chrome-win64/chrome.exe"
            )
        )
        launch_kwargs = {"headless": True}
        if chrome_candidates:
            launch_kwargs["executable_path"] = str(chrome_candidates[-1])
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(
                viewport={"width": 1600, "height": 1150},
                device_scale_factor=2,
            )
            page = context.new_page()
            page.goto(URL, wait_until="networkidle", timeout=180000)
            page.get_by_text("Wind Turbine Power Curve Modelling").first.wait_for(
                timeout=120000
            )
            page.wait_for_timeout(4000)

            def snap(name):
                page.mouse.move(1400, 1450)
                page.keyboard.press("Escape")
                page.evaluate("document.activeElement && document.activeElement.blur()")
                page.wait_for_timeout(1500)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(800)
                page.screenshot(path=str(OUT / name), full_page=False)
                print("saved", name, flush=True)

            for idx, (filename, label) in enumerate(TABS):
                print("opening tab", label, flush=True)
                page.get_by_role("tab", name=label, exact=False).click()
                page.wait_for_timeout(2500)

                if filename.startswith("dash_04"):
                    button = page.get_by_role(
                        "button", name="Run cross-validation", exact=False
                    )
                    button.click()
                    page.mouse.move(1400, 1450)
                    print("cross-validation started", flush=True)
                    page.get_by_text("Best model", exact=False).first.wait_for(
                        timeout=600000
                    )
                    page.wait_for_timeout(4000)
                    print("cross-validation finished", flush=True)

                if filename.startswith("dash_05"):
                    page.get_by_text("Diagnostic plots", exact=False).first.wait_for(
                        timeout=180000
                    )
                    page.wait_for_timeout(3000)

                snap(filename)

            context.close()
            browser.close()
    finally:
        stop(proc)
        log_handle.close()


if __name__ == "__main__":
    main()
