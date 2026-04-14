"""Tests for .infracanvas.yml config loading."""

from pathlib import Path

from infracanvas.config import InfraCanvasConfig, load_config


class TestLoadConfig:
    def test_default_config(self, tmp_path):
        config = load_config(tmp_path)
        assert config.severity_threshold == "high"
        assert config.ignore_rules == []
        assert config.open_browser is True

    def test_load_from_directory(self, tmp_path):
        (tmp_path / ".infracanvas.yml").write_text(
            "severity_threshold: medium\nignore_rules:\n  - SEC-010\nopen_browser: false\n"
        )
        config = load_config(tmp_path)
        assert config.severity_threshold == "medium"
        assert config.ignore_rules == ["SEC-010"]
        assert config.open_browser is False

    def test_load_from_parent_directory(self, tmp_path):
        (tmp_path / ".infracanvas.yml").write_text("severity_threshold: info\n")
        subdir = tmp_path / "modules" / "vpc"
        subdir.mkdir(parents=True)
        config = load_config(subdir)
        assert config.severity_threshold == "info"

    def test_invalid_yaml_returns_default(self, tmp_path):
        (tmp_path / ".infracanvas.yml").write_text(":::invalid yaml{{")
        config = load_config(tmp_path)
        assert config == InfraCanvasConfig()

    def test_empty_file_returns_default(self, tmp_path):
        (tmp_path / ".infracanvas.yml").write_text("")
        config = load_config(tmp_path)
        assert config == InfraCanvasConfig()
