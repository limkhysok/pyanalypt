# PyAnalypt - Analytics Platform

A Django-based analytics platform with RESTful API, JWT authentication, and Google OAuth integration.

## 🚀 Quick Start

### Option 1: Running with Docker (Recommended)

If you have Docker Desktop installed, this is the easiest way to get started. It handles Python, PostgreSQL, and Redis for you.

1.  **Start the containers**
    ```bash
    docker-compose up --build
    ```

2.  **Create a superuser** (in a second terminal)
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

The app will be available at: `http://localhost:8000/`

---

### Option 2: Native Installation (Manual)

#### Prerequisites
- Python 3.13+
- PostgreSQL database
- Redis (for caching)

#### Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pyanalypt
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   - Copy `.env.example` to `.env`
   - Update `DATABASE_URL` and `REDIS_URL`
   - Add your Django `SECRET_KEY`

5. **Run migrations & Start**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[API_DOCS.md](API_DOCS.md)** | Complete API documentation with all endpoints |
| **[plans.md](plans.md)** | Project planning and roadmap |
| **[mermaid_live.md](mermaid_live.md)** | Database schema diagrams |
| **[env.md](env.md)** | Environment variables reference |

---

## 🔑 Admin Access

- **URL**: http://127.0.0.1:8000/admin/
- **Email**: `admin@pyanalypt.com`
- **Password**: `admin123!@#`

---

## 🌐 API Endpoints

**Base URL**: `/api/v1/`

### Authentication
- `POST /auth/registration/` - Register new user
- `POST /auth/login/` - Login with email/password
- `POST /auth/logout/` - Logout
- `GET /auth/user/` - Get current user
- `PUT /auth/user/` - Update user (full)
- `PATCH /auth/user/` - Update user (partial)
- `POST /auth/token/` - Get JWT token
- `POST /auth/token/refresh/` - Refresh JWT token

### OAuth
- `GET /accounts/google/login/` - Google OAuth login

### File Operations
- `POST /upload/` - Upload file for analysis

See **[API_DOCS.md](API_DOCS.md)** for complete documentation.

---

## 🏗️ Project Structure

```
pyanalypt/
├── config/              # Django settings and main URLs
├── core/                # Core application
├── datasets/            # Dataset management
├── projects/            # Project management
├── .env                 # Environment variables
├── Dockerfile           # Docker image configuration
├── docker-compose.yml   # Multi-container orchestration
├── manage.py            # Django management script
├── requirements.txt     # Python dependencies
└── API_DOCS.md          # API documentation
```

---

## 🛠️ Tech Stack

- **Backend**: Django 5.2+, DRF, Pandas, Scikit-learn
- **Database**: PostgreSQL
- **Cache**: Redis
- **Auth**: JWT (SimpleJWT), Google OAuth (Allauth)
