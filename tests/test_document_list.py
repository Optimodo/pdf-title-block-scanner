from pathlib import Path

from openpyxl import Workbook

from drawing_qa.checker import check_paths
from drawing_qa.config_loader import load_config
from drawing_qa.document_list import (
    DocumentListIndex,
    PortalDocument,
    check_document_list,
    find_document_list,
    load_document_list,
)
from drawing_qa.models import (
    CheckStatus,
    DocumentResult,
    FilenameFields,
    TitleBlockFields,
    finalize_status,
)
from drawing_qa.paths import bundled_config_dir
from drawing_qa.tokens import is_allowed_first_revision, is_successor_revision, next_revision
from tests.pdf_fixtures import write_bottom_right_pdf


def _layout():
    return load_config(bundled_config_dir()).document_list.layout


def _write_excel(
    path: Path,
    rows: list[tuple[str, str, str]],
    *,
    headers: list[str] | None = None,
    header_row: int = 1,
) -> Path:
    wb = Workbook()
    ws = wb.active
    for _ in range(header_row - 1):
        ws.append(["ignore"] * 3)
    ws.append(headers or ["Original Doc Ref (Non-Standard)", "Description", "Revision"])
    for row in rows:
        ws.append(list(row))
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def _drawing(
    *,
    project: str = "ABC",
    number: str = "0001",
    revision: str = "P01",
    title: str = "Ground Floor GA",
    doc_ref: str | None = None,
    suitability: str | None = None,
) -> DocumentResult:
    ref = doc_ref or f"{project}-WXY-ZZ-00-DR-A-{number}"
    return DocumentResult(
        path=Path(f"{ref}-{revision}.pdf"),
        filename=FilenameFields(
            raw_stem=f"{ref}-{revision}",
            document_reference=ref,
            title=title,
            revision=revision,
            parse_ok=True,
            parts={"project": project},
        ),
        titleblock=TitleBlockFields(
            document_reference=ref,
            title=title,
            revision=revision,
            suitability=suitability,
        ),
        status=CheckStatus.MATCH,
    )
    ref = doc_ref or f"{project}-WXY-ZZ-00-DR-A-{number}"
    return DocumentResult(
        path=Path(f"{ref}-{revision}.pdf"),
        filename=FilenameFields(
            raw_stem=f"{ref}-{revision}",
            document_reference=ref,
            title=title,
            revision=revision,
            parse_ok=True,
            parts={"project": project},
        ),
        titleblock=TitleBlockFields(
            document_reference=ref,
            title=title,
            revision=revision,
        ),
        status=CheckStatus.MATCH,
    )


def test_successor_revision_rules():
    assert is_successor_revision("P01", "P02")
    assert is_successor_revision("P01", "C01")
    assert is_successor_revision("P09", "C01")
    assert not is_successor_revision("P01", "P01")
    assert not is_successor_revision("P01", "P03")
    assert not is_successor_revision("P01", "C02")
    assert not is_successor_revision("C01", "P02")
    assert next_revision("P01") == "P02"
    assert is_allowed_first_revision("C01", ["P01", "C01"])
    assert not is_allowed_first_revision("P02", ["P01", "C01"])


def test_load_4projects_headers(tmp_path: Path):
    path = _write_excel(
        tmp_path / "OVCD Document Listing.xlsx",
        [("R459-MBS-DZ-ZZ-DR-W-0001", "Plant", "P01")],
    )
    index = load_document_list(path, _layout())
    row = index.get("R459-MBS-DZ-ZZ-DR-W-0001")
    assert row is not None
    assert row.revision == "P01"
    assert row.title == "Plant"


def test_load_asite_headers_on_row_six(tmp_path: Path):
    path = _write_excel(
        tmp_path / "Asite export.xlsx",
        [("J106309-MBS-ZZ-00-DR-M-0001", "Basement", "P03")],
        headers=["Doc Ref", "Doc Title", "Rev"],
        header_row=6,
    )
    index = load_document_list(path, _layout())
    row = index.get("J106309-MBS-ZZ-00-DR-M-0001")
    assert row is not None
    assert row.revision == "P03"
    assert row.title == "Basement"


