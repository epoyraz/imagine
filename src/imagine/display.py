"""Terminal image display with multi-protocol support."""

import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal

TerminalType = Literal["iterm2", "kitty", "sixel", "fallback"]


def detect_terminal() -> TerminalType:
    """
    Detect terminal type for choosing display protocol.

    - iterm2: iTerm2, WezTerm (macOS, Linux, Windows)
    - kitty: Kitty, Ghostty (both support Kitty graphics protocol)
    - sixel: Windows Terminal 1.22+, XTerm, etc.
    - fallback: Save to temp and print path
    """
    term_program = os.environ.get("TERM_PROGRAM", "")
    term = os.environ.get("TERM", "")

    # iTerm2 and WezTerm support iTerm2 inline images protocol
    if "iTerm" in term_program or term_program == "WezTerm":
        return "iterm2"

    # Kitty and Ghostty support Kitty graphics protocol (Ghostty sets TERM=xterm-ghostty)
    if term_program == "kitty" or term_program == "Ghostty" or "ghostty" in term.lower():
        return "kitty"

    # Windows Terminal (1.22+) supports Sixel
    if os.environ.get("WT_SESSION"):
        return "sixel"

    # Some Linux terminals support Sixel (xterm-256color with sixel, mlterm, etc.)
    if "sixel" in term.lower() or "mlterm" in term:
        return "sixel"

    return "fallback"


def _display_iterm2(image_bytes: bytes, width: str | None = "auto") -> None:
    """Display via iTerm2/WezTerm protocol using imgcat."""
    import imgcat

    f = io.BytesIO(image_bytes)
    if width and width != "auto":
        imgcat.imgcat(f, width=width)
    else:
        imgcat.imgcat(f)


def _display_kitty(image_bytes: bytes, width: str | None = "auto") -> None:
    """Display via Kitty graphics protocol (works in Kitty and Ghostty)."""
    import base64

    # Kitty protocol: ESC _G a=T,f=100,m=<0|1>;<base64> ESC \
    # Chunks max 4096 bytes; all but last must be multiple of 4 (base64 alignment)
    encoded = base64.standard_b64encode(image_bytes).decode("ascii")
    chunk_size = 4092  # multiple of 4 so every non-last chunk is valid
    first = True
    out = sys.stdout.buffer

    for i in range(0, len(encoded), chunk_size):
        chunk = encoded[i : i + chunk_size]
        more = 1 if i + chunk_size < len(encoded) else 0
        if first:
            control = f"a=T,f=100,m={more};"
            first = False
        else:
            control = f"m={more};"
        out.write(b"\033_G" + control.encode("ascii") + chunk.encode("ascii") + b"\033\\")
    out.flush()


def _display_sixel(image_bytes: bytes, width: str | None = "auto") -> None:
    """Display via Sixel protocol using chafa if available."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    try:
        # chafa outputs Sixel to stdout
        cmd = ["chafa", "-f", "sixel", tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            sys.stdout.write(result.stdout)
            sys.stdout.flush()
        else:
            _display_fallback(image_bytes)
    except FileNotFoundError:
        _display_fallback(image_bytes)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _display_fallback(image_bytes: bytes) -> None:
    """Save to temp file, open with system viewer, and print path."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(image_bytes)
        path = tmp.name
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        elif sys.platform == "win32":
            subprocess.run(["start", "", path], shell=True, check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except FileNotFoundError:
        pass
    print(f"Image saved to {path}")
    print("(Use iTerm2, WezTerm, Kitty, or Windows Terminal 1.22+ for inline display)")


def display_image(image_bytes: bytes, width: str | None = "auto") -> None:
    """
    Display image in terminal using the best available protocol.

    Args:
        image_bytes: Raw PNG bytes
        width: Display width (e.g. "auto", "50%", "10" for 10 lines)
    """
    term = detect_terminal()
    if term == "iterm2":
        _display_iterm2(image_bytes, width)
    elif term == "kitty":
        _display_kitty(image_bytes, width)
    elif term == "sixel":
        _display_sixel(image_bytes, width)
    else:
        _display_fallback(image_bytes)
