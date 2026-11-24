# Wardrobe AI - Backend API & Database

Secure multi-user Flask REST API with PostgreSQL, SQLAlchemy ORM, Flask-Migrate, and JWT-Extended authentication with server-side token revocation.

## Tech Stack
- **Framework**: Flask 3.1
- **Database**: PostgreSQL 18.3
- **ORM**: Flask-SQLAlchemy 3.1
- **Migrations**: Flask-Migrate 4.1 (Alembic)
- **Authentication**: Flask-JWT-Extended (Access + Refresh tokens)
- **Security**: Werkzeug password hashing, TokenBlocklist revocation
- **Testing**: Pytest (14 automated tests)

## Setup & Running

### 1. Environment & Dependencies
```powershell
# Navigate to backend directory
cd d:\SHIVA\Documents\engineering\Project\WardrobeAI\backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Migration
```powershell
# Database migrations have already been generated and upgraded to wardrobe_ai
flask --app run.py db upgrade
```

### 3. Run Backend Server
```powershell
# Starts the backend on 0.0.0.0:5000 (accessible from Android emulator at http://10.0.2.2:5000)
python run.py
```

### 4. Run Automated Tests
```powershell
pytest -v
```

## API Endpoints

### Authentication
- `POST /api/auth/register`: Register a new user with profile.
- `POST /api/auth/login`: Authenticate with email/password; returns access & refresh tokens.
- `POST /api/auth/refresh`: Issue a new access token using a valid refresh token.
- `POST /api/auth/logout`: Revoke active JWT server-side.
- `GET /api/auth/me`: Fetch authenticated user identity and profile.

### Profile
- `GET /api/profile`: Retrieve user profile.
- `PUT /api/profile`: Update user profile (name, style, photo).

