================================================================================
  MBS FILE TOOLS (Windows programs)
================================================================================

If you found this note next to some small programs (FName, FList, FNamePro,
FUndo, QA-TB-Checker, QA-TB-File-Renamer, QA-TB-Custom-Checker,
QA-TB-Comments-Organiser), here is
what they are for, in plain language.

These tools are for people who work with engineering drawing files (for example
PDF or CAD files) that use our standard document reference in the file name.
They only look at the folder they are saved in. They do not send your files
anywhere over the internet.

The "document reference" is the coded part at the start of a file name. It is
made of several short pieces separated by dashes, then the file extension.
For example, a drawing might end up named like this:

  R459-MBS-CZ-ZZ-DR-W-51457.pdf

Real names are often longer because people add a title or revision after the
reference (for example " ... - BLOCK C VENTILATION LAYOUT.pdf"). These tools
help pull out or standardise the reference part so names match our filing rules.

--------------------------------------------------------------------------------
  WHAT EACH PROGRAM DOES
--------------------------------------------------------------------------------

  FName
    Tidies file names in this folder so they follow the standard document
    reference style. It writes a short text report (FNameReport.txt) so you
    can see what it did.

  FList
    Does not rename anything. It writes a text list (filelist.txt) describing
    the files in this folder in a way that is easy to copy into a spreadsheet
    or email.

  FNamePro
    Like FList, but it also renames files to the standard document reference
    where it can. It writes a text report (report.txt) with more detail.

  FUndo
    Tries to put file names back how they were before FName or FNamePro was
    run. It reads the text reports those programs left in the same folder
    (including older copies named with -1, -2, and so on). You normally do
    not need it unless something went wrong or you change your mind.

  QA-TB-Checker
    Looks inside each PDF drawing at the title block (the stamp with the
    drawing number, title, revision, and so on) and compares that with the
    file name. It also checks things like spelling and the revision history.
    It writes an Excel report. If drawings need CAD changes, it also writes
    a short designer workbook for email and a plain text list you can copy
    into a CDE comment (drawing number, title, and what to change; one
    drawing at a time, with a blank line between them). If the number on
    the file does not match the title block, it will ask if you want the
    file renamed (the rest of the name is kept). Paired CAD files are
    renamed too if you say yes. If you have put a portal document list in
    the folder, the report also checks against that (see below).

  QA-TB-File-Renamer
    Does the same checks as QA-TB-Checker, then automatically renames every
    PDF it can read to: drawing number, then title, then revision, taken
    from the title block. It does not ask first. Use this when you want
    names to match what is printed on the drawing.

  QA-TB-Custom-Checker
    Same as QA-TB-Checker, but you can turn some of the checks off.
    Double-click it and you will see a numbered list. Type a number (or a
    few) to switch a check off, then press Enter to run. The last item
    turns on field-crop pictures of every drawing in the Excel report (off
    by default, because it makes the report slower). This is useful when you
    are in the middle of renaming and you do not want the portal checks
    filling the report yet.

  QA-TB-Comments-Organiser
    Use this on a folder of marked-up drawings that have mixed revisions
    dumped together (for example P02 with P03, or C02 with C04). It reads
    the revision from the title block — the same layouts as QA-TB-Checker —
    and copies each PDF into Sorted\C01, Sorted\C02, and so on. The original
    files stay in the dump folder. If the revision cannot be read, the copy
    goes to Sorted\Unsorted so you can file it by hand. It writes a short
    Excel transmittal (Comments_Organiser_ddmmyy.xlsx) that you can issue
    with a share: how many comments files sit in each revision folder, then
    a list sorted by revision with document reference, title, revision, and
    whether the comments file is there. Title-block templates are omitted.

These QA-TB programs need PDF drawings with selectable text (normal CAD
exports). They do not read scanned paper drawings. Put the program in the
folder with the PDFs, the same way as FName. The file name includes a
version (for example QA-TB-Checker-v1.0.exe). If you are given a newer
copy, the number will be higher, so you can see which one is current.

You can also drag one or more files onto QA-TB-Checker, QA-TB-File-Renamer,
or QA-TB-Custom-Checker. Only those drawings are checked, not the whole
folder. You can include PDFs, CAD files (DWG), and a portal document-list
spreadsheet together. CAD files are not checked on their own; they are
matched to the PDFs. If you do not include a portal list, QA-TB-Checker
still looks for one in the drawings folder. Drag a whole folder onto
QA-TB-Checker (for example a date folder with B1, B2, B3 inside) to check
every PDF in every subfolder. Each subfolder that has PDFs gets its own
Excel report. A master report covering all of them is written in the
folder you dropped. Double-clicking the program still only checks PDFs
sitting next to it, not subfolders. Drag PDFs onto
QA-TB-Comments-Organiser to copy only those files into Sorted.

--------------------------------------------------------------------------------
  PORTAL DOCUMENT LIST (QA-TB-Checker)
--------------------------------------------------------------------------------

  The "portal list" is a document list you export from the client's
  document portal, such as 4Projects or Asite. Save that spreadsheet
  (Excel or CSV) in the same folder as the drawings and QA-TB-Checker.
  CSV is fine for Holloway Park and for 4Projects (Oval C+D, Trillium,
  West Cromwell Road). Those CSV downloads stop at 500 documents — if
  the file has exactly 500 rows, the report asks you to request the
  Excel export instead, because the CSV is likely missing drawings.
  Excel is slower (emailed) but complete. CSV is instant and is enough
  when the project is still small or you are checking a subset.

  When that file is there, the Excel report will also compare each drawing
  with what is already on the portal:

    - Revisions: the issue on the drawing should be the next one after
      the portal (for example portal C01, this drawing C02).
    - QA Rejected: the file can be replaced at the same revision (usual
      on WCR). Trillium also allows P00. Document control is not asked
      to change that status.
    - Titles: the title on the drawing should match the title on the
      portal.

  You can also drag the portal spreadsheet onto QA-TB-Checker along with
  the drawings. If you do not, it still looks for an export in the folder.

If you run a program more than once, new report files may be named with -1,
-2, and so on so earlier reports are not lost.

--------------------------------------------------------------------------------
  MORE INFORMATION
--------------------------------------------------------------------------------

  Source code and full documentation (for IT or technical staff):
  Filename tools:  https://github.com/Optimodo/mbs-file-tools
  Title-block QA:  https://github.com/Optimodo/pdf-title-block-scanner

--------------------------------------------------------------------------------
  CONTACT
--------------------------------------------------------------------------------

  Mike McLean
  mike.mclean@malcolmbuildingservices.co.uk

================================================================================
  Tip: Keep this text file in the same folder as the programs so others know
  what they are for.
================================================================================
