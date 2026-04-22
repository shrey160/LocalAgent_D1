"""Dharampal CLI: `dharampal start` / `dharampal stop`.

`start` boots LM Studio, loads the model, launches the chat UI as a
detached process, and records the UI PID + model identifier in a state
file so `stop` (from any terminal, even a fresh one) can tear everything
down cleanly.
"""

import os
import sys
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

# --- configuration --------------------------------------------------------

MODEL_ID = "google/gemma-4-e4b"
IDENTIFIER = "friday-main"
CONTEXT_LENGTH = "90000"
GPU_MODE = "off"

STATE_FILE = Path(tempfile.gettempdir()) / "dharampal.state"
UI_LOG_FILE = Path(tempfile.gettempdir()) / "dharampal_ui.log"
WIDGET_LOG_FILE = Path(tempfile.gettempdir()) / "dharampal_widget.log"

# --- state file helpers ---------------------------------------------------


def _save_state(**kwargs):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        for k, v in kwargs.items():
            f.write(f"{k}={v}\n")


def _load_state():
    state = {}
    if STATE_FILE.exists():
        for line in STATE_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                state[k.strip()] = v.strip()
    return state


def _clear_state():
    try:
        STATE_FILE.unlink()
    except FileNotFoundError:
        pass


# --- LM Studio helpers ----------------------------------------------------


def _find_lms():
    """Locate the `lms` CLI. Returns the resolved path or just 'lms' as a fallback."""
    lms = shutil.which("lms")
    if not lms:
        print("WARNING: 'lms' (LM Studio CLI) not found on PATH.")
        print("Install LM Studio and make sure 'lms' is available in your terminal.")
    return lms or "lms"


def _run(cmd, check=False):
    """Run a subprocess, surfacing stderr to the current console."""
    return subprocess.run(cmd, shell=False, check=check)


def _start_server(lms):
    print("Starting LM Studio server...")
    try:
        _run([lms, "server", "start"])
    except FileNotFoundError:
        print("ERROR: could not invoke 'lms'. Is LM Studio CLI installed?")
        raise


def _stop_server(lms):
    print("Stopping LM Studio server...")
    try:
        _run([lms, "server", "stop"])
    except Exception as e:
        print(f"  (could not stop server cleanly: {e})")


def _load_model(lms):
    print(
        f"Loading model {MODEL_ID} as '{IDENTIFIER}' (may take a while on first run)..."
    )
    # Kick off in the background so we don't block the CLI. The UI will
    # poll for readiness before enabling chat.
    subprocess.Popen(
        [
            lms,
            "load",
            MODEL_ID,
            "--identifier",
            IDENTIFIER,
            "--context-length",
            CONTEXT_LENGTH,
            "--gpu",
            GPU_MODE,
        ],
        shell=False,
    )


def _unload_model(lms, identifier):
    print(f"Unloading model '{identifier}'...")
    try:
        _run([lms, "unload", identifier])
    except Exception as e:
        print(f"  (could not unload '{identifier}': {e})")


# --- UI launch ------------------------------------------------------------


def _launch_ui_detached():
    """Spawn the UI in its own process so the terminal is free and the
    window survives the terminal closing."""
    pkg_dir = Path(__file__).resolve().parent
    project_root = pkg_dir.parent

    # Prefer pythonw.exe on Windows so no console window pops up with the GUI.
    python_exe = sys.executable
    if os.name == "nt":
        pythonw = Path(python_exe).with_name("pythonw.exe")
        if pythonw.exists():
            python_exe = str(pythonw)

    creationflags = 0
    if os.name == "nt":
        # DETACHED_PROCESS (0x00000008) + CREATE_NEW_PROCESS_GROUP (0x00000200)
        creationflags = 0x00000008 | 0x00000200

    # Capture the UI's stdout/stderr to a log file so import errors /
    # tracebacks from the detached (pythonw) process aren't lost.
    log_handle = open(UI_LOG_FILE, "w", encoding="utf-8")

    proc = subprocess.Popen(
        [python_exe, "-m", "dharampal.ui.chat_window"],
        cwd=str(project_root),
        creationflags=creationflags,
        close_fds=True,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    return proc.pid


def _kill_ui(pid):
    if not pid:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
            )
        else:
            os.kill(int(pid), signal.SIGTERM)
        print(f"Closed chat window (PID {pid}).")
    except Exception as e:
        print(f"  (could not kill UI PID {pid}: {e})")


# --- Floating widget launch -----------------------------------------------


def _launch_widget_detached(chat_pid):
    """Spawn the floating widget in its own detached process."""
    pkg_dir = Path(__file__).resolve().parent
    project_root = pkg_dir.parent

    python_exe = sys.executable
    if os.name == "nt":
        pythonw = Path(python_exe).with_name("pythonw.exe")
        if pythonw.exists():
            python_exe = str(pythonw)

    creationflags = 0
    if os.name == "nt":
        creationflags = 0x00000008 | 0x00000200

    log_handle = open(WIDGET_LOG_FILE, "w", encoding="utf-8")

    proc = subprocess.Popen(
        [python_exe, "-m", "dharampal.ui.floating_widget", "--chat-pid", str(chat_pid)],
        cwd=str(project_root),
        creationflags=creationflags,
        close_fds=True,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    return proc.pid


def _kill_widget(pid):
    if not pid:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
            )
        else:
            os.kill(int(pid), signal.SIGTERM)
        print(f"Closed floating widget (PID {pid}).")
    except Exception as e:
        print(f"  (could not kill widget PID {pid}: {e})")


# --- commands -------------------------------------------------------------


def start():
    print("=== Dharampal: start ===")
    if STATE_FILE.exists():
        print(f"A previous session's state file exists at {STATE_FILE}.")
        print("Run 'dharampal stop' first if anything is still running.")
        # We continue anyway — safer to try a fresh start than refuse.

    lms = _find_lms()
    _start_server(lms)
    _load_model(lms)
    ui_pid = _launch_ui_detached()
    print(f"Chat window launched (PID {ui_pid}).")

    # Launch floating widget after a short delay so the chat window exists
    time.sleep(1)
    widget_pid = _launch_widget_detached(ui_pid)
    print(f"Floating widget launched (PID {widget_pid}).")

    _save_state(ui_pid=ui_pid, widget_pid=widget_pid, identifier=IDENTIFIER)
    print(f"UI log: {UI_LOG_FILE}")
    print(f"Widget log: {WIDGET_LOG_FILE}")
    print("The window will show 'waiting for model' until LM Studio finishes loading.")
    print("Run 'dharampal stop' when you're done.")


def stop():
    print("=== Dharampal: stop ===")
    state = _load_state()
    lms = _find_lms()

    _kill_widget(state.get("widget_pid"))
    _kill_ui(state.get("ui_pid"))
    _unload_model(lms, state.get("identifier", IDENTIFIER))
    _stop_server(lms)

    _clear_state()
    print("Dharampal stopped.")


def main():
    if len(sys.argv) < 2:
        print("Usage: dharampal [start|stop]")
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == "start":
        start()
    elif command == "stop":
        stop()
    else:
        print(f"Unknown command: {command}")
        print("Usage: dharampal [start|stop]")
        sys.exit(1)


if __name__ == "__main__":
    main()
