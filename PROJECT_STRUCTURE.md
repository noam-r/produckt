# ProDuckt - Project Structure

Detailed architecture and structure documentation for the ProDuckt platform.

## Table of Contents

- [Overview](#overview)
- [Backend Structure](#backend-structure)
- [Frontend Structure](#frontend-structure)
- [Database Schema](#database-schema)
- [AI Agent Architecture](#ai-agent-architecture)
- [API Endpoints](#api-endpoints)

## Overview

ProDuckt is a full-stack application with a FastAPI backend and React frontend, designed as a monorepo with shared configuration.

```
produck/
├── .env                      # Single environment file for entire project
├── .env.example             # Environment template
├── alembic/                 # Database migrations
├── alembic.ini              # Alembic configuration
├── backend/                 # Python backend
│   ├── agents/              # AI agents
│   ├── auth/                # Authentication
│   ├── llm/                 # LLM client
│   ├── models/              # Database models
│   ├── repositories/        # Data access layer
│   ├── routers/             # API endpoints
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── database.py          # Database config
│   ├── main.py              # FastAPI app
│   └── requirements.txt     # Python dependencies
├── frontend/                # React frontend
│   ├── public/              # Static assets
│   ├── src/
│   │   ├── api/             # API client
│   │   ├── components/      # React components
│   │   ├── context/         # Context providers
│   │   ├── hooks/           # Custom hooks
│   │   ├── layouts/         # Layout components
│   │   ├── pages/           # Page components
│   │   ├── theme/           # MUI theme
│   │   ├── App.jsx          # App root
│   │   └── main.jsx         # Entry point
│   ├── package.json         # Node dependencies
│   └── vite.config.js       # Vite configuration
└── tests/                   # Test files
```

## Backend Structure

### Core Modules

#### `/backend/agents/`
AI agents that orchestrate Claude API calls for different tasks:

- `base.py` - Base agent class with LLM calling logic
- `knowledge_gap.py` - Generates discovery questions
- `mrd_generator.py` - Generates MRD sections
- `mrd_editor.py` - Consolidates and edits MRD
- `scoring.py` - Calculates RICE and FDV scores
- `prompts.py` - System prompts for AI agents

#### `/backend/auth/`
Authentication and session management:

- `session.py` - Session management
- `password.py` - Password hashing utilities

#### `/backend/llm/`
LLM integration layer:

- `client.py` - Anthropic API client wrapper

#### `/backend/models/`
SQLAlchemy database models:

- `user.py` - User accounts
- `organization.py` - Organizations/tenants
- `context.py` - Organizational context
- `initiative.py` - Product initiatives
- `question.py` - Discovery questions
- `answer.py` - Question answers
- `mrd.py` - Market Requirements Documents
- `score.py` - RICE/FDV scores
- `llm_call.py` - LLM usage tracking

#### `/backend/repositories/`
Data access layer (Repository pattern):

- One repository per model
- Handles all database operations
- Implements business logic queries

#### `/backend/routers/`
FastAPI route handlers:

- `auth.py` - Authentication endpoints
- `initiatives.py` - Initiative CRUD
- `questions.py` - Question management
- `context.py` - Context management
- `agents.py` - AI operations

#### `/backend/schemas/`
Pydantic schemas for request/response validation:

- Request models
- Response models
- Data validation rules

#### `/backend/services/`
Business logic services:

- `pdf_generator.py` - PDF generation (MRD and scorecards)

### Backend Flow

1. **Request** → API Router
2. **Router** → Repository (data access)
3. **Repository** → Database (SQLAlchemy)
4. **Router** → Agent (if AI needed)
5. **Agent** → LLM Client → Anthropic API
6. **Response** ← Router ← Schema validation

## Frontend Structure

### Core Directories

#### `/frontend/src/api/`
API client and endpoint definitions:

- `client.js` - Axios client with interceptors
- `initiatives.js` - Initiative endpoints
- `questions.js` - Question endpoints
- `context.js` - Context endpoints

#### `/frontend/src/components/`
Reusable React components:

- `InitiativeCard.jsx` - Initiative display card
- `QuestionsList.jsx` - Questions interface
- `ScoresTab.jsx` - Scoring visualization
- `MRDViewer.jsx` - MRD document viewer
- `Logo.jsx` - Application logo

#### `/frontend/src/context/`
React Context providers:

- `AuthContext.jsx` - Authentication state
- `ThemeContext.jsx` - Theme (light/dark mode)

#### `/frontend/src/hooks/`
Custom React hooks:

- `useInitiatives.js` - Initiative operations
- `useQuestions.js` - Question operations

#### `/frontend/src/layouts/`
Layout components:

- `MainLayout.jsx` - Main app layout with sidebar
- `AuthLayout.jsx` - Authentication pages layout

#### `/frontend/src/pages/`
Page components:

- `Dashboard.jsx` - Dashboard overview
- `Initiatives.jsx` - Initiatives list
- `InitiativeDetail.jsx` - Initiative detail view
- `Context.jsx` - Context management
- `Login.jsx` - Login page
- `Register.jsx` - Registration page

#### `/frontend/src/theme/`
Material-UI theme configuration:

- `theme.js` - Theme definitions (light/dark)

### Frontend Flow

1. **User Action** → Page Component
2. **Page** → Custom Hook (useQuery/useMutation)
3. **Hook** → API Client
4. **API Client** → Backend API
5. **Response** → React Query Cache
6. **Cache** → Component Re-render

## Database Schema

### Core Tables

**organizations**
- Organization/tenant data
- Multi-tenancy support

**users**
- User accounts
- Authentication
- Organization membership

**context**
- Organizational context
- Versioned updates
- Used by AI agents

**initiatives**
- Product initiatives
- Status tracking
- Organization-scoped

**questions**
- Discovery questions
- Generated by AI
- Initiative-specific

**answers**
- Question responses
- User-provided context
- Timestamped

**mrds**
- Market Requirements Documents
- Generated markdown
- Version tracking

**scores**
- RICE scores (reach, impact, confidence, effort)
- FDV scores (feasibility, desirability, viability)
- Reasoning/rationale

**llm_calls**
- Usage tracking
- Token consumption
- Cost monitoring

### Relationships

```
organizations
  ├── users (one-to-many)
  ├── context (one-to-many, versioned)
  └── initiatives (one-to-many)
      ├── questions (one-to-many)
      │   └── answers (one-to-many)
      ├── mrd (one-to-one)
      └── score (one-to-one)
```

## AI Agent Architecture

### Agent Flow

1. **Knowledge Gap Agent**
   - Input: Initiative details, context
   - Output: 5-10 discovery questions
   - Iterative improvement based on existing Q&A

2. **MRD Generator Agents**
   - Multiple section-specific agents
   - Parallel generation of 10 sections
   - Uses all Q&A and context

3. **MRD Editor Agent**
   - Consolidates all sections
   - Removes repetition
   - Ensures narrative flow
   - Tightens prose

4. **Scoring Agent**
   - Calculates RICE and FDV scores
   - Provides detailed reasoning
   - Uses MRD and Q&A data

### Agent Pattern

All agents inherit from `BaseAgent`:

```python
class BaseAgent:
    def call_llm(self, system, messages, **kwargs):
        # LLM call with tracking
        # Token counting
        # Error handling
        pass
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
- `GET /api/agents/initiatives/{id}/mrd/content` - Get MRD markdown
- `POST /api/agents/initiatives/{id}/mrd/fine-tune` - Fine-tune MRD section
- `POST /api/agents/initiatives/{id}/calculate-scores` - Calculate scores
- `GET /api/agents/initiatives/{id}/scores` - Get scores
- `GET /api/agents/initiatives/{id}/scores/pdf` - Export scorecard PDF
- `GET /api/agents/initiatives/{id}/evaluate-readiness` - Check readiness

### Context
- `GET /api/context` - Get organization context
- `PUT /api/context` - Update context

## Development Guidelines

### Backend

1. **Repository Pattern** - All database access through repositories
2. **Schema Validation** - Use Pydantic for all I/O
3. **Error Handling** - Proper HTTP exceptions
4. **Authentication** - Session-based auth with dependency injection
5. **Multi-tenancy** - Always filter by organization_id

### Frontend

1. **Component Structure** - Functional components with hooks
2. **Data Fetching** - Use TanStack Query (useQuery/useMutation)
3. **State Management** - React Context for global state
4. **Styling** - Material-UI components and sx prop
5. **Routing** - React Router with protected routes

### Testing

1. **Backend** - pytest with fixtures
2. **Frontend** - React Testing Library
3. **Integration** - End-to-end API tests
4. **AI Agents** - Mock LLM responses

## Configuration

### Environment Variables

**Backend:**
- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - JWT secret key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `ANTHROPIC_MODEL` - Claude model to use
- `CORS_ORIGINS` - Allowed frontend origins

**Frontend:**
- `VITE_API_BASE_URL` - Backend API URL

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Deployment

### Production Checklist

- [ ] Use PostgreSQL (not SQLite)
- [ ] Set strong SECRET_KEY
- [ ] Configure CORS origins
- [ ] Use environment variables (not .env)
- [ ] Enable HTTPS
- [ ] Use Gunicorn with Uvicorn workers
- [ ] Set up logging
- [ ] Configure rate limiting
- [ ] Set up monitoring
- [ ] Back up database regularly
