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
        # Get terminal size for better resolution
        try:
            term_cols = os.get_terminal_size().columns
        except OSError:
            term_cols = 80

        # chafa outputs Sixel to stdout
        # --work=9 for best quality (more processing)
        # --scale=max prevents upscaling (only downscale if needed)
        # --fg-only leaves background untouched (no black bar on right)
        cmd = [
            "chafa",
            "-f", "sixel",
            "--scale=max",           # don't upscale, only shrink if needed
            "--work=9",              # best quality
            "--fg-only",             # no background fill
            tmp_path,
        ]
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
    """Display image inline using Unicode half-blocks (works in any terminal)."""
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")

    # Get terminal width and scale image to fit
    try:
        term_width = os.get_terminal_size().columns
    except OSError:
        term_width = 80

    # Scale image to fit terminal width (leave some margin)
    max_width = min(term_width - 4, 120)
    scale = max_width / img.width
    new_width = int(img.width * scale)
    # Half-blocks show 2 pixel rows per character line
    # Multiply by ~1.0 since half-blocks already compensate for char aspect ratio
    new_height = int(img.height * scale)
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Render using Unicode half-blocks: upper half = ▀
    # Each output row represents 2 pixel rows
    pixels = img.load()
    output = []

    for y in range(0, new_height - 1, 2):
        row = []
        for x in range(new_width):
            # Top pixel
            r1, g1, b1 = pixels[x, y]
            # Bottom pixel (or same as top if at edge)
            if y + 1 < new_height:
                r2, g2, b2 = pixels[x, y + 1]
            else:
                r2, g2, b2 = r1, g1, b1

            # Use ANSI 24-bit color: fg for top half (▀), bg for bottom half
            row.append(f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m\u2580")
        output.append("".join(row) + "\033[0m")

    # Write with UTF-8 encoding to handle Unicode on Windows
    result = "\n".join(output) + "\n"
    sys.stdout.buffer.write(result.encode("utf-8"))
    sys.stdout.buffer.flush()


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
