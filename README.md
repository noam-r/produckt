# ProDuckt

AI-powered product discovery platform using Claude 3.5 Sonnet for MRD orchestration.

## Quick Start

### Prerequisites

- Python 3.10+ (for backend)
- Node.js 18+ (for frontend)
- Anthropic API key

### Setup

1. **Configure environment**

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and set your keys
nano .env  # or use your preferred editor
```

Required variables to update:
- `SECRET_KEY`: Generate with `openssl rand -hex 32`
- `ANTHROPIC_API_KEY`: Get from https://console.anthropic.com/

2. **Backend setup**

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations (from project root)
cd ..
alembic upgrade head
```

3. **Frontend setup**

```bash
cd frontend

# Install dependencies
npm install
```

4. **Start both services**

```bash
# Terminal 1 - Backend (from project root)
source backend/venv/bin/activate
python -m uvicorn backend.main:app --reload

# Terminal 2 - Frontend (from frontend directory)
cd frontend
npm run dev
```

### Access

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Project Structure

```
produck/
├── .env                    # Single environment file for entire project
├── .env.example           # Template for environment variables
├── alembic/               # Database migrations
├── alembic.ini            # Alembic configuration
├── backend/               # FastAPI backend
│   ├── agents/            # AI agents (Claude integration)
│   ├── models/            # Database models
│   ├── routers/           # API endpoints
│   ├── requirements.txt   # Python dependencies
│   └── README.md          # Backend documentation
└── frontend/              # React frontend
    ├── src/               # Frontend source code
    ├── package.json       # Node dependencies
    └── README.md          # Frontend documentation
```

## Key Features

1. **Initiative Management** - Create and track product initiatives
2. **AI-Powered Questions** - Automatically generate discovery questions
3. **Interactive Q&A** - Answer questions to build context
4. **MRD Generation** - Generate comprehensive Market Requirements Documents
5. **Prioritization** - RICE and FDV scoring for initiatives
6. **Context Management** - Organizational context versioning

## Environment Configuration

The project uses a **single `.env` file** at the project root. Both frontend and backend read from this file.

Key variables:
- `DATABASE_URL`: SQLite database path (default: `sqlite:///./produck.db`)
- `SECRET_KEY`: Secret key for JWT tokens
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `VITE_API_BASE_URL`: Frontend API endpoint (default: `http://localhost:8000`)
- `CORS_ORIGINS`: Allowed frontend origins

See [.env.example](.env.example) for complete configuration.

## Development

### Backend
- FastAPI framework
- SQLAlchemy ORM with SQLite
- Anthropic Claude 3.5 Sonnet
- Session-based authentication

See [backend/README.md](backend/README.md) for detailed backend documentation.

### Frontend
- React 19 with Vite
- Material-UI (MUI)
- TanStack Query for data fetching
- React Router for navigation

See [frontend/README.md](frontend/README.md) for detailed frontend documentation.

## Database

The project uses SQLite by default (no installation required). The database file `produck.db` is created automatically when you run migrations.

To reset the database:
```bash
rm produck.db
alembic upgrade head
```

For production, PostgreSQL is recommended. See [backend/README.md](backend/README.md) for PostgreSQL setup.

## Contributing

1. Create a new branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

MIT
