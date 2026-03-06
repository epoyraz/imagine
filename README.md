# Imagine

A CLI for AI image generation that shows images directly in your terminal. Describe an image, press Enter, and it appears inline—like Claude Code for images.

Powered by [Lumenfall](https://lumenfall.ai), a unified API for 58+ image models (Gemini, GPT Image, FLUX, and more).

## Requirements

- **Python 3.10+**
- A [Lumenfall](https://lumenfall.ai) API key (free credits available)

## Installation

### From source (recommended)

Clone the repo and install in editable mode:

```bash
git clone <repo-url>
cd imagine
pip install -e .
```

Or install the package without cloning:

```bash
pip install .
```

### Virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## Setup

### 1. Get an API key

1. Sign up at [lumenfall.ai](https://lumenfall.ai).
2. Copy your API key from the dashboard.

### 2. Set the environment variable

**Current session (macOS/Linux):**

```bash
export LUMENFALL_API_KEY=lmnfl_your_key_here
```

**Persistent (add to `~/.zshrc`, `~/.bashrc`, or equivalent):**

```bash
echo 'export LUMENFALL_API_KEY=lmnfl_your_key_here' >> ~/.zshrc
source ~/.zshrc
```

**Windows (PowerShell):**

```powershell
$env:LUMENFALL_API_KEY = "lmnfl_your_key_here"
```

Alternatively, you can set `OPENAI_API_KEY`; the app will use it if `LUMENFALL_API_KEY` is not set.

## Usage

### One-shot: generate from a single prompt

```bash
imagine "a serene mountain at sunset"
```

The image is displayed in the terminal and saved in the **current working directory** as `imagine_YYYY-MM-DD_HH-MM-SS.png`.

**Custom output path:**

```bash
imagine "a cat in space" -o ./my-image.png
```

**Model and size:**

```bash
imagine "portrait of a warrior" --model gpt-image-1.5 --size 1024x1024
# or short flags
imagine "..." -m gemini-3-pro-image -s 1024x1024
```

**List available models:**

```bash
imagine --list-models
```

### Interactive mode (full-screen TUI)

```bash
imagine
```

Launches a Textual TUI:

- **Prompt field** at the bottom: type a description and press **Enter** to generate.
- **Slash menu**: type **`/`** to open the menu:
  - **models** — pick a model from a list (arrow keys + Enter).
  - **exit** — quit the app.
- **Escape** — close any open menu.
- Generated images are shown inline (scaled to fit) and saved to the current working directory as `imagine_YYYY-MM-DD_HH-MM-SS.png`.

## CLI reference

| Option | Short | Description |
|--------|-------|-------------|
| `--model` | `-m` | Model ID (e.g. `gemini-3-pro-image`) |
| `--size` | `-s` | Image size (e.g. `1024x1024`) |
| `--save` | `-o` | Save path (default: cwd with timestamp) |
| `--list-models` | | List available models and exit |

Without a prompt argument, `imagine` starts the interactive TUI.

## Configuration

### Config file (optional)

Create `~/.config/imagine/config.json` (or `%APPDATA%\imagine\config.json` on Windows) to set default model and size:

```json
{
  "model": "gemini-3-pro-image",
  "size": "1024x1024"
}
```

CLI options override these values.

### Environment

| Variable | Description |
|----------|-------------|
| `LUMENFALL_API_KEY` | Lumenfall API key (primary) |
| `OPENAI_API_KEY` | Fallback if `LUMENFALL_API_KEY` is not set |

## Terminal support

Inline image display depends on your terminal:

| Terminal | Protocol | Platforms |
|----------|----------|-----------|
| iTerm2 | iTerm2 inline | macOS |
| WezTerm | iTerm2 inline | macOS, Linux, Windows |
| Kitty / Ghostty | Kitty Graphics Protocol | macOS, Linux |
| Windows Terminal 1.22+ | Sixel | Windows |

If no protocol is available, the image is saved to a temp file and opened with the system viewer, and the path is printed.

## Project structure

```
imagine/
├── pyproject.toml
├── README.md
├── src/imagine/
│   ├── __init__.py
│   ├── __main__.py      # python -m imagine
│   ├── cli.py           # Typer CLI, one-shot & TUI entry
│   ├── tui.py           # Textual interactive app
│   ├── lumenfall.py     # Lumenfall API client
│   ├── display.py       # Terminal image display (imgcat/Kitty/Sixel)
│   └── config.py        # API key, config file, defaults
└── tests/
```

## Development

**Run tests:**

```bash
pip install -e ".[dev]"
pytest
```

**Editable install:**

```bash
pip install -e .
```

Changes in `src/imagine/` are used immediately when you run `imagine`.

## License

MIT
