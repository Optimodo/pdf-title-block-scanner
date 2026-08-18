from pathlib import Path

import pytest

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


@pytest.fixture
def config_dir() -> Path:
    return CONFIG_DIR
