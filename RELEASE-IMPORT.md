# GitHub release notes import: specification

The stakeholder source is Oliver's feature brief of 2026-09-29. This document
records what was decided from it, stated so each rule can fail a test. Every
requirement names the test that verifies it.

## 1. Scope

**In:** one tray control; a dialog taking a repository address; retrieval of
every published release through GitHub's REST API; one Markdown file per
release in a local folder; opening that folder with the newest release
selected; refreshing an existing import without duplication or silent loss.

**Out, deliberately:** a repository, issue, pull request, commit or tag
browser; a Git client; authentication or tokens; release asset downloads;
editing or publishing back to GitHub; bidirectional synchronisation; deletion
of a local file because its release was withdrawn.

## 2. Definitions

| Term | Meaning |
|---|---|
| Release | A published, non-draft GitHub Release. A tag with no release is not one. |
| Collection | The local folder holding one repository's imported releases. |
| Manifest | `.plainsight-collection.json` in a collection: its source and its documents in display order. |
| Edited | A release file whose bytes match neither what was last written nor what would be written now. |
| Withdrawn | A release present in the manifest and absent from GitHub's current answer. |

## 3. Decisions taken against the existing architecture

| # | Decision | Reason |
|---|---|---|
| D1 | The collection store is the one module besides the settings store allowed to write; it writes only beneath its import directory. | The feature writes files by definition; `tests/structural/test_read_only.py` names it rather than being weakened. |
| D2 | A folder may declare the order of its documents through a manifest; documents it does not name follow in the ordinary case-insensitive order. | Newest first by publication date, without relying on file names and without GitHub-specific code in the tree or renderer. |
| D3 | Collections live at `~/.plainsight/github-releases/<owner>/<repo>`. | Beside the settings, the application's own storage; one directory per owner cannot collide. Uninstalling removes it with the settings (see Open questions). |
| D4 | Opening a collection is choosing it as the folder being read, which is remembered. | It is the existing "open a directory" path; no second mode. |
| D5 | Cancel is honoured until writing begins, never during it. | Nothing on disk changes before the plan is committed, so stopping earlier is always safe. |
| D6 | A still-published release whose local file was deleted is written again. | A refresh re-synchronises from GitHub; writing a missing file destroys nothing. |

## 4. Functional requirements

### Address

- **FR-01** When the dialog opens, the import dialog shall show `https://github.com/` fully selected in a focused address field.
  Verified by `tests/ui/test_release_import_dialog.py::test_it_opens_focused_on_the_address_with_the_default_selected`
- **FR-02** The address parser shall accept `owner/repo`, `github.com/owner/repo`, `https://github.com/owner/repo` with or without a trailing slash and surrounding whitespace, answering owner and repository.
  Verified by `tests/domain/test_repository_address.py::test_every_accepted_form_names_the_same_repository`
- **FR-03** When an address names a recognised repository sub-page such as `/releases`, the parser shall answer the repository itself.
  Verified by `tests/domain/test_repository_address.py::test_a_recognised_sub_page_names_its_repository`
- **FR-04** If an address is empty, is the bare host, lacks an owner or a repository, names another host, names an unrecognised sub-page or breaks GitHub's naming rules, then the parser shall refuse it with a stated reason and no request shall be made.
  Verified by `tests/domain/test_repository_address.py::test_each_malformed_address_is_refused_with_a_reason` and `tests/ui/test_release_import_dialog.py::test_a_refused_address_asks_nothing_of_the_network`

### Retrieval

- **FR-05** The release source shall follow GitHub's `Link: rel="next"` pagination until no next page remains.
  Verified by `tests/infrastructure/test_github_releases.py::test_every_page_is_followed_until_there_is_no_next`
- **FR-06** The release source shall leave out draft releases and keep pre-releases.
  Verified by `tests/infrastructure/test_github_releases.py::test_drafts_are_left_out_and_prereleases_kept`
- **FR-07** If GitHub answers 404, a rate limit, another refusal, a server error, no connection, a timeout, an oversized page or a body that does not describe releases, then the release source shall raise the typed problem for that case.
  Verified by `tests/infrastructure/test_github_releases.py` (one test per case)
- **FR-08** If a repository has no published release, then the import service shall report that and write nothing.
  Verified by `tests/application/test_release_import.py::test_no_releases_is_reported_and_nothing_is_written`

### Generated documents

- **FR-09** The import service shall write one Markdown file per release: a heading, the tag, the release date, a pre-release line where it is one, a source link, a rule, then the release body unchanged.
  Verified by `tests/domain/test_release.py::test_a_release_becomes_its_header_then_its_body_unchanged`
- **FR-10** If a release has no body, then its document shall say so rather than being omitted.
  Verified by `tests/domain/test_release.py::test_a_release_with_no_body_still_has_a_document`
