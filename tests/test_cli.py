from pathlib import Path

from drawing_qa.cli import main
from drawing_qa.paths import REPORT_NAME
from tests.pdf_fixtures import write_bottom_right_pdf


def test_cli_check_writes_report(tmp_path: Path, config_dir: Path):
    drawings = tmp_path / "drawings"
    write_bottom_right_pdf(
        drawings / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
    )
    output = tmp_path / "out.xlsx"
    code = main(
        [
            "check",
            str(drawings),
            "--config-dir",
            str(config_dir),
            "--output",
            str(output),
            "--no-pause",
        ]
    )
    assert code == 0
    assert output.is_file()


def test_cli_inspect_writes_crops(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
    )
    debug = tmp_path / "debug"
    code = main(
        [
            "inspect",
            str(pdf),
            "--config-dir",
            str(config_dir),
            "--debug-dir",
            str(debug),
            "--no-pause",
        ]
    )
    assert code == 0
    assert (debug / "ABC-WXY-ZZ-00-DR-A-0001-P01_bottom_right.png").is_file()
    assert (debug / "ABC-WXY-ZZ-00-DR-A-0001-P01_bottom_strip.png").is_file()


def test_auto_check_uses_program_folder(tmp_path: Path, monkeypatch):
    write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
    )
    monkeypatch.setattr("drawing_qa.cli.app_dir", lambda: tmp_path)
    code = main(["--no-pause"])
    assert code == 0
    assert (tmp_path / REPORT_NAME).is_file()


def test_auto_check_versions_existing_report(tmp_path: Path, monkeypatch):
    write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
    )
    (tmp_path / REPORT_NAME).write_bytes(b"old")
    monkeypatch.setattr("drawing_qa.cli.app_dir", lambda: tmp_path)
    code = main(["--no-pause"])
    assert code == 0
    assert (tmp_path / "TBCheckReport-1.xlsx").is_file()
    assert (tmp_path / REPORT_NAME).read_bytes() == b"old"
