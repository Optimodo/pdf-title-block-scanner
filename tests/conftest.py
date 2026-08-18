from pathlib import Path

import pytest

from drawing_qa.paths import bundled_config_dir


@pytest.fixture
def config_dir() -> Path:
    return bundled_config_dir()