- **FR-11** The file name shall be `YYYY-MM-DD_<tag>.md` (`undated_<tag>.md` without a date), safe on Windows, never climbing out of its folder, at most 100 characters of stem, made unique case-insensitively.
  Verified by `tests/domain/test_file_names.py`

### Ordering and opening

- **FR-12** The collection shall list its releases newest first by publication date; undated releases last; ties broken by GitHub's release id, newest first.
  Verified by `tests/domain/test_release_collection.py::test_entries_are_newest_first_whatever_their_names` and `tests/infrastructure/test_document_repository_order.py`
- **FR-13** When an import succeeds, the window shall read the collection as its folder and select the newest release.
  Verified by `tests/ui/test_release_import_flow.py::test_a_finished_import_opens_the_collection_on_its_newest_release`

### Refresh

- **FR-14** When a repository is imported again, the import service shall reuse its collection, keeping each release's file name by its GitHub id.
  Verified by `tests/domain/test_release_collection.py::test_a_known_release_keeps_its_file_name`
- **FR-15** The import service shall rewrite a file only when it is unedited and GitHub's content changed.
  Verified by `tests/domain/test_release_collection.py::test_an_unedited_file_whose_release_changed_is_rewritten`
- **FR-16** If a file was edited locally and its release changed on GitHub, then the import service shall keep the local file and report it.
  Verified by `tests/domain/test_release_collection.py::test_an_edited_file_is_kept_and_reported`
- **FR-17** If a release was withdrawn from GitHub, then the import service shall keep its local file.
  Verified by `tests/domain/test_release_collection.py::test_a_withdrawn_release_keeps_its_file`

### Atomicity and safety

- **FR-18** The collection store shall build a first import in a hidden staging folder and move it into place only when complete.
  Verified by `tests/infrastructure/test_release_collection_store.py::test_a_failed_first_import_leaves_no_collection`
- **FR-19** If a refresh fails, then every file in the collection shall be either its previous or its new content in full.
  Verified by `tests/infrastructure/test_release_collection_store.py::test_a_failed_refresh_leaves_the_collection_readable`
- **FR-20** The collection store shall refuse any file name that would land outside the collection, including one read from a tampered manifest.
  Verified by `tests/infrastructure/test_release_collection_store.py::test_a_name_that_climbs_out_is_refused`

### Interface

- **FR-21** While an import runs, the dialog shall state its stage and keep the window responsive.
  Verified by `tests/ui/test_release_import_dialog.py::test_the_stages_are_stated_while_it_runs`
- **FR-22** When Cancel or Escape is pressed while retrieving, the dialog shall stop before anything is written.
  Verified by `tests/ui/test_release_import_dialog.py::test_cancel_while_retrieving_writes_nothing`
- **FR-23** Enter in the address field shall start the import.
  Verified by `tests/ui/test_release_import_dialog.py::test_enter_in_the_field_imports`

## 5. Non-functional requirements

- **NFR-01** A GitHub page larger than 32 MiB shall be refused unread past that cap. (GitHub caps a release body at 125,000 characters; 100 of them fit well within it.)
  Verified by `tests/infrastructure/test_github_releases.py::test_a_page_past_the_cap_is_refused_unread`
- **NFR-02** A single request shall time out after 15 seconds.
  Verified by `tests/infrastructure/test_github_releases.py::test_one_page_is_read_with_the_right_headers_and_timeout`
- **NFR-03** Retrieval shall stop after 100 pages (10,000 releases) rather than follow a pagination loop for ever.
  Verified by `tests/infrastructure/test_github_releases.py::test_a_pagination_loop_is_stopped`
- **NFR-04** Nothing downloaded is executed, opened or followed during import; release Markdown reaches the screen through the existing renderer only.
  Verified by inspection: `github_releases` and `release_collection_store` call no opener, launcher or subprocess; `tests/infrastructure/test_release_rendering.py` renders a generated document through `DocumentHtmlRenderer`.

**Measured against the live API on 2026-09-29:** importing `oernster/PlainSight` read 9 releases and listed them newest first; a second import wrote nothing (9 unchanged). Forced to 2 releases per page, the real `Link` headers were followed across 5 pages to the same 9 releases.

**Non-claims.** The import uses GitHub's unauthenticated API, which allows 60 requests an hour per address; the collection is not encrypted; edits made locally are never merged with GitHub's changes.

## 6. Open questions

| # | Question | Owner |
|---|---|---|
| Q1 | Uninstalling removes `~/.plainsight`, so imported collections (and any edits made to them) go with it; the README and the uninstall screen now say so. Keep this, else move collections under Documents? | Oliver |
| Q2 | A first import killed mid-write (power loss, not an exception) leaves a hidden `.staging-*` folder beside the collection. Nothing reads it; nothing removes it either. Sweep old ones on the next import? | Oliver |
