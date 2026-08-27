from pathlib import Path

from drawing_qa.paths import (
    REPORT_NAME,
    designer_report_path,
    document_control_report_path,
    is_versioned_report_name,
    next_available_paired_report_path,
    next_available_report_path,
    resolve_config_dir,
    sanitize_filename_part,
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


def test_sanitize_filename_part_strips_illegal_chars():
    assert sanitize_filename_part('Oval C+D') == "Oval C+D"
    assert sanitize_filename_part('R459: Oval*C+D') == "R459 Oval C+D"
    assert sanitize_filename_part("   ") == "Drawings"


def test_paired_report_skips_existing_designer_sidecar(tmp_path: Path):
    (tmp_path / "Oval C+D_260826.xlsx").write_bytes(b"main")
    first = next_available_paired_report_path(tmp_path, "Oval C+D_260826")
    assert first.name == "Oval C+D_260826-1.xlsx"
    designer_report_path(tmp_path / "Free_260826.xlsx").write_bytes(b"side")
    second = next_available_paired_report_path(tmp_path, "Free_260826")
    assert second.name == "Free_260826-1.xlsx"


def test_paired_report_skips_existing_document_control_sidecar(tmp_path: Path):
    document_control_report_path(tmp_path / "Oval C+D_260826.xlsx").write_bytes(b"side")
    first = next_available_paired_report_path(tmp_path, "Oval C+D_260826")
    assert first.name == "Oval C+D_260826-1.xlsx"


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
