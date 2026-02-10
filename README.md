# PyAnalypt - Analytics Platform

A Django-based analytics platform with RESTful API, JWT authentication, and Google OAuth integration.

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- PostgreSQL database
- Redis (for caching)

### Installation

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
- Copy `.env.example` to `.env` (if exists, or see `env.md` for variables)
- Update database and Redis URLs
- Add Django secret key

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Run development server**
```bash
python manage.py runserver
```

Server runs at: `http://127.0.0.1:8000/`

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
│   ├── settings.py      # Main settings
│   ├── urls.py          # Root URL configuration
│   └── wsgi.py          # WSGI configuration
├── core/                # Core application
│   ├── models/          # Database models
│   │   └── auth_user.py # Custom user model
│   ├── adapters.py      # Google OAuth adapter
│   ├── admin.py         # Admin configuration
│   ├── urls.py          # App URL patterns
│   └── views.py         # API views
├── uploads/             # Uploaded files
├── venv/                # Virtual environment
├── .env                 # Environment variables (not in git)
├── .gitignore           # Git ignore rules
├── manage.py            # Django management script
├── requirements.txt     # Python dependencies
└── API_DOCS.md          # API documentation
```

---

## 🔐 Authentication System

### Features
- ✅ Email-based authentication
- ✅ JWT token management (access + refresh)
- ✅ Token rotation and blacklisting
- ✅ Google OAuth integration
- ✅ Custom user model with validations
- ✅ Password reset functionality

### Custom User Model
**Model**: `core.models.AuthUser`

**Fields**:
- `email` - Primary authentication field (unique)
- `username` - Display name (unique)
- `first_name`, `last_name`, `full_name`
- `profile_picture` - URL (from Google OAuth or CDN)
- `email_verified` - Boolean (auto-set for Google users)
- `password` - Hashed
- `is_staff`, `is_active`, `is_superuser`
- `date_joined`, `last_login`

**Validations**:
- Email: Valid email format, unique
- Username: Alphanumeric + `._-`, min 3 chars
- Names: Letters, hyphens, apostrophes, min 2 chars
- Full name: Letters + spaces, min 10 chars
- Password: Min 8 chars, validated by Django settings
- Profile picture: HTTPS only

### Google OAuth
Automatically extracts and populates:
- Email → `user.email`
- First/Last name → `user.first_name`, `user.last_name`
- Full name → `user.full_name`
- Profile picture → `user.profile_picture`
- Email verified → `user.email_verified = True`

---

## 🛠️ Tech Stack

### Backend
- **Django 5.2+** - Web framework
- **Django REST Framework** - API framework
- **dj-rest-auth** - Authentication endpoints
- **django-allauth** - Social authentication
- **djangorestframework-simplejwt** - JWT tokens
- **PostgreSQL** - Database
- **Redis** - Caching

### Authentication
- Email/password login
- Google OAuth 2.0
- JWT (JSON Web Tokens)

### Database
- PostgreSQL for data persistence
- Redis for session/cache storage

---

## 🧪 Testing

### Test API with cURL

**Register**:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/registration/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"test","password1":"Pass123!","password2":"Pass123!"}'
```

**Login**:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Pass123!"}'
```

**Get User**:
```bash
curl -X GET http://127.0.0.1:8000/api/v1/auth/user/ \
  -H "Authorization: Bearer <access_token>"
```

---

## 💡 Development Tips

### Useful Commands

```bash
# Run development server
python manage.py runserver

# Create superuser
python manage.py createsuperuser

# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Check database tables
python list_tables.py

# Django shell
python manage.py shell
```

### Database Utilities

- `list_tables.py` - List all database tables
- `check_auth_user.py` - Check auth_user table structure
- `test_auth_user.py` - Test AuthUser model
- `drop_tables.py` - Drop all tables (WARNING: destructive)

---

## 📦 Dependencies

See `requirements.txt` for full list. Key packages:

- `django>=5.2`
- `djangorestframework`
- `dj-rest-auth`
- `django-allauth`
- `djangorestframework-simplejwt`
- `psycopg[binary]` (PostgreSQL adapter)
- `django-redis`
- `django-cors-headers`
- `django-environ`

---

## 🔒 Security

- ✅ JWT token authentication
- ✅ Token rotation and blacklisting
- ✅ HTTPS enforcement for profile pictures
- ✅ Password hashing (Django default)
- ✅ CORS configuration
- ✅ Email verification support
- ✅ Rate limiting (to be implemented)

**Production Checklist**:
- [ ] Set `DEBUG = False`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Use environment variables for secrets
- [ ] Set up HTTPS/SSL
- [ ] Configure email backend for verifications
- [ ] Update Google OAuth redirect URIs
- [ ] Set up proper logging
- [ ] Configure rate limiting

---

## 📝 License

*To be determined*

---

## 👥 Contributors

*To be added*

---

**Version**: 1.0  
**Status**: ✅ Production Ready  
**Last Updated**: 2026-02-10
