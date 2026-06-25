"""Test MODEL bisa di-override via env RUKA_MODEL (fallback default).

Headless: importlib.reload(config) agar os.getenv dievaluasi ulang dengan env
yang dimonkeypatch. Autouse fixture mengembalikan config ke default sesudah tiap
test agar tak bocor ke file test lain.
"""
import importlib
import os

import pytest

import config

DEFAULT = "openrouter/owl-alpha"


@pytest.fixture(autouse=True)
def _restore_config():
    yield
    os.environ.pop("RUKA_MODEL", None)
    importlib.reload(config)


def test_default_when_unset(monkeypatch):
    monkeypatch.delenv("RUKA_MODEL", raising=False)
    importlib.reload(config)
    assert config.MODEL == DEFAULT == config._DEFAULT_MODEL


def test_override_applied(monkeypatch):
    monkeypatch.setenv("RUKA_MODEL", "openrouter/qwen/qwen3-8b")
    importlib.reload(config)
    assert config.MODEL == "openrouter/qwen/qwen3-8b"


def test_empty_falls_back(monkeypatch):
    monkeypatch.setenv("RUKA_MODEL", "")
    importlib.reload(config)
    assert config.MODEL == config._DEFAULT_MODEL


def test_whitespace_falls_back(monkeypatch):
    monkeypatch.setenv("RUKA_MODEL", "   ")
    importlib.reload(config)
    assert config.MODEL == config._DEFAULT_MODEL


def test_value_is_stripped(monkeypatch):
    monkeypatch.setenv("RUKA_MODEL", "  openrouter/foo-bar  ")
    importlib.reload(config)
    assert config.MODEL == "openrouter/foo-bar"
