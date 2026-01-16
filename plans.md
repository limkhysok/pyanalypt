# Project Plan: Decoupled Full-Stack Data Analyzer (2026)

## 1. System Architecture Overview
A modern "Headless" approach where the frontend and backend are independent, backed by a robust relational database.

*   **Frontend:** React (TypeScript) + NextJS + (Shadcn UI for components like buttons..) (Apache ECharts for Visualization)
*   **Backend:** Django + Django Rest Framework (DRF).
*   **Database:** PostgreSQL (Cloud Database supabase.com).
*   **Data Processing:** Pandas + Scikit-Learn.
*   **Cache:** Redis (for high-speed DataFrame access).

---

## Phase 1: Persistence Layer (PostgreSQL Setup)
**Goal:** Establish a permanent source of truth for files, users, and analysis results.

1.  **Database Connection:** Initialize PostgreSQL with psycopg2.
2.  **Schema Design:**
    *   `UserFile` Model: Store file metadata (original name, file size, storage path).
    *   `AnalysisResult` Model: Use a **JSONB** column to store summary statistics (mean, median, min/max) so you don't have to re-calculate them using Pandas every time the page loads.
3.  **Relational Integrity:** Link every uploaded file to a unique `session_id` or `user_id` to ensure data privacy.

---

## Phase 2: Backend Foundation (The API)
**Goal:** Setup a server that acts as a data engine.

1.  **Environment Setup:** Initialize Django with `djangorestframework`, `django-cors-headers`, and `django-environ` for DB credentials.
2.  **CORS Configuration:** Whitelist the React frontend (typically `localhost:5173`).
3.  **Migration:** Run initial migrations to build the PostgreSQL tables for file tracking.

---

## Phase 3: The Data Engine (Pandas Utility)
**Goal:** Abstract data manipulation away from the API views.

1.  **Ingestion:** Create `data_engine.py` to read CSVs and load them into Pandas.
2.  **Cleaning:** Standardize column names (lowercase, no spaces) for TypeScript compatibility.
3.  **Profiling:** Detect "Numeric" vs "Categorical" columns and save this metadata into the **PostgreSQL JSONB** field for instant retrieval.

---

## Phase 4: The Frontend (NextJS, TypeScript, Shadcn UI & Visualization)
**Goal:** Build a type-safe UI for visual rendering.

1.  **State Management:** Use React hooks to manage the `uploadedData` and `selectedFeatures`.
2.  **Component Architecture:**
    *   `FileUploader`: Posts CSVs to the API.
    *   `ControlPanel`: Fetches column metadata from the PostgreSQL-backed API.
    *   `Visualizer`: Renders data via Apache ECharts.
3.  **Type Safety:** Match TypeScript interfaces to the PostgreSQL schema.

---

## Phase 5: Full-Stack Integration (The Flow)
**Goal:** Connect layers via REST endpoints.

1.  **Upload Flow:** Frontend POSTs file -> Django saves file to disk -> Django creates a record in **PostgreSQL** -> returns `file_id`.
2.  **Processing Flow:** Frontend sends `file_id` + `axes` -> Django fetches file path from **PostgreSQL** -> Pandas processes -> returns JSON.
3.  **JSON Exchange:** Return lean JSON arrays for optimal chart performance.

---

## Phase 6: The Intelligence Layer (Machine Learning)
**Goal:** Add server-side analytical power.

1.  **Clustering Logic:** Use `scikit-learn` (KMeans) on the backend.
2.  **Augmented Data:** Add `cluster_id` to the JSON response.
3.  **Visual Mapping:** ECharts colors points based on the `cluster_id`.

---

## Phase 7: The "Glue" (State & Persistence)
**Goal:** Ensure the app survives browser refreshes.

1.  **Session Handshake:** Store the `short_uuid` in **PostgreSQL** to map anonymous sessions to specific data files.
2.  **Memory Management:** Integrate **Redis** to cache the Pandas DataFrames in RAM for 30 minutes, using the PostgreSQL `file_id` as the cache key.
3.  **Data Integrity:** Sanitize `NaN/Infinity` values before they leave the Python environment.

---

## Phase 8: The Shield (Security & Robustness)
**Goal:** Protect the server and database.

1.  **Secure File Ingestion:** Validate file signatures (Magic Numbers) and sanitize filenames.
2.  **Database Security:** Use Django’s ORM to prevent SQL injection; use `HttpOnly` cookies for any session tokens.
3.  **Data Sanitization:** Use `DOMPurify` on the frontend for any dynamic labels stored in the DB.

---



## PROJECT CORE

# Input: Support .csv, .xlsx, .json, .html, .xml, .parquet,
# Output: Support .png (default), .jpg, .pdf, .html, .xlsx
# pip install kaleido (for .pdf file format)