def test_load_dochosting_csv(tmp_path: Path):
    path = tmp_path / "HPA dump.csv"
    path.write_text(
        "Title,Subject,Rev\nHPA-MBS-ZZ-00-DR-E-0001,Lighting,P01\n",
        encoding="utf-8",
    )
    index = load_document_list(path, _layout())
    row = index.get("HPA-MBS-ZZ-00-DR-E-0001")
    assert row is not None
    assert row.revision == "P01"
    assert row.title == "Lighting"


def test_keeps_highest_portal_revision(tmp_path: Path):
    path = _write_excel(
        tmp_path / "Listing.xlsx",
        [
            ("ABC-WXY-ZZ-00-DR-A-0001", "Ground Floor GA", "P01"),
            ("ABC-WXY-ZZ-00-DR-A-0001", "Ground Floor GA", "P02"),
        ],
    )
    index = load_document_list(path, _layout())
    assert index.get("ABC-WXY-ZZ-00-DR-A-0001").revision == "P02"


def test_skips_irs_and_tbcheck_report_names(tmp_path: Path):
    layout = _layout()
    irs = _write_excel(
        tmp_path / "OVCD IRS.xlsx",
        [("ABC-WXY-ZZ-00-DR-A-0001", "Ground Floor GA", "P01")],
    )
    report = _write_excel(
        tmp_path / "ABC_260826.xlsx",
        [("ABC-WXY-ZZ-00-DR-A-0001", "Ground Floor GA", "P01")],
    )
    listing = _write_excel(
        tmp_path / "Document Listing.xlsx",
        [("ABC-WXY-ZZ-00-DR-A-0001", "Ground Floor GA", "P02")],
    )
    assert find_document_list(tmp_path, layout) == listing
    assert find_document_list(tmp_path, layout, explicit=irs) == irs
    only_irs = tmp_path / "irs_only"
    only_irs.mkdir()
    _write_excel(
        only_irs / "Project IRS.xlsx",
        [("ABC-WXY-ZZ-00-DR-A-0001", "Ground Floor GA", "P01")],
    )
    assert find_document_list(only_irs, layout) is None


def test_portal_successor_and_same_revision():
    layout = _layout()
    index = DocumentListIndex(
        path=Path("Document Listing.xlsx"),
        by_ref={
            "ABC-WXY-ZZ-00-DR-A-0001": PortalDocument(
                "ABC-WXY-ZZ-00-DR-A-0001", "P01", "Ground Floor GA"
            )
        },
    )
    ok = check_document_list([_drawing(revision="P02")], index, layout)[0]
    finalize_status(ok)
    assert CheckStatus.PORTAL_REVISION not in ok.issues

    same = check_document_list([_drawing(revision="P01")], index, layout)[0]
    finalize_status(same)
    assert CheckStatus.PORTAL_REVISION in same.issues

    skip = check_document_list([_drawing(revision="P03")], index, layout)[0]
    finalize_status(skip)
    assert CheckStatus.PORTAL_REVISION in skip.issues

    construction = check_document_list([_drawing(revision="C01")], index, layout)[0]
    finalize_status(construction)
    assert CheckStatus.PORTAL_REVISION not in construction.issues


def test_wcr_allows_c01_when_not_on_portal():
    layout = _layout()
    index = DocumentListIndex(path=Path("WCR Listing.xlsx"), by_ref={})
    first = check_document_list(
        [_drawing(project="WCR", revision="C01")], index, layout
    )[0]
    finalize_status(first)
    assert CheckStatus.PORTAL_REVISION not in first.issues

    too_far = check_document_list(
        [_drawing(project="WCR", revision="P02")], index, layout
    )[0]
    finalize_status(too_far)
    assert CheckStatus.PORTAL_REVISION in too_far.issues


def test_new_drawing_must_be_p01_except_wcr():
    layout = _layout()
    index = DocumentListIndex(path=Path("Listing.xlsx"), by_ref={})
    ok = check_document_list([_drawing(revision="P01")], index, layout)[0]
    finalize_status(ok)
    assert CheckStatus.PORTAL_REVISION not in ok.issues

    bad = check_document_list([_drawing(revision="C01")], index, layout)[0]
    finalize_status(bad)
    assert CheckStatus.PORTAL_REVISION in bad.issues


