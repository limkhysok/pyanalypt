# Project Plan: PyAnalypt (Real-World Data Analysis Workflow)

## Core Technologies
- **Backend:** Django + DRF, Pandas, Scikit-learn, PostgreSQL, Redis.
- **Frontend:** Next.js (TypeScript), Shadcn UI, Apache ECharts.

---

## Part 1: Backend (The Data Engine)

### 1. Ingestion & Persistence (Import)
- [x] **Database Setup:** Initialize PostgreSQL for users, datasets, and analysis metadata.
- [x] **File Processing:** Implement `datasets` app to handle CSV/Excel/JSON uploads linked directly to the User.
- [ ] **Data Versioning:** Support "Dataset Versions" so cleaning creates new records linked to the original file.

### 2. Diagnostic Engine (Identifying Issues)
- [ ] **Profiling Utility:** Use Pandas to detect:
    - Missing values (counts and percentages per column).
    - Duplicate rows.
    - Data type inconsistencies (e.g., numbers stored as strings).
    - Outliers using Z-Score or IQR methods.

### 3. Wrangling Service (Data Cleaning)
- [ ] **Cleaning Pipelines:** Build API endpoints to apply:
    - Missing value imputation (Mean, Median, Mode, or Constant).
    - Row/Column dropping.
    - Data type casting.
    - String sanitization (trimging, case normalization).

### 4. Descriptive Engine (EDA)
- [ ] **Statistical Profiling:** Calculate summary statistics (Mean, Median, Std Dev, Min/Max, Quartiles).
- [ ] **Relationship Discovery:** Generate correlation matrices and cross-tabulations.

### 5. API Visualization Bridge
- [ ] **Chart Formatter:** Convert Pandas DataFrames into lean JSON structures specifically for Apache ECharts (Scatter, Bar, Line).

---

## Part 2: Frontend (The Analysis Workspace)

### 1. Import Workspace
- [ ] **Multi-Source Upload:** Drag-and-drop file uploader and custom "Paste Data" text area.
- [ ] **Home Dashboard:** Visual inventory of all data analysis datasets.

### 2. Diagnosis Dashboard (Identifying Issues)
- [ ] **Quality Report:** Visual cards showing "% of missing data" and "Dirty Data" warnings.
- [ ] **Inconsistency Highlighting:** UI that highlights columns with potential issues.

### 3. Cleaning Interface (Wrangling)
- [ ] **Command Center:** Interactive sidebar where users can select cleaning operations and preview changes.
- [ ] **History Logs:** Show what cleaning steps were applied to the dataset.

### 4. Exploratory Dashboard (EDA)
- [ ] **Table View:** High-performance data grid with sorting and filtering.
- [ ] **Stat Cards:** Quick-glance cards for core dataset metrics.

### 5. Visualization Studio
- [ ] **Chart Builder:** Interactive axis selection (X-axis, Y-axis, Color/Group-by).
- [ ] **Theme System:** Professional "Business Intelligence" styles for all ECharts.

### 6. Insight & Reporting
- [ ] **Annotation System:** Allow users to add notes/insights directly next to visualizations.
- [ ] **Export Center:** Download cleaned datasets and save visualizations as PNG/PDF.

---

## Optional: Advanced Analytics (ML)
*Note: This is an "add-on" for predictive tasks, not the core focus.*
- [ ] **KMeans Clustering:** To find hidden segments in customer/sales data.
- [ ] **Linear Regression:** To predict simple future trends based on historical values.

---

## Technical Specifications
- **Input Formats:** .csv, .xlsx, .json, .html, .xml, .parquet
- **Output Formats:** .png (default), .jpg, .pdf, .html, .xlsx
- **Key Python Libs:** `pandas`, `openpyxl`, `scikit-learn`, `kaleido` (for PDF)