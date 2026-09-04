#!/usr/bin/env python3
"""Show a floating label on every connected X11 output until Ctrl+C."""

from __future__ import annotations

import re
import signal
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass

OUTPUT_RE = re.compile(
    r"^(\S+) connected(?: primary)? (\d+)x(\d+)\+(\d+)\+(\d+)",
    re.MULTILINE,
)

WINDOW_W = 420
WINDOW_H = 160


@dataclass(frozen=True)
class Output:
    name: str
    width: int
    height: int
    x: int
    y: int

    @property
    def center_x(self) -> int:
        return self.x + (self.width - WINDOW_W) // 2

    @property
    def center_y(self) -> int:
        return self.y + (self.height - WINDOW_H) // 2


def list_outputs() -> list[Output]:
    try:
        result = subprocess.run(
            ["xrandr", "--query"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("xrandr is required but was not found", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or "xrandr failed", file=sys.stderr)
        sys.exit(1)

    outputs = [
        Output(name, int(w), int(h), int(x), int(y))
        for name, w, h, x, y in OUTPUT_RE.findall(result.stdout)
    ]
    if not outputs:
        print("No connected X11 outputs with a mode found", file=sys.stderr)
        sys.exit(1)
    return outputs


def make_label(parent: tk.Tk, output: Output) -> tk.Toplevel:
    win = tk.Toplevel(parent)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    try:
        win.attributes("-alpha", 0.92)
    except tk.TclError:
        pass

    win.configure(bg="#111111")
    win.geometry(f"{WINDOW_W}x{WINDOW_H}+{output.center_x}+{output.center_y}")

    frame = tk.Frame(win, bg="#111111", highlightbackground="#f0c040", highlightthickness=3)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        frame,
        text=output.name,
        fg="#f0c040",
        bg="#111111",
        font=("sans-serif", 36, "bold"),
    ).pack(expand=True)

    return win


def main() -> None:
    outputs = list_outputs()
    root = tk.Tk()
    root.withdraw()

    windows = [make_label(root, output) for output in outputs]

    def shutdown(*_: object) -> None:
        for win in windows:
            win.destroy()
        root.quit()

    signal.signal(signal.SIGINT, shutdown)
    # Tk's mainloop blocks signals until it next wakes; poll so Ctrl+C is prompt.
    def poll() -> None:
        root.after(200, poll)

    root.after(200, poll)
    print("Showing output names — Ctrl+C to quit", file=sys.stderr)
    root.mainloop()


if __name__ == "__main__":
    main()
