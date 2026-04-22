"""Dharampal chat window.

A minimal customtkinter chat UI. On startup it polls LM Studio until the
model identified as `friday-main` is ready, then asks the agent for a
short greeting. The user input is disabled until the model is reachable
so we don't surface confusing "connection refused" errors.
"""

import threading
import time

import customtkinter as ctk

try:
    import requests
except ImportError:  # pragma: no cover - requests is a declared dep
    requests = None

from dharampal.agent.graph import get_response

LM_STUDIO_URL = "http://localhost:1234/v1"
MODEL_IDENTIFIER = "friday-main"
READINESS_TIMEOUT_SECONDS = 600  # give slow first-time model loads room to finish


class ChatWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dharampal AI Agent")
        self.geometry("720x820")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Chat history (read-only)
        self.chat_history = ctk.CTkTextbox(
            self, state="disabled", wrap="word", font=("Segoe UI", 13)
        )
        self.chat_history.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # Input row
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Waiting for model to load...",
            font=("Segoe UI", 13),
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=6)
        self.entry.bind("<Return>", self.send_message)
        self.entry.configure(state="disabled")

        self.send_btn = ctk.CTkButton(
            self.input_frame, text="Send", command=self.send_message, width=100
        )
        self.send_btn.pack(side="right")
        self.send_btn.configure(state="disabled")

        # Status bar
        self.status_label = ctk.CTkLabel(
            self, text="Connecting to LM Studio...", anchor="w", font=("Segoe UI", 11)
        )
        self.status_label.grid(row=2, column=0, padx=20, pady=(0, 12), sticky="ew")

        self.append_message(
            "System",
            "Dharampal is starting up. Waiting for LM Studio to finish loading the model...",
        )

        threading.Thread(target=self._startup_sequence, daemon=True).start()

    # --- UI helpers --------------------------------------------------------

    def append_message(self, sender, text):
        self.after(0, self._append_message_internal, sender, text)

    def _append_message_internal(self, sender, text):
        self.chat_history.configure(state="normal")
        self.chat_history.insert("end", f"{sender}: {text}\n\n")
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")

    def set_status(self, text):
        self.after(0, lambda: self.status_label.configure(text=text))

    def _enable_input(self):
        def _do():
            self.entry.configure(state="normal", placeholder_text="Type your message...")
            self.send_btn.configure(state="normal")
            self.entry.focus_set()
        self.after(0, _do)

    # --- readiness + greeting ---------------------------------------------

    def _wait_for_model(self, timeout=READINESS_TIMEOUT_SECONDS):
        """Poll LM Studio's /v1/models endpoint until our identifier appears."""
        if requests is None:
            # Fall back to time-based wait if requests isn't available.
            time.sleep(5)
            return True

        deadline = time.time() + timeout
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            try:
                r = requests.get(f"{LM_STUDIO_URL}/models", timeout=3)
                if r.status_code == 200:
                    data = r.json().get("data", []) or []
                    ids = [m.get("id", "") for m in data]
                    if any(MODEL_IDENTIFIER in mid for mid in ids):
                        return True
                    self.set_status(
                        f"LM Studio reachable, waiting for '{MODEL_IDENTIFIER}' to load... (attempt {attempt})"
                    )
                else:
                    self.set_status(
                        f"LM Studio responded with status {r.status_code}, retrying..."
                    )
            except Exception:
                self.set_status(
                    f"LM Studio not reachable yet, retrying... (attempt {attempt})"
                )
            time.sleep(2)
        return False

    def _startup_sequence(self):
        ready = self._wait_for_model()
        if not ready:
            self.set_status("Timed out waiting for the model. You can still try sending a message.")
            self.append_message(
                "System",
                "Model did not become ready in time. Input is enabled — requests may still fail.",
            )
            self._enable_input()
            return

        self.set_status(f"Model '{MODEL_IDENTIFIER}' ready.")
        self._enable_input()
        try:
            greeting = get_response(
                "Greet the user briefly as Dharampal, a helpful AI assistant. One or two sentences."
            )
            self.append_message("Dharampal", greeting)
        except Exception as e:
            self.append_message("System", f"Could not fetch greeting: {e}")

    # --- send / receive ----------------------------------------------------

    def send_message(self, event=None):
        if str(self.send_btn.cget("state")) == "disabled":
            return
        user_text = self.entry.get().strip()
        if not user_text:
            return

        self.entry.delete(0, "end")
        self.append_message("You", user_text)
        self.set_status("Dharampal is thinking...")

        threading.Thread(
            target=self._process_message, args=(user_text,), daemon=True
        ).start()

    def _process_message(self, msg):
        try:
            response = get_response(msg)
            self.append_message("Dharampal", response)
            self.set_status(f"Model '{MODEL_IDENTIFIER}' ready.")
        except Exception as e:
            self.append_message("System Error", str(e))
            self.set_status("Error — see chat.")


def run_app():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = ChatWindow()
    app.mainloop()


if __name__ == "__main__":
    run_app()
