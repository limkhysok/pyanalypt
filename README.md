# PyAnalypt - Analytics Platform

## ✨ Project Features

- **Robust REST API**: Fully functional endpoints powered by Django REST Framework.
- **Authentication System**: Secure JWT-based authentication with email verifications and Google OAuth via `django-allauth`.
- **Intelligent Data Engine**: Advanced Pandas operations running seamlessly under the hood to perform statistical generation.
- **Dataset Management**: Upload, preview, and process datasets in various formats (CSV, Excel, JSON, Parquet).
- **Automated Issue Diagnostics**: Auto-detects data anomalies like whitespace inconsistences, missing values, outliers, duplicate rows, and mojibake encodings.
- **Data Cleaning Suite**: A wide suite of data transformation operations (fill NAs, clip outliers, drop rows, rename columns, fix encodings).

---

## 🏗️ Project Structure

```
pyanalypt/
├── config/              # Django settings, WSGI, ASGI, and main URLs
├── apps/                # Core business logic directory
│   ├── core/            # Core Pandas data engines and utilities 
│   ├── datasets/        # Dataset ingestion, storage, and models
│   ├── issues/          # Data anomaly diagnostics and reporting
│   ├── cleaning/        # Operations to transform and clean data
│   └── users/           # Custom AuthUser models and OAuth handlers
├── .env                 # Environment variables
├── Dockerfile           # Docker image configuration
├── docker-compose.yml   # Multi-container orchestration
├── manage.py            # Django management script
├── requirements.txt     # Python dependencies
└── API_DOCS.md          # Comprehensive API documentation
```

---

## 📚 Related Documentation

If you'd like to explore the specifics of our architecture, endpoints, or environment setup, please refer to the dedicated documentation files below:

- 📖 **[API Documentation (`API_DOCS.md`)](./API_DOCS.md)**: Discover and interact with our fully documented Django REST framework endpoints.
- ⚙️ **[Environment Setup (`env.md`)](./env.md)**: Learn how to configure your local `.env`.
- 🗺️ **[Database Schemas (`mermaid_live.md`)](./mermaid_live.md)**: View our visual architecture pipelines and schema mappings.
- 🚀 **[Project Roadmaps (`plans.md`)](./plans.md)**: Check out the planned updates and milestones.
