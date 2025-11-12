# ProDuckt

AI-powered product discovery platform that helps product teams generate Market Requirements Documents (MRDs) and prioritize initiatives using Claude AI.

## TL;DR - Quick Start

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and SECRET_KEY (use: openssl rand -hex 32)

# 2. Install backend dependencies
python -m venv backend/venv
source backend/venv/bin/activate
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend && npm install && cd ..

# 4. Setup database
alembic upgrade head
python scripts/init_db.py

# 5. Start servers
./start.sh
```

Access at http://localhost:5173 with `admin@produckt.local` / `Admin123!`

---

## Features

- **AI-Powered Discovery** - Automatically generate contextual questions to understand product initiatives
- **MRD Generation** - Create comprehensive Market Requirements Documents with AI assistance
- **Initiative Scoring** - Calculate RICE and FDV scores to prioritize product work
- **Context Management** - Maintain organizational context for better AI recommendations
- **PDF Export** - Export MRDs and scorecards as professional PDFs

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 20.19.0+ or 22.12.0+**
  - Note: Node.js 18 is not supported due to frontend dependency requirements (Vite 7, React Router 7)
  - If you have Node.js 18, upgrade using [nvm](https://github.com/nvm-sh/nvm): `nvm install 20 && nvm use 20`
- **Anthropic API key** ([Get one here](https://console.anthropic.com/))
- **System libraries for PDF generation** (WeasyPrint dependencies):
  - **Ubuntu/Debian**: `sudo apt-get install -y python3-dev libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info`
  - **macOS**: `brew install pango gdk-pixbuf libffi`
  - **Windows**: See [WeasyPrint documentation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)

### Installation

**Important**: All commands should be run from the project root directory unless otherwise specified.

1. **Clone and configure environment**

```bash
# Copy environment template
cp .env.example .env

# Edit .env and configure required variables:
# - SECRET_KEY: Generate with: openssl rand -hex 32
# - ANTHROPIC_API_KEY: Your Anthropic API key from https://console.anthropic.com/
```

2. **Backend setup**

```bash
# Create virtual environment in backend directory
python -m venv backend/venv

# Activate virtual environment
source backend/venv/bin/activate  # Windows: backend\venv\Scripts\activate

# Install Python dependencies (includes FastAPI, Anthropic SDK, WeasyPrint, etc.)
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Initialize database with roles and admin user
python scripts/init_db.py
```

**Important**: The `init_db.py` script creates:
- Default RBAC roles (admin, product, technical, bizdev, viewer)
- A default admin user with credentials:
  - Email: `admin@produckt.local`
  - Password: `Admin123!`
- Proper role assignments so admin features work correctly

⚠️ Change the admin password after first login!

3. **Frontend setup**

```bash
# Install Node.js dependencies
cd frontend
npm install
cd ..
```

4. **Start development servers**

**Option A: Using the startup script (Recommended)**

```bash
./start.sh
```

The startup script will:
- ✓ Validate all system requirements (Python, Node.js, system libraries)
- ✓ Check environment configuration (.env file)
- ✓ Verify backend and frontend dependencies are installed
- ✓ Initialize database if needed (migrations + roles)
- ✓ Check that ports 8000 and 5173 are available
- ✓ Start both backend and frontend servers
- ✓ Display access URLs and admin credentials

Press `Ctrl+C` to stop both servers.

**Option B: Manual startup (two terminals)**

```bash
# Terminal 1 - Backend API server
source backend/venv/bin/activate  # Windows: backend\venv\Scripts\activate
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend development server
cd frontend
npm run dev
```

### Access

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Default Admin**: `admin@produckt.local` / `Admin123!`

## Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed architecture documentation.

```
produck/
├── backend/          # FastAPI backend with AI agents
├── frontend/         # React + Material-UI frontend
├── alembic/          # Database migrations
└── .env              # Single config file for both services
```

## Tech Stack

**Backend:**
- FastAPI - Modern Python web framework
- SQLAlchemy - Database ORM (SQLite default, PostgreSQL supported)
- Anthropic Claude 3.5 Sonnet - AI agent orchestration
- WeasyPrint - PDF generation

**Frontend:**
- React 19 + Vite
- Material-UI (MUI) - Component library
- TanStack Query - Data fetching and caching
- React Router - Navigation

## Environment Configuration

The project uses a **single `.env` file** at the root. Key variables:

```env
# Database
DATABASE_URL=sqlite:///./produck.db

# Security
SECRET_KEY=your-secret-key-here

# AI Integration
ANTHROPIC_API_KEY=your-anthropic-api-key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

See [.env.example](.env.example) for complete configuration options.

## Development

### Database Management

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Initialize/seed database (safe to run multiple times)
python scripts/init_db.py

# Reset database completely
rm produck.db
alembic upgrade head
python scripts/init_db.py
```

**Troubleshooting**:

*Admin menus not appearing:*
1. The user needs to have roles assigned in the new RBAC system
2. Run `python scripts/init_db.py` to ensure roles are created
3. For existing admin users, the script `fix_admin_roles.py` can assign roles
4. Log out and log back in to refresh the session

*PDF export fails with "PDF.__init__()" error:*
1. This is a version incompatibility between WeasyPrint and pydyf
2. Fix: `pip install pydyf==0.10.0` (already pinned in requirements.txt)
3. The requirements file now includes the correct version

### Testing

```bash
# Backend tests
pytest

# Frontend tests
cd frontend
npm test
```

## Production Deployment

For production use:

1. Use PostgreSQL instead of SQLite
2. Set strong `SECRET_KEY`
3. Configure proper CORS origins
4. Use environment variables (not `.env` file)
5. Set up HTTPS
6. Use production WSGI server (Gunicorn with Uvicorn workers)

## License

This project is licensed under the **PolyForm Noncommercial License 1.0.0**.

**TL;DR:** Free for personal, educational, and non-commercial use. Commercial use requires a separate license.

For commercial licensing inquiries, contact: produckt.team@pm.me

## Support

- Issues: [GitHub Issues](https://github.com/noam-r/produckt/issues)

