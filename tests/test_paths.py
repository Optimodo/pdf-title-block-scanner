from pathlib import Path

from drawing_qa.paths import (
    REPORT_NAME,
    is_versioned_report_name,
    next_available_report_path,
    resolve_config_dir,
)


def test_next_available_report_uses_suffix(tmp_path: Path):
    first = next_available_report_path(tmp_path)
    assert first.name == REPORT_NAME
    first.write_bytes(b"one")
    second = next_available_report_path(tmp_path)
    assert second.name == "TBCheckReport-1.xlsx"
    second.write_bytes(b"two")
    third = next_available_report_path(tmp_path)
    assert third.name == "TBCheckReport-2.xlsx"


def test_versioned_report_names():
    assert is_versioned_report_name("TBCheckReport.xlsx")
    assert is_versioned_report_name("TBCheckReport-12.xlsx")
    assert not is_versioned_report_name("other.xlsx")


def test_sidecar_config_wins(tmp_path: Path, config_dir: Path):
    sidecar = tmp_path / "config"
    sidecar.mkdir()
    (sidecar / "settings.yaml").write_text(
        (config_dir / "settings.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert resolve_config_dir(tmp_path) == sidecar


def test_bundled_config_when_no_sidecar(tmp_path: Path, config_dir: Path):
    assert resolve_config_dir(tmp_path) == config_dir
