"""Tests for display module."""

import os

import pytest

from imagine.display import detect_terminal


def test_detect_terminal_iterm2(monkeypatch):
    monkeypatch.setenv("TERM_PROGRAM", "iTerm.app")
    assert detect_terminal() == "iterm2"


def test_detect_terminal_wezterm(monkeypatch):
    monkeypatch.setenv("TERM_PROGRAM", "WezTerm")
    assert detect_terminal() == "iterm2"


def test_detect_terminal_kitty(monkeypatch):
    monkeypatch.setenv("TERM_PROGRAM", "kitty")
    monkeypatch.delenv("WT_SESSION", raising=False)
    assert detect_terminal() == "kitty"


def test_detect_terminal_ghostty(monkeypatch):
    monkeypatch.setenv("TERM_PROGRAM", "Ghostty")
    monkeypatch.delenv("WT_SESSION", raising=False)
    assert detect_terminal() == "kitty"


def test_detect_terminal_ghostty_term(monkeypatch):
    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    monkeypatch.setenv("TERM", "xterm-ghostty")
    assert detect_terminal() == "kitty"


def test_detect_terminal_windows(monkeypatch):
    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    monkeypatch.setenv("WT_SESSION", "abc123")
    assert detect_terminal() == "sixel"


def test_detect_terminal_fallback(monkeypatch):
    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    monkeypatch.delenv("WT_SESSION", raising=False)
    monkeypatch.setenv("TERM", "xterm")
    assert detect_terminal() == "fallback"
