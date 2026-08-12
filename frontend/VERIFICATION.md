# Frontend Verification

## Commands

Codex desktop does not expose system `node`/`npm` in this workspace. Use the bundled runtime path when running the Vite scripts locally:

```bash
PATH=/Users/maxbond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH \
VITE_OFFLINE_MODE=true ./node_modules/.bin/vite --host 127.0.0.1 --port 5173
```

Production build smoke:

```bash
PATH=/Users/maxbond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH \
VITE_OFFLINE_MODE=true ./node_modules/.bin/vite build
```

Lint smoke:

```bash
PATH=/Users/maxbond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH \
./node_modules/.bin/oxlint
```

Vite can report large chunk warnings for existing export/chart dependencies.

## Audit Inputs

The frontend review is tracked as ten input units:

- `00-index.md` - reading order, priorities, and checked flows.
- `01-ui.md` - visual clarity, duplicate labels, non-product technical text.
- `02-ux.md` - analysis flow, upload state, discoverability.
- `03-accessibility.md` - file upload, modal labels, button names, theme radios.
- `04-responsive.md` - mobile 390px students and history layouts.
- `05-upload-and-validation.md` - selected file list, removal, validation copy.
- `06-export-and-data.md` - file download reliability and export feedback.
- `07-settings-and-archive.md` - settings/archive navigation and wording.
- `08-additional-recommendations.md` - product polish and user guidance.
- `09-priority-cards.md` - P1-P7 regression priorities.

## Runtime Smoke Test

Run:

```bash
VITE_OFFLINE_MODE=true npm run dev -- --host 127.0.0.1
```

Checked flows:

- Offline login opens the upload workspace.
- XLSX upload shows client validation for extension and file size.
- Offline analysis reaches the naming dialog and saves a report.
- Report detail opens with dashboard, qualitative analysis, and analytical report tabs.
- Dashboard renders five chart panels.
- Qualitative analysis shows topic evidence lines.
- Analytical report renders four required sections.
- Mobile viewport check does not produce horizontal page overflow.

## Regression Checklist

- Upload screen has a keyboard-accessible file picker and no stale selected files after completing/archiving a report.
- Multi-file upload shows file names, sizes, validation status, per-file removal, and clear-all.
- Starting analysis without files explains what is missing.
- Completed offline analysis opens the report immediately, with naming as a secondary step.
- Report header has distinct actions for saving a title and exporting a file.
- Export menu exposes loading, success, and failure feedback for PDF, DOCX, Excel, CSV, and JSON.
- Mobile 390x844 shows the Students page without clipped values; course rows are readable.
- Sidebar history keeps full accessible names and shows enough metadata to distinguish reports.
- Settings and archive are reachable from the main sidebar and profile menu.
- Accessibility toolbar labels controls clearly and allows reset to defaults.

## Priority Cards Acceptance

Use this list as the post-fix gate for `09-priority-cards.md`.

- P1 Export: PDF, DOCX, Excel, CSV, and JSON create non-empty blobs, show loading/success/error state, and expose a fallback download link with the correct filename extension.
- P2 Mobile Students: viewport `390x844` shows course cards instead of a clipped table, with no horizontal page overflow.
- P3 File Choice: selected files show name, size, extension, validation status, per-file remove action, and `Очистить все`.
- P4 File Upload A11Y: the upload control has a visible keyboard-focusable target, label/description, Enter/Space activation, and a named file input.
- P5 Save Actions: inline rename uses `Сохранить название`; report export is named `Экспортировать отчет`.
- P6 Settings Visibility: `Студенты`, `Архив`, and `Настройки` are visible in the main sidebar; `#settings-archive` opens the archive tab directly.
- P7 Accessibility Toolbar: groups are labeled, controls have specific aria labels, active state is visible beyond color, and reset is available.
