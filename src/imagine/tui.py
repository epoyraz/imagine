"""Textual TUI for Imagine - full-screen Claude Code-style interface."""

import asyncio
import io
from datetime import datetime
from pathlib import Path

from PIL import Image as PILImage

# Import before Textual app starts - required for protocol detection
from textual_image.widget import Image as TextualImage

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Footer, Input, LoadingIndicator, OptionList, Static
from textual.widgets.option_list import Option
from textual.worker import get_current_worker

from .config import validate_api_key
from .lumenfall import generate_image, list_models

SLASH_COMMANDS = [("/model", "models"), ("/exit", "exit")]


class ImagineApp(App[None]):
    """Full-screen TUI for image generation."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #content {
        scrollbar-gutter: stable;
        padding: 0 1;
        min-height: 1fr;
    }

    .prompt-bubble {
        padding: 0 1;
        margin: 0;
        border: solid dodgerblue;
        width: auto;
        max-width: 80;
    }

    .status {
        padding: 0 1;
        margin: 0;
        color: dimgray;
    }

    .generating {
        padding: 0 1;
        margin: 0;
        color: dodgerblue;
    }

    .generating LoadingIndicator {
        width: 2;
        height: 1;
    }

    .error {
        padding: 0 1;
        margin: 0;
        color: red;
        border: solid red;
    }

    .image-compact {
        max-height: 16;
    }

    .image-container {
        height: 20;
        width: 100%;
    }

    .image-container > * {
        width: auto;
        height: auto;
    }

    #slash-menu-container {
        display: none;
        padding: 0 2;
        border: solid #333;
        background: $surface;
        max-height: 12;
        height: auto;
    }

    #slash-menu-container.slash-menu-visible {
        display: block;
    }

    #slash-options {
        height: auto;
        max-height: 10;
    }

    #model-picker-container {
        display: none;
        padding: 0 2;
        border: solid #333;
        background: $surface;
        max-height: 16;
        height: auto;
    }

    #model-picker-container.model-picker-visible {
        display: block;
    }

    #model-picker-options {
        height: auto;
        max-height: 14;
    }

    #input-area {
        padding: 1 2;
        border-top: solid #333;
        height: auto;
    }

    Input {
        width: 1fr;
    }

    #statusline {
        padding: 0 2;
        border-top: solid #333;
        height: 3;
        width: 1fr;
    }
    """

    def __init__(self, model: str, size: str, **kwargs):
        super().__init__(**kwargs)
        self.settings = {"model": model, "size": size}
        self._models_cache: list[str] | None = None

    def compose(self) -> ComposeResult:
        yield Vertical(
            ScrollableContainer(id="content"),
            Vertical(
                Vertical(
                    OptionList(id="slash-options", compact=True),
                    id="slash-menu-container",
                ),
                Vertical(
                    OptionList(id="model-picker-options", compact=True),
                    id="model-picker-container",
                ),
                Input(placeholder="Describe an image... or /help for commands", id="prompt-input"),
                id="input-area",
            ),
            Static(
                f"[bold]Imagine[/bold] — model: [dim]{self.settings['model']}[/]  size: [dim]{self.settings['size']}[/]",
                id="statusline",
            ),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()
        content = self.query_one("#content", ScrollableContainer)
        content.mount(Static("Type a prompt and press Enter. Use /help for slash commands.", classes="status"))
        self.run_worker(self._fetch_and_cache_models(), exclusive=False)

    async def _fetch_and_cache_models(self) -> None:
        """Fetch models from API once and cache for model picker."""
        try:
            validate_api_key()
            models = await asyncio.to_thread(list_models)
            self._models_cache = models
        except (SystemExit, Exception):
            pass  # Silently ignore; /model picker will show error when opened

    def _show_slash_menu(self, prefix: str) -> None:
        """Show slash command menu with options filtered by prefix."""
        container = self.query_one("#slash-menu-container", Vertical)
        options = self.query_one("#slash-options", OptionList)
        options.clear_options()
        search = prefix.lstrip("/").lower() if prefix.startswith("/") else prefix.lower()
        filtered = [
            (cmd, label) for cmd, label in SLASH_COMMANDS
            if prefix == "/" or cmd.startswith(prefix) or label.lower().startswith(search)
        ]
        for cmd, label in filtered:
            options.add_option(Option(label, id=cmd))
        if filtered:
            options.highlighted = 0
            container.add_class("slash-menu-visible")
            options.focus()

    def _hide_slash_menu(self, refocus_input: bool = True) -> None:
        """Hide slash command menu; optionally refocus input."""
        container = self.query_one("#slash-menu-container", Vertical)
        container.remove_class("slash-menu-visible")
        if refocus_input:
            self.query_one("#prompt-input", Input).focus()

    @on(Input.Changed)
    def _on_input_changed(self, event: Input.Changed) -> None:
        value = event.value
        # When typing "/", show slash menu (models, exit)
        if value.startswith("/") and not (value.endswith(" ") and len(value) > 1):
            prefix = value.split()[0] if value.split() else "/"
            self._show_slash_menu(prefix)
        else:
            self._hide_slash_menu()
            self._hide_model_picker()

    @on(OptionList.OptionSelected)
    def _on_slash_option_selected(self, event: OptionList.OptionSelected) -> None:
        if getattr(event.control, "id", None) != "slash-options":
            return
        container = self.query_one("#slash-menu-container", Vertical)
        if not container.has_class("slash-menu-visible"):
            return
        cmd = event.option.id or str(event.option.prompt)
        self._hide_slash_menu()
        if cmd == "/model":
            self._hide_slash_menu(refocus_input=False)
            self._show_model_picker()
        elif cmd == "/exit":
            self.exit()
        else:
            inp = self.query_one("#prompt-input", Input)
            inp.value = f"{cmd} "
            inp.focus()

    @on(OptionList.OptionSelected)
    def _on_model_option_selected(self, event: OptionList.OptionSelected) -> None:
        if getattr(event.control, "id", None) != "model-picker-options":
            return
        model_id = event.option.id or str(event.option.prompt)
        self.settings["model"] = model_id
        self._hide_model_picker()
        self.query_one("#prompt-input", Input).value = ""
        self._add_status(f"Model set to: {model_id}", classes="status")
        self._update_statusline()

    def _show_model_picker(self) -> None:
        """Show model submenu: list of models, pick with arrow keys + Enter."""
        container = self.query_one("#model-picker-container", Vertical)
        options = self.query_one("#model-picker-options", OptionList)
        options.clear_options()
        if self._models_cache:
            for m in self._models_cache:
                options.add_option(Option(m, id=m))
            options.highlighted = 0
            container.add_class("model-picker-visible")
            options.focus()
        else:
            self.run_worker(self._fetch_models_for_picker(), exclusive=True)

    async def _fetch_models_for_picker(self) -> None:
        """Fetch models and then show picker (used when cache miss)."""
        try:
            validate_api_key()
            models = await asyncio.to_thread(list_models)
            self._models_cache = models
            options = self.query_one("#model-picker-options", OptionList)
            options.clear_options()
            for m in models:
                options.add_option(Option(m, id=m))
            options.highlighted = 0
            container = self.query_one("#model-picker-container", Vertical)
            container.add_class("model-picker-visible")
            options.focus()
        except SystemExit:
            self._add_status("Set LUMENFALL_API_KEY to list models.", classes="error")
        except Exception as e:
            self._add_status(str(e), classes="error")

    def _hide_model_picker(self) -> None:
        """Hide model picker and refocus input."""
        container = self.query_one("#model-picker-container", Vertical)
        container.remove_class("model-picker-visible")
        self.query_one("#prompt-input", Input).focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            model_picker = self.query_one("#model-picker-container", Vertical)
            if model_picker.has_class("model-picker-visible"):
                self._hide_model_picker()
                event.prevent_default()
                event.stop()
                return
            container = self.query_one("#slash-menu-container", Vertical)
            if container.has_class("slash-menu-visible"):
                self._hide_slash_menu()
                event.prevent_default()
                event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if not value:
            return
        event.input.value = ""
        self._handle_input(value)

    def _handle_input(self, text: str) -> None:
        if text.startswith("/"):
            self._handle_slash(text)
            return
        if text.lower() in ("exit", "quit", "q"):
            self.exit()
            return
        self._add_prompt(text)
        self.run_worker(self._generate_and_show(text), exclusive=True)

    def _scroll_to_bottom(self) -> None:
        content = self.query_one("#content", ScrollableContainer)
        self.call_after_refresh(content.scroll_end, animate=False)

    def _add_prompt(self, text: str) -> None:
        content = self.query_one("#content", ScrollableContainer)
        content.mount(Static(f"  {text}", classes="prompt-bubble"))
        self._scroll_to_bottom()

    def _add_status(self, msg: str, classes: str = "status", temp: bool = False) -> None:
        content = self.query_one("#content", ScrollableContainer)
        wid = Static(msg, classes=classes, id="temp-status" if temp else None)
        if temp:
            for old in content.query("#temp-status"):
                old.remove()
        content.mount(wid)
        self._scroll_to_bottom()

    def _remove_temp_status(self) -> None:
        content = self.query_one("#content", ScrollableContainer)
        for w in content.query("#temp-status"):
            w.remove()

    def _add_image(self, image_bytes: bytes) -> None:
        content = self.query_one("#content", ScrollableContainer)
        try:
            pil_image = PILImage.open(io.BytesIO(image_bytes))
            img_widget = TextualImage(pil_image, classes="image-compact")
            wrapper = Vertical(img_widget, classes="image-container")
            content.mount(wrapper)
            self._scroll_to_bottom()
        except Exception as e:
            self._add_status(f"Could not display image: {e}", classes="error")

    def _add_generating(self) -> None:
        """Show 'Generating' with animated spinner."""
        content = self.query_one("#content", ScrollableContainer)
        for old in content.query("#temp-status"):
            old.remove()
        gen = Horizontal(
            LoadingIndicator(),
            Static("Generating..."),
            classes="generating",
            id="temp-status",
        )
        content.mount(gen)
        self._scroll_to_bottom()

    async def _generate_and_show(self, prompt: str) -> None:
        worker = get_current_worker()
        self._add_generating()
        try:
            validate_api_key()
            image_bytes = await asyncio.to_thread(
                generate_image,
                prompt=prompt,
                model=self.settings["model"],
                size=self.settings["size"],
            )
            if worker.is_cancelled:
                return
            self._remove_temp_status()
            save_path = Path.cwd() / f"imagine_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
            save_path.write_bytes(image_bytes)
            self._add_image(image_bytes)
            self._add_status(f"Saved to {save_path.name}", classes="status")
            self._scroll_to_bottom()
        except SystemExit:
            self._remove_temp_status()
            self._add_status("Set LUMENFALL_API_KEY to generate images.", classes="error")
        except Exception as e:
            self._remove_temp_status()
            self._add_status(str(e), classes="error")

    async def _fetch_models(self) -> None:
        try:
            validate_api_key()
            models = await asyncio.to_thread(list_models)
            for m in models[:20]:
                self._add_status(f"  {m}", classes="status")
            if len(models) > 20:
                self._add_status(f"  ... and {len(models) - 20} more", classes="status")
        except SystemExit:
            self._add_status("Set LUMENFALL_API_KEY to list models.", classes="error")
        except Exception as e:
            self._add_status(str(e), classes="error")

    def _handle_slash(self, text: str) -> None:
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/help":
            self._add_status("  /model [name] — pick or set model  /size [dims]  /models  /settings  /help  /exit", classes="status")
        elif cmd == "/model":
            if arg:
                self.settings["model"] = arg
                self._add_status(f"Model set to: {arg}", classes="status")
                self._update_statusline()
            else:
                self._show_model_picker()
        elif cmd == "/size":
            if arg:
                self.settings["size"] = arg
                self._add_status(f"Size set to: {arg}", classes="status")
                self._update_statusline()
            else:
                self._add_status(f"Current size: {self.settings['size']}", classes="status")
        elif cmd == "/settings":
            self._add_status(f"Model: {self.settings['model']}  Size: {self.settings['size']}", classes="status")
        elif cmd == "/models":
            self.run_worker(self._fetch_models(), exclusive=True)
        elif cmd == "/exit":
            self.exit()
        else:
            self._add_status(f"Unknown: {cmd}. Use /help", classes="error")

        self._update_statusline()

    def _update_statusline(self) -> None:
        self.query_one("#statusline", Static).update(
            f"[bold]Imagine[/bold] — model: [dim]{self.settings['model']}[/]  size: [dim]{self.settings['size']}[/]"
        )


def run_tui(model: str, size: str) -> None:
    """Launch the Textual TUI."""
    app = ImagineApp(model=model, size=size)
    app.run()