def test_portal_title_mismatch():
    layout = _layout()
    index = DocumentListIndex(
        path=Path("Listing.xlsx"),
        by_ref={
            "ABC-WXY-ZZ-00-DR-A-0001": PortalDocument(
                "ABC-WXY-ZZ-00-DR-A-0001", "P01", "Ground Floor GA"
            )
        },
    )
    result = check_document_list(
        [_drawing(revision="P02", title="Roof Plan")], index, layout
    )[0]
    finalize_status(result)
    assert CheckStatus.PORTAL_TITLE in result.issues


def test_check_paths_uses_folder_listing(tmp_path: Path, config_dir: Path):
    write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
    )
    _write_excel(
        tmp_path / "Document Listing.xlsx",
        [("ABC-WXY-ZZ-00-DR-A-0001", "Ground Floor GA", "P01")],
    )
    results = check_paths(
        list(tmp_path.glob("*.pdf")),
        load_config(config_dir),
    )
    assert results[0].portal_list_name == "Document Listing.xlsx"
    assert CheckStatus.PORTAL_REVISION in results[0].issues


def test_check_paths_skips_when_no_listing(tmp_path: Path, config_dir: Path):
    write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
    )
    results = check_paths(
        list(tmp_path.glob("*.pdf")),
        load_config(config_dir),
    )
    assert results[0].portal_list_name == ""
    assert CheckStatus.PORTAL_REVISION not in results[0].issues
    assert results[0].status == CheckStatus.MATCH


def test_status_allows_upload_uses_project_wordings():
    from drawing_qa.document_list import status_allows_upload

    layout = _layout()
    assert status_allows_upload("A Proceed", layout, "R459")
    assert status_allows_upload("Status A", layout, "R459")
    assert status_allows_upload("C", layout, "WCR")
    assert status_allows_upload("EA+DM - Status B", layout, "WCR")
    assert status_allows_upload("Construction", layout, "HPA")
    assert not status_allows_upload("Construction", layout, "R459")
    assert status_allows_upload("QA Approved", layout, "R459")
    assert not status_allows_upload("Pending QA Check", layout, "R459")
    assert not status_allows_upload("QA Rejected", layout, "R459")
    assert not status_allows_upload("", layout, "R459")


def test_prefers_revision_workflow_over_purpose_status_column(tmp_path: Path):
    path = _write_excel(
        tmp_path / "OVCD Document Listing.xlsx",
        [
            (
                "R459-MBS-DZ-ZZ-DR-W-0001",
                "Plant",
                "P01",
                "S3 - For Review & Comment",
                "Pending QA Check",
            )
        ],
        headers=[
            "Original Doc Ref (Non-Standard)",
            "Description",
            "Revision",
            "Status",
            "Revision Workflow",
        ],
    )
    index = load_document_list(path, _layout())
    assert index.has_status
    row = index.get("R459-MBS-DZ-ZZ-DR-W-0001")
    assert row is not None
    assert row.status == "Pending QA Check"


def test_blocks_upload_when_portal_status_is_not_abc():
    layout = _layout()
    index = DocumentListIndex(
        path=Path("Document Listing.xlsx"),
        has_status=True,
        by_ref={
            "ABC-WXY-ZZ-00-DR-A-0001": PortalDocument(
                "ABC-WXY-ZZ-00-DR-A-0001",
                "P01",
                "Ground Floor GA",
                "Pending QA Check",
            )
        },
    )
    blocked = check_document_list([_drawing(revision="P02")], index, layout)[0]
    assert blocked.portal_blocks_upload
    assert blocked.portal_status == "Pending QA Check"

    index.by_ref["ABC-WXY-ZZ-00-DR-A-0001"].status = "A Proceed"
    ok = check_document_list([_drawing(revision="P02")], index, layout)[0]
    assert not ok.portal_blocks_upload

    index.by_ref["ABC-WXY-ZZ-00-DR-A-0001"].status = "QA Approved"
    qa_ok = check_document_list([_drawing(revision="P02")], index, layout)[0]
    assert not qa_ok.portal_blocks_upload


def test_new_portal_drawing_is_not_an_upload_block():
    layout = _layout()
    index = DocumentListIndex(path=Path("Listing.xlsx"), has_status=True, by_ref={})
    result = check_document_list([_drawing(revision="P01")], index, layout)[0]
    assert not result.portal_blocks_upload


