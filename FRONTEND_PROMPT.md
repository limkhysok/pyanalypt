# Frontend Integration Prompt — Drop Duplicate Rows

## What changed

The `POST /api/v1/datalab/drop-duplicates/{dataset_id}/` endpoint now requires a `mode`
field instead of the old `subset` + `keep` combination. There are exactly 4 modes, each
mapping to one dedup strategy. Old requests that only sent `subset` and `keep` will break —
`mode` is now the primary selector.

---

## 4 modes — one UI control each

| Mode | Label to show user | Extra fields needed |
|---|---|---|
| `"all_first"` | "Remove duplicates — keep first" | none |
| `"all_last"` | "Remove duplicates — keep last" | none |
| `"subset_keep"` | "Remove duplicates by column — keep first/last" | column picker + keep selector |
| `"drop_all"` | "Drop all copies of any duplicate" | optional column picker |

---

## UI behaviour rules

### Mode selector
- Render as a radio group or dropdown with the 4 options above.
- Default to `"all_first"` on mount.

### Column picker (`subset`)
- Show **only** when mode is `"subset_keep"` or `"drop_all"`.
- Populate from the inspect endpoint (`GET /api/v1/datalab/inspect/{dataset_id}/`) column list.
- Allow multi-select.
- `"subset_keep"` → column picker is **required** (disable the submit button if empty).
- `"drop_all"` → column picker is **optional** (omit `subset` from body if nothing selected).

### Keep selector (`keep`)
- Show **only** when mode is `"subset_keep"`.
- Two options: `"first"` (default) and `"last"`.
- Do not send `keep` in the request body for any other mode.

---

## Request shape per mode

```ts
// all_first
{ mode: "all_first" }

// all_last
{ mode: "all_last" }

// subset_keep
{ mode: "subset_keep", subset: ["col_a", "col_b"], keep: "first" | "last" }

// drop_all — subset optional
{ mode: "drop_all" }
{ mode: "drop_all", subset: ["email"] }
```

---

## Success response

```json
{
  "mode": "subset_keep",
  "rows_before": 1000,
  "rows_after": 950,
  "rows_dropped": 50
}
```

- Show `rows_dropped` as the primary result number.
- If `rows_dropped === 0`, response also includes `"detail": "No duplicate rows found."` — show
  this as an info message, not an error.
- After a successful drop, **re-fetch** the preview and inspect data (row count and column stats
  will have changed).

---

## Error handling

| HTTP | `detail` value | Show to user as |
|---|---|---|
| 400 | `"Invalid 'mode'..."` | Dev/validation error — should not reach prod |
| 400 | `"'subset' is required for mode 'subset_keep'."` | Disable submit if subset is empty |
| 400 | `"For mode 'subset_keep', 'keep' must be 'first' or 'last'."` | Dev/validation error |
| 400 | `"Columns not found in dataset: [...]"` | Column picker out of sync — reload column list |
| 400 | `"'subset' must be a non-empty list of column names."` | Validation — same as above |
| 400 | `"Unsupported file format."` | Show generic error banner |
| 500 | `"Failed to save updated dataset."` | Show error banner, do not update row counts |
