# Frontend Integration Prompt — Null Handling Pipeline

## Context

Three new Datalab endpoints have been added for handling missing data. They are designed to be
used in sequence — **replace_values → drop_nulls → fill_nulls** — and the UI should guide the
user through this order. Each endpoint is independent; any one can be called without the others.

All endpoints are under `/api/v1/datalab/` and require `Authorization: Bearer <token>`.

---

## The 3 new endpoints at a glance

| # | Method | URL | Purpose |
|---|--------|-----|---------|
| 7 | POST | `/datalab/replace-values/{dataset_id}/` | Convert sentinel strings (`"N/A"`, `"-"`) to real NaN |
| 8 | POST | `/datalab/drop-nulls/{dataset_id}/` | Drop rows or columns with too many nulls |
| 9 | POST | `/datalab/fill-nulls/{dataset_id}/` | Fill remaining nulls with a chosen strategy |

---

## 1. Replace Values — `/datalab/replace-values/{dataset_id}/`

### What it does
Replaces specific values in the dataset with another value. The most common use case is
converting dirty sentinel strings (`"N/A"`, `"-"`, `"?"`, `"none"`) into real NaN so that
subsequent null operations work correctly.

### Request shape
```ts
{
  replacements: Record<string, string | number | null>,  // required
  columns?: string[]                                     // optional — omit to apply to ALL columns
}
```

### Examples
```ts
// Replace common sentinels with null (NaN) across all columns
{ replacements: { "N/A": null, "-": null, "?": null, "none": null } }

// Replace in specific columns only
{ replacements: { "999": null }, columns: ["age", "salary"] }

// Replace one value with another (not null)
{ replacements: { "Yes": "true", "No": "false" }, columns: ["is_active"] }
```

### Success response
```json
{
  "replacements": { "N/A": null, "-": null },
  "columns_affected": ["name", "status", "country"],
  "cells_replaced": 47
}
```

### UI behaviour
- Provide a multi-value tag input for `replacements` keys (old values to find)
- Provide a single input for the replacement value — default to empty which means `null`
- Optional column multi-select (populate from `inspect` endpoint)
- If `cells_replaced === 0`, show an info message: "No matching values found" — not an error
- After success, **re-fetch inspect** (null counts will have changed)

### Error cases
| HTTP | `detail` | Action |
|---|---|---|
| 400 | `"'replacements' must be an object..."` | Form validation — should not reach prod |
| 400 | `"Columns not found in dataset: [...]"` | Column picker out of sync — reload column list |

---

## 2. Drop Nulls — `/datalab/drop-nulls/{dataset_id}/`

### What it does
Drops rows or entire columns that contain null values. Two modes controlled by `axis`.

### Request shape
```ts
// axis="rows" (default)
{
  axis: "rows",
  how: "any" | "all",   // default "any"
  subset?: string[]     // check nulls only in these columns
}

// axis="columns"
{
  axis: "columns",
  thresh_pct: number    // 0–100 — drop columns where null% exceeds this
}
```

### Examples
```ts
// Drop any row that has at least one null
{ axis: "rows", how: "any" }

// Drop rows only if ALL values are null (safe cleanup)
{ axis: "rows", how: "all" }

// Drop rows where a key column is null
{ axis: "rows", how: "any", subset: ["user_id", "transaction_date"] }

// Drop columns that are more than 70% empty
{ axis: "columns", thresh_pct: 70 }
```

### Success response — rows
```json
{
  "axis": "rows",
  "rows_before": 1000,
  "rows_after": 943,
  "rows_dropped": 57
}
```

### Success response — columns
```json
{
  "axis": "columns",
  "columns_before": 12,
  "columns_after": 9,
  "columns_dropped": ["notes", "legacy_id", "deprecated_field"]
}
```

### UI behaviour
- Show two tabs or a toggle: **Drop Rows** / **Drop Columns**
- **Drop Rows tab**:
  - `how` selector: radio — "Drop if any null" (`any`) / "Drop if all null" (`all`)
  - Optional column multi-select for `subset` — label: "Check only these columns (optional)"
- **Drop Columns tab**:
  - Number slider or input for `thresh_pct` — label: "Drop columns with more than X% nulls"
  - Show a preview list of which columns would be dropped (can derive from `inspect` data client-side before calling)
