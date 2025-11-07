# ProDuckt

AI-powered product discovery platform that helps product teams generate Market Requirements Documents (MRDs) and prioritize initiatives using Claude AI.

## Features

- **AI-Powered Discovery** - Automatically generate contextual questions to understand product initiatives
- **MRD Generation** - Create comprehensive Market Requirements Documents with AI assistance
- **Initiative Scoring** - Calculate RICE and FDV scores to prioritize product work
- **Context Management** - Maintain organizational context for better AI recommendations
- **PDF Export** - Export MRDs and scorecards as professional PDFs

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Anthropic API key ([Get one here](https://console.anthropic.com/))

### Installation

1. **Clone and configure**

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set:
# - SECRET_KEY: Generate with: openssl rand -hex 32
# - ANTHROPIC_API_KEY: Your Anthropic API key
```

2. **Backend setup**

```bash
# Create virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations (from project root)
cd ..
alembic upgrade head
```

3. **Frontend setup**

```bash
cd frontend
npm install
```

4. **Start development servers**

```bash
# Terminal 1 - Backend (from project root)
source backend/venv/bin/activate
python -m uvicorn backend.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Access

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

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

# Reset database
rm produck.db
alembic upgrade head
```

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

- Issues: [GitHub Issues](https://github.com/yourusername/produck/issues)
- Documentation: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- API Docs: http://localhost:8000/docs (when running locally)
