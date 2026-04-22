"""Dharampal modern chat window.

A clean, modern customtkinter chat UI with message bubbles, dark theme,
and smooth interactions. On startup it polls LM Studio until the model is
ready, then greets the user.

Design notes (for reviewer):
- Dark theme by default for a modern look
- Message bubbles instead of plain text
- Color-coded: user (blue), AI (green), system (gray), error (red)
- Header bar with status indicator
- Smooth auto-scroll
- Loading animation when AI is thinking
- Clear chat button
"""

import threading
import time
from datetime import datetime

import customtkinter as ctk

try:
    import requests
except ImportError:
    requests = None

from dharampal.agent.graph import get_response

LM_STUDIO_URL = "http://localhost:1234/v1"
MODEL_IDENTIFIER = "friday-main"
READINESS_TIMEOUT_SECONDS = 600

# Color scheme
COLORS = {
    "bg": "#1a1a2e",  # Deep dark blue background
    "bg_secondary": "#16213e",  # Slightly lighter for frames
    "user_bubble": "#0f3460",  # Dark blue for user
    "ai_bubble": "#1a472a",  # Dark green for AI
    "system_bubble": "#2d2d2d",  # Gray for system
    "error_bubble": "#5c1a1a",  # Dark red for errors
    "text_primary": "#eaeaea",  # Primary text
    "text_secondary": "#a0a0a0",  # Secondary/muted text
    "accent": "#e94560",  # Pink accent
    "input_bg": "#0f0f23",  # Input background
    "status_ready": "#4ade80",  # Green dot
    "status_busy": "#fbbf24",  # Yellow/orange dot
    "status_offline": "#ef4444",  # Red dot
}


class ModernChatWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Dharampal")
        self.geometry("900x750")
        self.minsize(600, 400)
        self.configure(fg_color=COLORS["bg"])

        # Configure grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Header Bar ---
        self.header = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], height=50)
        self.header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header.grid_propagate(False)

        # App title
        self.title_label = ctk.CTkLabel(
            self.header,
            text="Dharampal",
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS["text_primary"],
        )
        self.title_label.pack(side="left", padx=20, pady=10)

        # Status indicator frame
        self.status_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.status_frame.pack(side="right", padx=20, pady=10)

        # Status dot
        self.status_dot = ctk.CTkLabel(
            self.status_frame,
            text="●",
            font=("Segoe UI", 12),
            text_color=COLORS["status_offline"],
        )
        self.status_dot.pack(side="left", padx=(0, 5))

        # Status text
        self.status_text = ctk.CTkLabel(
            self.status_frame,
            text="Connecting...",
            font=("Segoe UI", 11),
            text_color=COLORS["text_secondary"],
        )
        self.status_text.pack(side="left")

        # Clear button
        self.clear_btn = ctk.CTkButton(
            self.header,
            text="Clear",
            font=("Segoe UI", 11),
            width=60,
            height=28,
            fg_color="transparent",
            hover_color=COLORS["bg"],
            command=self.clear_chat,
        )
        self.clear_btn.pack(side="right", padx=(0, 10), pady=10)

        # --- Chat Area ---
        self.chat_container = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        self.chat_container.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)
        self.chat_container.grid_rowconfigure(0, weight=1)
        self.chat_container.grid_columnconfigure(0, weight=1)

        # Scrollable frame for messages
        self.chat_scroll = ctk.CTkScrollableFrame(
            self.chat_container,
            fg_color=COLORS["bg"],
            scrollbar_button_color=COLORS["bg_secondary"],
            scrollbar_button_hover_color=COLORS["user_bubble"],
        )
        self.chat_scroll.grid(row=0, column=0, sticky="nsew")
        self.chat_scroll.grid_columnconfigure(0, weight=1)

        # Messages list to track widgets
        self.messages = []

        # --- Input Area ---
        self.input_frame = ctk.CTkFrame(
            self, fg_color=COLORS["bg_secondary"], height=70
        )
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        self.input_frame.grid_propagate(False)
        self.input_frame.grid_columnconfigure(0, weight=1)

        # Input field
        self.entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Waiting for model...",
            font=("Segoe UI", 13),
            fg_color=COLORS["input_bg"],
            border_color=COLORS["bg_secondary"],
            border_width=1,
            corner_radius=20,
            height=40,
        )
        self.entry.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="ew")
        self.entry.bind("<Return>", self.send_message)
        self.entry.configure(state="disabled")

        # Send button
        self.send_btn = ctk.CTkButton(
            self.input_frame,
            text="➤",
            font=("Segoe UI", 16),
            width=40,
            height=40,
            corner_radius=20,
            fg_color=COLORS["accent"],
            hover_color="#d63d56",
            command=self.send_message,
        )
        self.send_btn.grid(row=0, column=1, padx=(0, 15), pady=15)
        self.send_btn.configure(state="disabled")

        # Processing indicator (hidden by default)
        self.processing_label = ctk.CTkLabel(
            self.input_frame,
            text="",
            font=("Segoe UI", 10),
            text_color=COLORS["status_busy"],
        )
        self.processing_label.grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 5)
        )

        # Show initial system message
        self.add_system_message(
            "Dharampal is starting up. Waiting for LM Studio to load the model..."
        )

        # Initialize processing flag
        self._is_processing = False

        # Start background thread
        threading.Thread(target=self._startup_sequence, daemon=True).start()

    # --- Message Display ---

    def add_message(self, sender, text, msg_type="ai"):
        """Add a message bubble to the chat."""
        self.after(0, self._add_message_internal, sender, text, msg_type)

    def _add_message_internal(self, sender, text, msg_type):
        # Container frame for the message
        msg_frame = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        msg_frame.grid(
            row=len(self.messages), column=0, sticky="ew", pady=(5, 5), padx=5
        )
        msg_frame.grid_columnconfigure(0, weight=1)

        # Timestamp
        timestamp = datetime.now().strftime("%H:%M")

        # Determine alignment and colors based on message type
        if msg_type == "user":
            bubble_color = COLORS["user_bubble"]
            align = "e"
            sender_text = "You"
            sender_color = COLORS["accent"]
        elif msg_type == "system":
            bubble_color = COLORS["system_bubble"]
            align = "center"
            sender_text = "System"
            sender_color = COLORS["text_secondary"]
        elif msg_type == "error":
            bubble_color = COLORS["error_bubble"]
            align = "w"
            sender_text = "Error"
            sender_color = COLORS["status_offline"]
        else:  # ai
            bubble_color = COLORS["ai_bubble"]
            align = "w"
            sender_text = "Dharampal"
            sender_color = COLORS["status_ready"]

        # Inner frame for alignment
        inner_frame = ctk.CTkFrame(msg_frame, fg_color="transparent")
        inner_frame.grid(row=0, column=0, sticky=align)

        # Sender label (only for user and AI, not system)
        if msg_type != "system":
            sender_label = ctk.CTkLabel(
                inner_frame,
                text=f"{sender_text}  •  {timestamp}",
                font=("Segoe UI", 9),
                text_color=sender_color,
            )
            sender_label.pack(anchor=align, padx=10, pady=(0, 2))

        # Message bubble
        bubble = ctk.CTkFrame(
            inner_frame,
            fg_color=bubble_color,
            corner_radius=15,
        )
        bubble.pack(anchor=align, padx=5, pady=(0, 5))

        # Message text
        msg_label = ctk.CTkLabel(
            bubble,
            text=text,
            font=("Segoe UI", 12),
            text_color=COLORS["text_primary"],
            wraplength=500 if msg_type in ["user", "ai"] else 600,
            justify="left" if msg_type in ["user", "ai", "error"] else "center",
        )
        msg_label.pack(padx=15, pady=10)

        # Store reference
        self.messages.append(msg_frame)

        # Auto-scroll to bottom
        self.after(100, self._scroll_to_bottom)

    def add_user_message(self, text):
        """Add a user message."""
        self.add_message("You", text, "user")

    def add_ai_message(self, text):
        """Add an AI message."""
        self.add_message("Dharampal", text, "ai")

    def add_system_message(self, text):
        """Add a system message."""
        self.add_message("System", text, "system")

    def add_error_message(self, text):
        """Add an error message."""
        self.add_message("Error", text, "error")

    def _scroll_to_bottom(self):
        """Scroll to the latest message."""
        if self.messages:
            self.messages[-1].update_idletasks()
            self.chat_scroll._parent_canvas.yview_moveto(1.0)

    def clear_chat(self):
        """Clear all messages."""
        for msg in self.messages:
            msg.destroy()
        self.messages.clear()
        self.add_system_message("Chat cleared.")

    # --- Status Management ---

    def set_status(self, text, status_type="busy"):
        """Update status with color-coded indicator."""
        self.after(0, self._set_status_internal, text, status_type)

    def _set_status_internal(self, text, status_type):
        self.status_text.configure(text=text)

        if status_type == "ready":
            color = COLORS["status_ready"]
        elif status_type == "busy":
            color = COLORS["status_busy"]
        elif status_type == "error":
            color = COLORS["status_offline"]
        else:
            color = COLORS["text_secondary"]

        self.status_dot.configure(text_color=color)

    # --- Startup Sequence ---

    def _wait_for_model(self, timeout=READINESS_TIMEOUT_SECONDS):
        """Poll LM Studio until model is ready."""
        if requests is None:
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
                    self.set_status(f"Loading model... (attempt {attempt})", "busy")
                else:
                    self.set_status(
                        f"Server responded {r.status_code}, retrying...", "busy"
                    )
            except Exception:
                self.set_status(
                    f"Connecting to LM Studio... (attempt {attempt})", "busy"
                )
            time.sleep(2)
        return False

    def _enable_entry(self):
        """Enable the entry field for user input."""

        def _do():
            self.entry.configure(
                state="normal", placeholder_text="Type your message..."
            )
            self.send_btn.configure(state="normal")
            self.entry.focus_set()

        self.after(0, _do)

    def _startup_sequence(self):
        """Initialize the agent and show greeting."""
        ready = self._wait_for_model()

        if not ready:
            self.set_status("Model timeout — check LM Studio", "error")
            self.add_error_message(
                "Model did not become ready in time. Input is enabled but may fail."
            )
            self._enable_entry()
            return

        self.set_status(f"Ready", "ready")
        self._enable_entry()

        try:
            greeting = get_response(
                "Greet the user briefly as Dharampal, a helpful AI assistant. One or two sentences."
            )
            self.add_ai_message(greeting)
        except Exception as e:
            self.add_error_message(f"Could not fetch greeting: {e}")

    # --- Message Handling ---

    def send_message(self, event=None):
        """Send user message and get AI response."""
        user_text = self.entry.get().strip()
        if not user_text:
            return

        # Check if already processing
        if self._is_processing:
            self.add_system_message("Still processing previous message. Please wait...")
            return

        # Clear input
        self.entry.delete(0, "end")

        # Show user message
        self.add_user_message(user_text)

        # Update status and show processing indicator
        self.set_status("Thinking...", "busy")
        self._is_processing = True
        self._show_processing_indicator(True)

        # Process in background thread
        def _background_process():
            try:
                self._process_message(user_text)
            except Exception as e:
                import traceback

                print(f"[CHAT ERROR] Background thread exception: {e}")
                traceback.print_exc()
            finally:
                self._processing_complete()

        threading.Thread(target=_background_process, daemon=True).start()

    def _process_message(self, msg):
        """Process message in background thread with timeout safety."""
        import traceback

        response = None
        error_occurred = False

        try:
            print(f"[CHAT] Processing message: {msg!r}")

            # Use a thread with timeout to prevent hanging
            response_container = [None]
            exception_container = [None]

            def _get_response_with_timeout():
                try:
                    response_container[0] = get_response(msg)
                except Exception as e:
                    exception_container[0] = e

            # Start the response thread
            response_thread = threading.Thread(
                target=_get_response_with_timeout, daemon=True
            )
            response_thread.start()

            # Wait with timeout (30 seconds max)
            response_thread.join(timeout=30.0)

            if response_thread.is_alive():
                # Thread is still running after timeout
                print("[CHAT ERROR] get_response timed out after 30 seconds")
                self.add_error_message(
                    "Request timed out. The model is taking too long to respond."
                )
                self.set_status("Timeout", "error")
                error_occurred = True
            elif exception_container[0] is not None:
                # An exception occurred
                raise exception_container[0]
            else:
                # Success
                response = response_container[0]
                print(f"[CHAT] Got response: {response[:100]!r}...")
                self.add_ai_message(response)
                self.set_status("Ready", "ready")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            self.add_error_message(error_msg)
            self.set_status("Error occurred", "error")
            # Log full traceback
            traceback_str = traceback.format_exc()
            print(f"[CHAT ERROR] {error_msg}\n{traceback_str}")
            error_occurred = True
        finally:
            print("[CHAT] Processing complete")
            if error_occurred:
                print("[CHAT] An error occurred during processing")

    def _show_processing_indicator(self, show=True):
        """Show or hide the processing indicator."""

        def _do():
            if show:
                self.processing_label.configure(text="⚡ Processing...")
                self.send_btn.configure(state="disabled")
            else:
                self.processing_label.configure(text="")
                self.send_btn.configure(state="normal")
                self.entry.focus_set()

        self.after(0, _do)

    def _processing_complete(self):
        """Called when processing is complete."""
        self._is_processing = False
        self._show_processing_indicator(False)
        print("[CHAT] Processing complete, input remains enabled")


def run_app():
    """Launch the modern chat application."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = ModernChatWindow()
    app.mainloop()


if __name__ == "__main__":
    run_app()