- If `rows_dropped === 0` or `columns_dropped` is empty, show info: "No null rows/columns matched" — not an error
- After success, **re-fetch both preview and inspect** (row count and/or column list changed)

### Error cases
| HTTP | `detail` | Action |
|---|---|---|
| 400 | `"'axis' must be 'rows' or 'columns'."` | Dev validation |
| 400 | `"'how' must be 'any' or 'all'."` | Dev validation |
| 400 | `"'thresh_pct' is required when axis is 'columns'."` | Show field validation |
| 400 | `"'thresh_pct' must be a number between 0 and 100."` | Show field validation |
| 400 | `"Columns not found in dataset: [...]"` | Reload column list |

---

## 3. Fill Nulls — `/datalab/fill-nulls/{dataset_id}/`

### What it does
Fills remaining null values using a chosen imputation strategy.

### Request shape
```ts
{
  strategy: "constant" | "mean" | "median" | "mode" | "ffill" | "bfill",  // required
  value?: string | number,   // required only when strategy === "constant"
  columns?: string[]         // optional — omit to apply to ALL columns
}
```

### Strategy guide (use this for UI labels)

| `strategy` value | UI label | Notes |
|---|---|---|
| `median` | Fill with median | Best default for numeric — robust to outliers |
| `mean` | Fill with mean | Numeric only — sensitive to outliers |
| `mode` | Fill with most frequent value | Works on any dtype |
| `constant` | Fill with custom value | Shows extra input for `value` |
| `ffill` | Forward fill | For time-ordered data — uses previous row |
| `bfill` | Backward fill | For time-ordered data — uses next row |

### Examples
```ts
// Fill all numeric nulls with median (most common default)
{ strategy: "median" }

// Fill categorical columns with a constant
{ strategy: "constant", value: "Unknown", columns: ["country", "status"] }

// Forward-fill a time series column
{ strategy: "ffill", columns: ["daily_price"] }
```

### Success response
```json
{
  "strategy": "median",
  "cells_filled": 143,
  "skipped_columns": ["name", "country"]
}
```

> `skipped_columns` — columns that were skipped because the strategy is incompatible with their
> dtype (e.g. `mean`/`median` on a string column). This is not an error — show it as an info note:
> "Skipped X columns (incompatible dtype)".

### UI behaviour
- Strategy dropdown with the 6 options above (show the UI label, not the raw value)
- Default to `"median"` on mount
- Show `value` input **only** when `strategy === "constant"` — disable submit if empty
- Optional column multi-select — when empty, all columns are targeted
- After success:
  - Show `cells_filled` as the primary result
  - If `skipped_columns` is non-empty, show a soft warning: "Skipped columns: [name, country] — incompatible dtype for this strategy"
  - If `cells_filled === 0`, show info: "No null values found to fill"
  - **Re-fetch inspect** (null counts will have changed to zero for affected columns)

### Error cases
| HTTP | `detail` | Action |
|---|---|---|
| 400 | `"'strategy' must be one of: [...]"` | Dev validation |
| 400 | `"'value' is required when strategy is 'constant'."` | Disable submit if value is empty |
| 400 | `"Columns not found in dataset: [...]"` | Reload column list |

---

## Shared behaviour across all 3 endpoints

### Column list source
Always populate column pickers from `GET /api/v1/datalab/inspect/{dataset_id}/` — the
`info.columns[].column` field. Re-fetch this list after any operation that changes column structure
(drop_nulls with axis=columns, rename_column, drop_duplicates).

### Re-fetch rules after success

| Endpoint | Re-fetch preview | Re-fetch inspect |
|---|---|---|
| `replace_values` | No (values changed but structure same) | Yes (null counts changed) |
| `drop_nulls` rows | Yes (row count changed) | Yes (null counts changed) |
| `drop_nulls` columns | Yes (columns removed) | Yes (column list changed) |
| `fill_nulls` | No | Yes (null counts dropped to 0) |

### No-op responses (cells_replaced/filled = 0, rows/columns dropped = 0)
All three endpoints return HTTP 200 with a `"detail"` field when nothing changed. **Do not write
back to the file on no-ops** — the server already short-circuits. Show the `detail` message as an
info/toast, not an error banner.

### Error banner (500)
```json
{ "detail": "Failed to save updated dataset." }
```
Show as a full error banner. Do not update any counts or column lists on the frontend.
