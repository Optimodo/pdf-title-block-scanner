from pathlib import Path

from drawing_qa.cli import main
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
        ]
    )
    assert code == 0
    assert (debug / "ABC-WXY-ZZ-00-DR-A-0001-P01_bottom_right.png").is_file()
    assert (debug / "ABC-WXY-ZZ-00-DR-A-0001-P01_bottom_strip.png").is_file()
