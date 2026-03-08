"""Imagine CLI - Typer-based interface."""

from datetime import datetime
from pathlib import Path

import typer

from .config import load_config, validate_api_key
from .display import display_image
from .lumenfall import generate_image, list_models

# For testing: bypass API and always show this image
TEST_IMAGE_PATH = Path(__file__).resolve().parent.parent.parent / "intense-anime-portrait-stockcake.webp"

app = typer.Typer(
    name="imagine",
    help="Generate AI images in your terminal via Lumenfall API.",
)


def _run_generate(
    prompt: str,
    model: str,
    size: str,
    save: Path | None,
) -> None:
    """Generate and display image (one-shot mode)."""
    if TEST_IMAGE_PATH.exists():
        image_bytes = TEST_IMAGE_PATH.read_bytes()
        typer.echo("(test mode: showing local image)", err=True)
    else:
        validate_api_key()
        typer.echo("Generating...", err=True)
        try:
            image_bytes = generate_image(prompt=prompt, model=model, size=size)
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
    display_image(image_bytes)
    out_path = save or (Path.cwd() / f"imagine_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png")
    out_path.write_bytes(image_bytes)
    typer.echo(f"Saved to {out_path}", err=True)


@app.callback(invoke_without_command=True)
def main(
    prompt: str = typer.Argument(
        None,
        help="Text prompt for image generation. Omit for interactive mode.",
    ),
    model: str = typer.Option(
        None,
        "--model",
        "-m",
        help="Lumenfall model ID (e.g. gemini-3-pro-image, gpt-image-1.5).",
    ),
    size: str = typer.Option(
        None,
        "--size",
        "-s",
        help="Image size (e.g. 1024x1024).",
    ),
    save: Path | None = typer.Option(
        None,
        "--save",
        "-o",
        path_type=Path,
        help="Save image to file.",
    ),
    list_models_flag: bool = typer.Option(
        False,
        "--list-models",
        help="List available Lumenfall models and exit.",
    ),
) -> None:
    """Generate AI images in your terminal."""
    config = load_config()
    model = model or config["model"]
    size = size or config["size"]

    if list_models_flag:
        validate_api_key()
        try:
            models = list_models()
            for m in models:
                typer.echo(m)
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
        return

    if prompt is None or (isinstance(prompt, str) and not prompt.strip()):
        from .tui import run_tui

        run_tui(model=model, size=size)
        return

    _run_generate(prompt=prompt, model=model, size=size, save=save)


def run() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    app()