def test_intended_upload_revision_ignores_skipped_drawing_rev():
    from drawing_qa.document_list import intended_upload_revision

    assert intended_upload_revision("C01", "C02") == "C02"
    assert intended_upload_revision("C01", "C03") == "C02"
    assert intended_upload_revision("C01", "C01") == "C02"
    assert intended_upload_revision("P01", "C01") == "C01"
    assert intended_upload_revision("P01", "P02") == "P02"
    assert intended_upload_revision("P01", "P01") == "P02"


def test_check_sets_proposed_upload_to_next_portal_issue():
    layout = _layout()
    index = DocumentListIndex(
        path=Path("Document Listing.xlsx"),
        has_status=True,
        by_ref={
            "ABC-WXY-ZZ-00-DR-A-0001": PortalDocument(
                "ABC-WXY-ZZ-00-DR-A-0001",
                "C01",
                "Ground Floor GA",
                "Pending QA Check",
            )
        },
    )
    result = check_document_list([_drawing(revision="C03")], index, layout)[0]
    assert result.proposed_upload_revision == "C02"
    assert result.portal_blocks_upload


def test_r459_approved_p_must_go_to_c01_construction():
    layout = _layout()
    index = DocumentListIndex(
        path=Path("OVCD Document Listing.xlsx"),
        has_status=True,
        by_ref={
            "R459-WXY-ZZ-00-DR-A-0001": PortalDocument(
                "R459-WXY-ZZ-00-DR-A-0001",
                "P04",
                "Ground Floor GA",
                "A Proceed",
            )
        },
    )
    still_p = check_document_list(
        [_drawing(project="R459", revision="P05")], index, layout
    )[0]
    finalize_status(still_p)
    assert still_p.construction_upgrade_required
    assert still_p.proposed_upload_revision == "C01"
    assert CheckStatus.PORTAL_REVISION in still_p.issues
    assert CheckStatus.PURPOSE_MISMATCH not in still_p.issues

    ok = check_document_list(
        [_drawing(project="R459", revision="C01")],
        index,
        layout,
    )[0]
    finalize_status(ok)
    assert ok.proposed_upload_revision == "C01"
    assert CheckStatus.PORTAL_REVISION not in ok.issues

    # Purpose of issue is not pinned to one whitelist string here.
    review_purpose = check_document_list(
        [
            _drawing(
                project="R459",
                revision="C01",
                suitability="S3 - For Review & Comment",
            )
        ],
        index,
        layout,
    )[0]
    finalize_status(review_purpose)
    assert CheckStatus.PORTAL_REVISION not in review_purpose.issues
    assert CheckStatus.PURPOSE_MISMATCH not in review_purpose.issues


def test_r459_rejected_p_can_still_go_to_p_next():
    layout = _layout()
    index = DocumentListIndex(
        path=Path("OVCD Document Listing.xlsx"),
        has_status=True,
        by_ref={
            "R459-WXY-ZZ-00-DR-A-0001": PortalDocument(
                "R459-WXY-ZZ-00-DR-A-0001",
                "P04",
                "Ground Floor GA",
                "C Rejected",
            )
        },
    )
    result = check_document_list(
        [_drawing(project="R459", revision="P05")], index, layout
    )[0]
    finalize_status(result)
    assert not result.construction_upgrade_required
    assert result.proposed_upload_revision == "P05"
    assert CheckStatus.PORTAL_REVISION not in result.issues


def test_construction_upgrade_is_off_for_other_projects():
    layout = _layout()
    index = DocumentListIndex(
        path=Path("Listing.xlsx"),
        has_status=True,
        by_ref={
            "ABC-WXY-ZZ-00-DR-A-0001": PortalDocument(
                "ABC-WXY-ZZ-00-DR-A-0001",
                "P01",
                "Ground Floor GA",
                "A Proceed",
            )
        },
    )
    result = check_document_list([_drawing(revision="P02")], index, layout)[0]
    finalize_status(result)
    assert not result.construction_upgrade_required
    assert CheckStatus.PORTAL_REVISION not in result.issues


def test_intended_upload_revision_can_require_c01():
    from drawing_qa.document_list import intended_upload_revision

    assert intended_upload_revision("P04", "P05", require_revision="C01") == "C01"
