# ProDuckt Backend

FastAPI-based backend for ProDuckt - AI-powered product discovery platform.

## Prerequisites

- Python 3.10 or higher
- Anthropic API key (Claude)

## Quick Start

### 1. Set up Python environment

**Important:** Run these commands from the `backend` directory:

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure environment variables

**Important:** The project uses a single `.env` file at the **project root** (not in the backend directory).

If you don't have a `.env` file yet, copy from `.env.example` in the project root:

```bash
# From backend directory, go back to root
cd ..
cp .env.example .env
```

Then edit `.env` and update these key values:
- `SECRET_KEY`: Generate with `openssl rand -hex 32` or `python -c "import secrets; print(secrets.token_hex(32))"`
- `ANTHROPIC_API_KEY`: Your Anthropic API key from https://console.anthropic.com/

### 3. Run database migrations

**Important:** Run alembic commands from the **project root** directory:

```bash
# Navigate back to project root (from backend directory)
cd ..

# Run migrations (creates produck.db file)
alembic upgrade head
```

### 4. Start the development server

**Important:** Start the server from the **project root** directory with venv activated:

```bash
# From project root directory
# Activate the virtual environment first
source backend/venv/bin/activate

# Start the server
python -m uvicorn backend.main:app --reload
```

The API will be available at: http://localhost:8000

## API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Project Structure

```
backend/
├── agents/                 # AI agents
│   ├── base.py            # Base agent class
│   ├── knowledge_gap.py   # Question generation
│   ├── mrd_generator.py   # MRD generation
│   ├── scoring.py         # RICE/FDV scoring
│   └── prompts.py         # AI prompts
├── llm/                   # LLM integration
│   └── client.py          # Anthropic client
├── models/                # Database models
│   ├── user.py
│   ├── organization.py
│   ├── context.py
│   ├── initiative.py
│   ├── question.py
│   ├── mrd.py
│   ├── score.py
│   └── llm_call.py
├── repositories/          # Database access layer
│   ├── user.py
│   ├── organization.py
│   ├── context.py
│   ├── initiative.py
│   ├── question.py
│   ├── mrd.py
│   └── score.py
├── routers/              # API endpoints
│   ├── auth.py           # Authentication
│   ├── initiatives.py    # Initiative CRUD
│   ├── questions.py      # Q&A management
│   ├── context.py        # Context management
│   └── agents.py         # AI operations
├── schemas/              # Pydantic schemas
├── alembic/             # Database migrations
├── main.py              # FastAPI application
├── database.py          # Database configuration
├── auth.py              # Authentication utilities
└── requirements.txt     # Python dependencies
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_agents/test_knowledge_gap_agent.py

# Run with verbose output
pytest -v
```

## Common Tasks

### Create a new migration

```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

### Reset database

```bash
alembic downgrade base
alembic upgrade head
```

### Check database connection

```bash
python -c "from backend.database import engine; print(engine.connect())"
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login
- `POST /auth/logout` - Logout
- `GET /auth/session` - Get current session

### Initiatives
- `GET /api/initiatives` - List initiatives
- `POST /api/initiatives` - Create initiative
- `GET /api/initiatives/{id}` - Get initiative
- `PATCH /api/initiatives/{id}` - Update initiative
- `DELETE /api/initiatives/{id}` - Delete initiative
- `PUT /api/initiatives/{id}/status` - Update status

### Questions
- `GET /api/initiatives/{id}/questions` - List questions
- `GET /api/initiatives/{id}/questions/{qid}` - Get question
- `PUT /api/initiatives/{id}/questions/{qid}/answer` - Answer question
- `GET /api/initiatives/{id}/questions/unanswered/count` - Get count

### AI Agents
- `POST /api/agents/initiatives/{id}/generate-questions` - Generate questions
- `POST /api/agents/initiatives/{id}/regenerate-questions` - Regenerate questions
- `POST /api/agents/initiatives/{id}/generate-mrd` - Generate MRD
- `GET /api/agents/initiatives/{id}/mrd` - Get MRD
- `GET /api/agents/initiatives/{id}/mrd/content` - Get MRD content
- `POST /api/agents/initiatives/{id}/calculate-scores` - Calculate scores
- `GET /api/agents/initiatives/{id}/scores` - Get scores

### Context
- `GET /api/context` - Get organization context
- `PUT /api/context` - Update context

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| DATABASE_URL | PostgreSQL connection string | Yes | - |
| SECRET_KEY | Secret key for JWT tokens | Yes | - |
| ANTHROPIC_API_KEY | Anthropic API key | Yes | - |
| HOST | Server host | No | 0.0.0.0 |
| PORT | Server port | No | 8000 |
| RELOAD | Auto-reload on changes | No | True |
| CORS_ORIGINS | Allowed CORS origins | No | ["http://localhost:5173"] |

## Troubleshooting

### Database connection errors

For SQLite, the database file will be created automatically. If you have issues:

```bash
# Check if database file exists
ls -la produck.db

# Remove and recreate database
rm produck.db
alembic upgrade head
```

### Using PostgreSQL (Optional)

If you prefer PostgreSQL over SQLite:

1. Install PostgreSQL:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

2. Create database:
```sql
sudo -u postgres psql
CREATE DATABASE produck;
CREATE USER produck_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE produck TO produck_user;
\q
```

3. Install PostgreSQL driver:
```bash
pip install psycopg2-binary
```

4. Update `.env`:
```bash
DATABASE_URL=postgresql://produck_user:your_password@localhost:5432/produck
```

### Migration errors

```bash
# Check migration status
alembic current

# Show migration history
alembic history

# Downgrade one version
alembic downgrade -1
```

### Import errors

Make sure you're running commands from the project root, not the backend directory:
```bash
# Wrong
cd backend
python main.py

# Correct
python -m uvicorn backend.main:app --reload
```

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker

```bash
# Build image
docker build -t produck-backend .

# Run container
docker run -p 8000:8000 --env-file .env produck-backend
```

### Environment Setup

For production:
- Use a strong SECRET_KEY
- Set RELOAD=False
- Use a production-grade database
- Set up proper CORS origins
- Use HTTPS
- Set up rate limiting
- Configure logging
- Use environment variables, not .env file

## Contributing

1. Create a new branch for your feature
2. Write tests for new functionality
3. Ensure all tests pass
4. Update documentation
5. Submit a pull request

## License

MIT License
