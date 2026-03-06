"""Tests for config module."""

import os

import pytest

from imagine.config import get_api_key, load_config


def test_get_api_key_from_lumenfall_env(monkeypatch):
    monkeypatch.setenv("LUMENFALL_API_KEY", "lmnfl_test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_api_key() == "lmnfl_test"


def test_get_api_key_fallback_to_openai(monkeypatch):
    monkeypatch.delenv("LUMENFALL_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk_test")
    assert get_api_key() == "sk_test"


def test_get_api_key_empty(monkeypatch):
    monkeypatch.delenv("LUMENFALL_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_api_key() is None


def test_load_config_defaults():
    config = load_config()
    assert "model" in config
    assert "size" in config
    assert config["model"] == "gemini-3-pro-image"
    assert config["size"] == "1024x1024"
