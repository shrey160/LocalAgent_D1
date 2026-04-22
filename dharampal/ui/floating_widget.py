"""Dharampal floating widget (square floating button).

A small, draggable square that floats on top of all windows.
Click to minimize/maximize the chat window.
Right-click for options menu.

Usage:
    python -m dharampal.ui.floating_widget --chat-pid <PID>

Design notes (for reviewer):
- Uses overrideredirect(True) to remove window decorations
- Always on top via attributes('-topmost', True)
- Finds chat window by title ("Dharampal") using Windows API
- Stores position in %TEMP%/dharampal_widget.pos
- Square shape with slight rounded corners
"""

import argparse
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import customtkinter as ctk

# --- config ---------------------------------------------------------------

WIDGET_SIZE = 60
POS_FILE = Path(tempfile.gettempdir()) / "dharampal_widget.pos"

# Colors matching the chat window theme
COLORS = {
    "bg": "#1a1a2e",
    "accent": "#e94560",
    "accent_hover": "#ff6b6b",
    "text": "#ffffff",
}


def _find_chat_window():
    """Find the chat window handle by its title using Windows API."""
    if os.name != "nt":
        return None

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

        # Find window by exact title
        hwnd = user32.FindWindowW(None, "Dharampal")
        if hwnd:
            return hwnd

        # Try partial match by enumerating windows
        found_hwnd = None

        def callback(hwnd, extra):
            nonlocal found_hwnd
            if not user32.IsWindowVisible(hwnd):
                return True

            # Get window title
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value

                # Match if title contains "Dharampal"
                if "Dharampal" in title:
                    found_hwnd = hwnd
                    return False
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM,
        )
        user32.EnumWindows(EnumWindowsProc(callback), 0)

        return found_hwnd
    except Exception:
        return None


def _minimize_chat():
    """Minimize the chat window."""
    hwnd = _find_chat_window()
    if hwnd and os.name == "nt":
        try:
            import ctypes

            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
            return True
        except Exception:
            pass
    return False


def _restore_chat():
    """Restore and focus the chat window."""
    hwnd = _find_chat_window()
    if hwnd and os.name == "nt":
        try:
            import ctypes

            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            pass
    return False


class FloatingWidget(ctk.CTkToplevel):
    """Floating square widget."""

    def __init__(self, chat_pid=None):
        super().__init__()

        self.chat_pid = chat_pid
        self.chat_visible = True
        self.chat_hwnd = None

        # Remove window decorations (no title bar, no border)
        self.overrideredirect(True)

        # Always on top
        self.attributes("-topmost", True)

        # Set size (square)
        self.geometry(f"{WIDGET_SIZE}x{WIDGET_SIZE}")
        self.configure(fg_color=COLORS["bg"])

        # Position at bottom-right initially, or load saved position
        self._load_position()

        # Create the square button with small rounded corners
        self.button = ctk.CTkButton(
            self,
            text="D",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS["text"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            width=WIDGET_SIZE - 4,
            height=WIDGET_SIZE - 4,
            corner_radius=12,  # Slight rounded corners, not circular
            command=self._on_click,
        )
        self.button.place(relx=0.5, rely=0.5, anchor="center")

        # Bind dragging events
        self.bind("<Button-1>", self._start_drag)
        self.bind("<B1-Motion>", self._on_drag)
        self.button.bind("<Button-1>", self._start_drag)
        self.button.bind("<B1-Motion>", self._on_drag)

        # Right-click menu
        self.bind("<Button-3>", self._show_menu)
        self.button.bind("<Button-3>", self._show_menu)

        # Auto-save position periodically
        self._start_position_autosave()

    # --- Position management ------------------------------------------------

    def _load_position(self):
        """Load saved position or default to bottom-right."""
        if POS_FILE.exists():
            try:
                x, y = map(int, POS_FILE.read_text().strip().split(","))
                self.geometry(f"+{x}+{y}")
                return
            except Exception:
                pass

        # Default: bottom-right of screen
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - WIDGET_SIZE - 20
        y = screen_height - WIDGET_SIZE - 80
        self.geometry(f"+{x}+{y}")

    def _save_position(self):
        """Save current position to file."""
        try:
            x = self.winfo_x()
            y = self.winfo_y()
            POS_FILE.write_text(f"{x},{y}")
        except Exception:
            pass

    def _start_position_autosave(self):
        """Auto-save position every 5 seconds."""

        def autosave():
            while True:
                time.sleep(5)
                try:
                    if self.winfo_exists():
                        self._save_position()
                except Exception:
                    break

        threading.Thread(target=autosave, daemon=True).start()

    # --- Dragging -----------------------------------------------------------

    def _start_drag(self, event):
        """Start dragging the widget."""
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _on_drag(self, event):
        """Handle dragging motion."""
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")

    # --- Chat window toggle -------------------------------------------------

    def _on_click(self):
        """Handle left click on the square."""
        if self.chat_visible:
            if _minimize_chat():
                self.chat_visible = False
                self.button.configure(text="▲")  # Up arrow when minimized
        else:
            if _restore_chat():
                self.chat_visible = True
                self.button.configure(text="D")  # D when visible

    # --- Right-click menu ---------------------------------------------------

    def _show_menu(self, event):
        """Show right-click context menu."""
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        menu.configure(fg_color=COLORS["bg"])

        # Menu items
        ctk.CTkButton(
            menu,
            text="Show/Hide Chat",
            command=lambda: [self._on_click(), menu.destroy()],
            fg_color="transparent",
            hover_color=COLORS["accent"],
        ).pack(padx=5, pady=2)

        ctk.CTkButton(
            menu,
            text="Reset Position",
            command=lambda: [self._reset_position(), menu.destroy()],
            fg_color="transparent",
            hover_color=COLORS["accent"],
        ).pack(padx=5, pady=2)

        ctk.CTkButton(
            menu,
            text="Exit Widget",
            command=self.destroy,
            fg_color="transparent",
            hover_color=COLORS["accent"],
        ).pack(padx=5, pady=2)

        # Auto-close menu when clicking elsewhere
        def close_menu(_event):
            menu.destroy()
            self.unbind("<Button-1>", close_binding)

        close_binding = self.bind("<Button-1>", close_menu)

    def _reset_position(self):
        """Reset to bottom-right corner."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - WIDGET_SIZE - 20
        y = screen_height - WIDGET_SIZE - 80
        self.geometry(f"+{x}+{y}")
        self._save_position()


def run_widget(chat_pid=None):
    """Run the floating widget standalone."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    # Create hidden root window (required for Toplevel)
    root = ctk.CTk()
    root.withdraw()
    root.geometry("0x0")

    # Create floating widget
    widget = FloatingWidget(chat_pid=chat_pid)

    # Keep root alive but hidden
    root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dharampal floating widget")
    parser.add_argument("--chat-pid", type=int, help="PID of the chat window process")
    args = parser.parse_args()

    run_widget(chat_pid=args.chat_pid)
