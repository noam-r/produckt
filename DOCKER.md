# ProDuckt Docker Guide

Complete guide for running ProDuckt using Docker and Docker Compose.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Development Workflow](#development-workflow)
- [Production Deployment](#production-deployment)
- [Local Customization](#local-customization)
- [Common Commands](#common-commands)
- [Database Management](#database-management)
- [Troubleshooting](#troubleshooting)
- [Architecture Overview](#architecture-overview)
- [Configuration Reference](#configuration-reference)

---

## Quick Start

Get ProDuckt running with a single command:

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and SECRET_KEY (use: openssl rand -hex 32)

# 2. Start all services
docker-compose up
```

That's it! Access ProDuckt at http://localhost:5173

**Default credentials:** `admin@produckt.local` / `Admin123!` (change on first login)

---

## Prerequisites

### Required Software

- **Docker** 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ (included with Docker Desktop)

### Verify Installation

```bash
docker --version
# Docker version 20.10.0 or higher

docker-compose --version
# Docker Compose version 2.0.0 or higher
```

### Required Configuration

You need an Anthropic API key to use ProDuckt's AI features:

1. Get your API key from [Anthropic Console](https://console.anthropic.com/)
2. Copy `.env.example` to `.env`
3. Set `ANTHROPIC_API_KEY` in your `.env` file
4. Generate a secure `SECRET_KEY`: `openssl rand -hex 32`

**That's all you need!** No Python, Node.js, or system libraries required on your host machine.

---

## Development Workflow

### Starting Development Environment

```bash
# Start all services with hot-reload enabled
docker-compose up

# Or run in background (detached mode)
docker-compose up -d
```

The development environment includes:
- ✓ Backend hot-reload (code changes auto-restart server)
- ✓ Frontend hot-reload (code changes auto-refresh browser)
- ✓ Debug logging enabled
- ✓ Source code mounted as volumes
- ✓ Interactive API documentation at http://localhost:8000/docs

### Viewing Logs

```bash
# View logs from all services
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View logs from specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# View last 100 lines
docker-compose logs --tail=100
```

### Making Code Changes

**Backend changes:**
1. Edit files in `./backend/`
2. Uvicorn automatically detects changes and reloads
3. Changes appear within 2-3 seconds

**Frontend changes:**
1. Edit files in `./frontend/src/`
2. Vite detects changes and triggers HMR (Hot Module Replacement)
3. Browser automatically refreshes within 1-2 seconds

### Running Commands Inside Containers

```bash
# Execute Python commands in backend
docker-compose exec backend python scripts/init_db.py
docker-compose exec backend alembic upgrade head

# Open Python shell
docker-compose exec backend python

# Open bash shell in backend container
docker-compose exec backend bash

# Install new Python package
docker-compose exec backend pip install package-name
# Then add to requirements.txt and rebuild: docker-compose build backend

# Install new npm package in frontend
docker-compose exec frontend npm install package-name
# Then rebuild: docker-compose build frontend
```

### Debugging

**Backend debugging:**
```bash
# View detailed logs with stack traces
docker-compose logs -f backend

# Check backend health
curl http://localhost:8000/health

# Access interactive API docs
open http://localhost:8000/docs
```

**Frontend debugging:**
```bash
# View build output and errors
docker-compose logs -f frontend

# Check if frontend is serving
curl http://localhost:5173
```

### Stopping Services

```bash
# Stop all services (keeps containers and volumes)
docker-compose stop

# Stop and remove containers (keeps volumes)
docker-compose down

# Stop, remove containers, and remove volumes (DELETES DATA)
docker-compose down -v
```

---

## Production Deployment

### Building Production Images

```bash
# Build optimized production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start production services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Production Features

The production configuration includes:
- ✓ Multi-stage builds for smaller images
- ✓ Gunicorn with Uvicorn workers (4 workers)
- ✓ Nginx serving optimized static assets
- ✓ Gzip compression enabled
- ✓ Resource limits enforced
- ✓ Security headers configured
- ✓ Health checks and auto-restart
- ✓ Production logging (INFO level)

### Production Best Practices

**1. Use PostgreSQL instead of SQLite:**

```env
# In .env file
DATABASE_URL=postgresql://produck:password@db:5432/produck
```

Uncomment the `db` service in `docker-compose.yml` to enable PostgreSQL.

**2. Set strong secrets:**

```bash
# Generate secure SECRET_KEY
openssl rand -hex 32

# Set in .env
SECRET_KEY=your-generated-key-here
```

**3. Configure resource limits:**

Edit `docker-compose.prod.yml` to adjust memory and CPU limits:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
```

**4. Enable HTTPS:**

Use a reverse proxy (Nginx, Traefik, Caddy) in front of Docker Compose:

```yaml
# Example with Traefik labels
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.produck.rule=Host(`produck.example.com`)"
  - "traefik.http.routers.produck.tls.certresolver=letsencrypt"
```

**5. Set up monitoring:**

```bash
# View service health status
docker-compose ps

# Monitor resource usage
docker stats

# Check disk usage
docker system df
```

### Production Environment Variables

```env
# Production settings
ENVIRONMENT=production
LOG_LEVEL=INFO
BUILD_TARGET=production

# Security
SECRET_KEY=your-strong-secret-key
SECURE_COOKIES=true

# Database (use PostgreSQL in production)
DATABASE_URL=postgresql://produck:password@db:5432/produck

# AI Service
ANTHROPIC_API_KEY=your-api-key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

---

## Local Customization

### Using docker-compose.override.yml

Docker Compose automatically applies `docker-compose.override.yml` if it exists, allowing you to customize the configuration for your local environment without modifying the main compose files.

**Create your override file:**

```bash
# Copy the example template
cp docker-compose.override.yml.example docker-compose.override.yml

# Edit with your customizations
nano docker-compose.override.yml
```

**Common use cases:**

**1. Change ports to avoid conflicts:**
```yaml
services:
  backend:
    ports:
      - "8888:8000"
  frontend:
    ports:
      - "3000:5173"
    environment:
      - VITE_API_BASE_URL=http://localhost:8888
```

**2. Add debug logging:**
```yaml
services:
  backend:
    environment:
      - LOG_LEVEL=DEBUG
      - PYTHONUNBUFFERED=1
```

**3. Mount additional volumes:**
```yaml
services:
  backend:
    volumes:
      - ./local-data:/app/local-data
      - ./custom-config.yml:/app/config.yml:ro
```

**4. Add development tools:**
```yaml
services:
  adminer:
    image: adminer:latest
    ports:
      - "8080:8080"
    networks:
      - produck-network
```

**5. Use external database:**
```yaml
services:
  backend:
    environment:
      - DATABASE_URL=postgresql://user:pass@external-db.example.com:5432/produck
  db:
    profiles:
      - disabled  # Prevents db service from starting
```

**6. Adjust resource limits:**
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

**Benefits:**
- ✓ Customize without modifying tracked files
- ✓ Each developer can have their own configuration
- ✓ Automatically applied by `docker-compose up`
- ✓ Gitignored by default (won't be committed)

**See more examples** in `docker-compose.override.yml.example`

---

## Common Commands

### Service Management

```bash
# Start services
docker-compose up                    # Foreground (see logs)
docker-compose up -d                 # Background (detached)

# Stop services
docker-compose stop                  # Stop containers
docker-compose down                  # Stop and remove containers
docker-compose down -v               # Stop, remove containers and volumes

# Restart services
docker-compose restart               # Restart all services
docker-compose restart backend       # Restart specific service

# View status
docker-compose ps                    # List containers and health status
docker stats                         # Real-time resource usage
```

### Building and Updating

```bash
# Build images
docker-compose build                 # Build all services
docker-compose build backend         # Build specific service
docker-compose build --no-cache      # Build without cache (clean build)

# Pull latest base images
docker-compose pull

# Rebuild and restart
docker-compose up -d --build         # Rebuild and restart in background
```

### Logs and Debugging

```bash
# View logs
docker-compose logs                  # All services
docker-compose logs -f               # Follow logs (real-time)
docker-compose logs -f backend       # Follow specific service
docker-compose logs --tail=50        # Last 50 lines
docker-compose logs --since 10m      # Last 10 minutes

# Execute commands
docker-compose exec backend bash     # Open shell in backend
docker-compose exec backend python   # Open Python REPL
docker-compose run backend pytest    # Run one-off command
```

### Cleanup

```bash
# Remove stopped containers
docker-compose rm

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Remove everything (CAUTION: deletes all Docker data)
docker system prune -a --volumes
```

---

## Database Management

### Migrations

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# View migration history
docker-compose exec backend alembic history

# Rollback one migration
docker-compose exec backend alembic downgrade -1
```

### Database Initialization

```bash
# Initialize database with roles and admin user
docker-compose exec backend python scripts/init_db.py

# Seed additional data
docker-compose exec backend python scripts/seed_db.py
```

### Backup and Restore

**SQLite (default):**

```bash
# Backup database
docker-compose exec backend cp /app/data/produck.db /app/data/produck.db.backup
docker cp $(docker-compose ps -q backend):/app/data/produck.db ./backup-$(date +%Y%m%d).db

# Restore database
docker cp ./backup-20241120.db $(docker-compose ps -q backend):/app/data/produck.db
docker-compose restart backend
```

**PostgreSQL:**

```bash
# Backup database
docker-compose exec db pg_dump -U produck produck > backup-$(date +%Y%m%d).sql

# Restore database
docker-compose exec -T db psql -U produck produck < backup-20241120.sql
```

### Switching to PostgreSQL

1. **Uncomment PostgreSQL service** in `docker-compose.yml`

2. **Update `.env` file:**
```env
DATABASE_URL=postgresql://produck:password@db:5432/produck
DB_PASSWORD=your-secure-password
```

3. **Restart services:**
```bash
docker-compose down
docker-compose up -d
```

4. **Initialize database:**
```bash
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/init_db.py
```

---

## Migration and Rollback

### Migrating from Manual Setup to Docker

If you're currently running ProDuckt with a manual setup (Python virtual environment, npm, etc.), follow these steps to migrate to Docker.

#### Pre-Migration Checklist

Before starting the migration:

1. ✓ Ensure your current setup is working correctly
2. ✓ Backup your database (see backup procedures below)
3. ✓ Note any custom configuration or environment variables
4. ✓ Commit any uncommitted code changes
5. ✓ Have Docker and Docker Compose installed

#### Step-by-Step Migration Guide

**Step 1: Backup Your Current Data**

```bash
# Backup SQLite database
cp produck.db produck.db.backup-$(date +%Y%m%d-%H%M%S)

# Backup any uploaded files or custom data
tar -czf data-backup-$(date +%Y%m%d-%H%M%S).tar.gz produck.db data/ uploads/

# Store backup in safe location
mkdir -p ~/backups/produck
mv produck.db.backup-* ~/backups/produck/
mv data-backup-*.tar.gz ~/backups/produck/
```

**Step 2: Verify Current Setup**

```bash
# Test that your current setup works
./start.sh

# Verify you can access the application
curl http://localhost:8000/health
curl http://localhost:5173

# Stop the manual setup
# Press Ctrl+C or kill the processes
```

**Step 3: Prepare Docker Configuration**

```bash
# Copy environment configuration
cp .env.example .env

# Edit .env with your existing configuration
nano .env

# Important: Copy these values from your current setup:
# - ANTHROPIC_API_KEY
# - SECRET_KEY
# - Any custom DATABASE_URL or other settings
```

**Step 4: Build Docker Images**

```bash
# Build all Docker images
docker-compose build

# This may take 5-10 minutes on first build
# Subsequent builds will be faster due to caching
```

**Step 5: Migrate Database to Docker**

**Option A: Start fresh with Docker (recommended for testing)**

```bash
# Start Docker services
docker-compose up -d

# Database will be automatically initialized
# Default admin user will be created
```

**Option B: Copy existing database into Docker**

```bash
# Start Docker services
docker-compose up -d

# Wait for services to be healthy
sleep 10

# Stop backend to safely copy database
docker-compose stop backend

# Copy your existing database into the Docker volume
docker cp produck.db $(docker-compose ps -q backend):/app/data/produck.db

# Set correct permissions
docker-compose run --rm backend chown appuser:appuser /app/data/produck.db

# Start backend again
docker-compose start backend
```

**Option C: Migrate to PostgreSQL (recommended for production)**

```bash
# 1. Export data from SQLite
sqlite3 produck.db .dump > produck-dump.sql

# 2. Enable PostgreSQL in docker-compose.yml (uncomment db service)

# 3. Update .env
echo "DATABASE_URL=postgresql://produck:password@db:5432/produck" >> .env
echo "DB_PASSWORD=your-secure-password" >> .env

# 4. Start services
docker-compose up -d

# 5. Wait for PostgreSQL to be ready
sleep 15

# 6. Import data (you may need to clean up the dump file first)
# Note: Direct SQLite to PostgreSQL migration requires data transformation
# Consider using a migration tool or starting fresh with PostgreSQL
docker-compose exec -T db psql -U produck produck < produck-dump.sql
```

**Step 6: Verify Docker Setup**

```bash
# Check all services are running and healthy
docker-compose ps

# Should show:
# - backend: Up (healthy)
# - frontend: Up (healthy)
# - db: Up (healthy) [if using PostgreSQL]

# Test backend
curl http://localhost:8000/health
# Should return: {"status":"healthy","database":"connected"}

# Test frontend
curl http://localhost:5173
# Should return HTML

# View logs to check for errors
docker-compose logs --tail=50

# Try logging in
open http://localhost:5173
```

**Step 7: Test Application Functionality**

1. Log in with your existing credentials
2. Verify your initiatives and data are present
3. Create a test initiative
4. Generate an MRD
5. Check that all features work as expected

**Step 8: Update Your Workflow**

```bash
# Old workflow (manual setup)
./start.sh                    # Start application
source venv/bin/activate      # Activate Python environment
cd frontend && npm run dev    # Start frontend

# New workflow (Docker)
docker-compose up             # Start everything
docker-compose logs -f        # View logs
docker-compose down           # Stop everything
```

**Step 9: Clean Up Old Setup (Optional)**

Once you've verified Docker works correctly:

```bash
# Deactivate and remove Python virtual environment
deactivate
rm -rf venv/

# Remove node_modules (will be in Docker container)
rm -rf frontend/node_modules/

# Keep your backup files in ~/backups/produck/
```

#### Migration Troubleshooting

**Problem: Database file not found in Docker**

```bash
# Check if database exists in container
docker-compose exec backend ls -la /app/data/

# If missing, copy it again
docker-compose stop backend
docker cp produck.db $(docker-compose ps -q backend):/app/data/produck.db
docker-compose start backend
```

**Problem: Permission denied errors**

```bash
# Fix ownership of data directory
docker-compose exec backend chown -R appuser:appuser /app/data/
docker-compose restart backend
```

**Problem: Database schema mismatch**

```bash
# Run migrations to update schema
docker-compose exec backend alembic upgrade head
```

**Problem: Missing environment variables**

```bash
# Check what environment variables are set
docker-compose exec backend env | grep -E "ANTHROPIC|SECRET|DATABASE"

# Update .env file and restart
nano .env
docker-compose restart
```

### Rollback Procedures

If you encounter issues with Docker and need to rollback to your manual setup:

#### Quick Rollback (Emergency)

```bash
# 1. Stop Docker services
docker-compose down

# 2. Restore database backup
cp ~/backups/produck/produck.db.backup-YYYYMMDD-HHMMSS produck.db

# 3. Start manual setup
./start.sh

# Your application should now be running as before
```

#### Complete Rollback with Data Recovery

**Step 1: Stop Docker Services**

```bash
# Stop all Docker services
docker-compose down

# Optionally, remove volumes (if you want to clean up)
# WARNING: This deletes Docker data
# docker-compose down -v
```

**Step 2: Extract Data from Docker (if needed)**

```bash
# If you made changes in Docker that you want to keep:

# Get the backend container ID (even if stopped)
CONTAINER_ID=$(docker-compose ps -q backend)

# Copy database from Docker volume
docker cp $CONTAINER_ID:/app/data/produck.db ./produck-from-docker.db

# Or if container is removed, extract from volume
docker run --rm -v produck-data:/data -v $(pwd):/backup alpine \
  cp /data/produck.db /backup/produck-from-docker.db
```

**Step 3: Restore Manual Setup**

```bash
# Restore your Python virtual environment (if removed)
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Restore frontend dependencies (if removed)
cd frontend
npm install
cd ..

# Restore database
cp ~/backups/produck/produck.db.backup-YYYYMMDD-HHMMSS produck.db
# Or use the Docker version if you want recent changes
# cp produck-from-docker.db produck.db

# Verify .env file has correct settings for manual setup
nano .env
# Ensure DATABASE_URL points to local file:
# DATABASE_URL=sqlite:///./produck.db
```

**Step 4: Start Manual Setup**

```bash
# Start the application
./start.sh

# Or start services separately:
# Terminal 1: Backend
source venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

**Step 5: Verify Rollback**

```bash
# Test backend
curl http://localhost:8000/health

# Test frontend
curl http://localhost:5173

# Log in and verify your data
open http://localhost:5173
```

### Backup and Restore Procedures

#### Automated Backup Scripts

Use the provided backup scripts for easy data management:

**Backup:**
```bash
# Backup all Docker data (database, volumes, configuration)
./scripts/backup-docker.sh

# Creates timestamped backup in ./backups/
# Example: backups/produck-backup-20241123-143022.tar.gz
```

**Restore:**
```bash
# Restore from a backup file
./scripts/restore-docker.sh backups/produck-backup-20241123-143022.tar.gz

# This will:
# 1. Stop running services
# 2. Restore database and volumes
# 3. Restart services
```

#### Manual Backup Procedures

**SQLite Backup (Default):**

```bash
# Method 1: Copy database file from running container
docker-compose exec backend cp /app/data/produck.db /app/data/produck.db.backup
docker cp $(docker-compose ps -q backend):/app/data/produck.db.backup \
  ./backup-$(date +%Y%m%d-%H%M%S).db

# Method 2: Use SQLite backup command
docker-compose exec backend sqlite3 /app/data/produck.db \
  ".backup /app/data/backup-$(date +%Y%m%d).db"
docker cp $(docker-compose ps -q backend):/app/data/backup-*.db ./

# Method 3: Backup entire volume
docker run --rm \
  -v produck-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/produck-data-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

**PostgreSQL Backup:**

```bash
# Method 1: pg_dump (recommended)
docker-compose exec db pg_dump -U produck produck > \
  backup-postgres-$(date +%Y%m%d-%H%M%S).sql

# Method 2: pg_dumpall (includes all databases and roles)
docker-compose exec db pg_dumpall -U produck > \
  backup-postgres-all-$(date +%Y%m%d-%H%M%S).sql

# Method 3: Backup volume
docker run --rm \
  -v postgres-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres-data-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

**Configuration Backup:**

```bash
# Backup environment and compose files
tar czf config-backup-$(date +%Y%m%d-%H%M%S).tar.gz \
  .env \
  docker-compose.yml \
  docker-compose.override.yml \
  docker-compose.dev.yml \
  docker-compose.prod.yml
```

#### Manual Restore Procedures

**SQLite Restore:**

```bash
# Stop backend to prevent database locks
docker-compose stop backend

# Method 1: Copy backup file into container
docker cp ./backup-20241123-143022.db \
  $(docker-compose ps -q backend):/app/data/produck.db

# Method 2: Restore from volume backup
docker run --rm \
  -v produck-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/produck-data-20241123-143022.tar.gz -C /data

# Fix permissions
docker-compose run --rm backend chown -R appuser:appuser /app/data/

# Start backend
docker-compose start backend

# Verify restore
docker-compose exec backend ls -lh /app/data/produck.db
curl http://localhost:8000/health
```

**PostgreSQL Restore:**

```bash
# Stop backend to prevent connections
docker-compose stop backend

# Method 1: Restore from SQL dump
docker-compose exec -T db psql -U produck produck < backup-postgres-20241123-143022.sql

# Method 2: Drop and recreate database (clean restore)
docker-compose exec db psql -U produck -c "DROP DATABASE IF EXISTS produck;"
docker-compose exec db psql -U produck -c "CREATE DATABASE produck;"
docker-compose exec -T db psql -U produck produck < backup-postgres-20241123-143022.sql

# Method 3: Restore from volume backup
docker-compose down
docker run --rm \
  -v postgres-data:/data \
  -v $(pwd)/backups:/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/postgres-data-20241123-143022.tar.gz -C /data"
docker-compose up -d

# Start backend
docker-compose start backend

# Verify restore
docker-compose exec db psql -U produck produck -c "SELECT COUNT(*) FROM users;"
curl http://localhost:8000/health
```

**Configuration Restore:**

```bash
# Extract configuration backup
tar xzf config-backup-20241123-143022.tar.gz

# Review and merge changes if needed
diff .env .env.backup
diff docker-compose.override.yml docker-compose.override.yml.backup

# Restart services with restored configuration
docker-compose down
docker-compose up -d
```

#### Backup Best Practices

1. **Regular Backups:**
   ```bash
   # Add to crontab for daily backups
   0 2 * * * cd /path/to/produck && ./scripts/backup-docker.sh
   ```

2. **Backup Before Updates:**
   ```bash
   # Always backup before pulling updates
   ./scripts/backup-docker.sh
   git pull
   docker-compose build
   docker-compose up -d
   ```

3. **Test Restores:**
   ```bash
   # Periodically test that backups can be restored
   # Use a separate test environment
   ```

4. **Off-Site Backups:**
   ```bash
   # Copy backups to remote location
   rsync -avz backups/ user@backup-server:/backups/produck/
   
   # Or use cloud storage
   aws s3 sync backups/ s3://my-bucket/produck-backups/
   ```

5. **Retention Policy:**
   ```bash
   # Keep last 7 daily backups, 4 weekly, 12 monthly
   # Use backup rotation script or tools like restic
   ```

#### Disaster Recovery

**Complete System Recovery:**

```bash
# 1. Install Docker on new system
# 2. Clone repository
git clone https://github.com/noam-r/produckt.git
cd produckt

# 3. Restore configuration
tar xzf config-backup-20241123-143022.tar.gz

# 4. Build images
docker-compose build

# 5. Restore data (before starting services)
./scripts/restore-docker.sh backups/produck-backup-20241123-143022.tar.gz

# 6. Start services
docker-compose up -d

# 7. Verify
docker-compose ps
curl http://localhost:8000/health
```

---

## Troubleshooting

### Services Won't Start

**Problem:** `docker-compose up` fails or services exit immediately

**Solutions:**

1. **Check logs for errors:**
```bash
docker-compose logs backend
docker-compose logs frontend
```

2. **Verify environment variables:**
```bash
# Check .env file exists and has required variables
cat .env | grep ANTHROPIC_API_KEY
cat .env | grep SECRET_KEY
```

3. **Check port conflicts:**
```bash
# Check if ports 8000 or 5173 are already in use
lsof -i :8000
lsof -i :5173

# Or on Linux
netstat -tulpn | grep 8000
netstat -tulpn | grep 5173
```

4. **Rebuild containers:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Backend Health Check Failing

**Problem:** Backend container shows as "unhealthy"

**Solutions:**

1. **Check backend logs:**
```bash
docker-compose logs backend
```

2. **Test health endpoint manually:**
```bash
docker-compose exec backend curl http://localhost:8000/health
```

3. **Check database connection:**
```bash
docker-compose exec backend python -c "from backend.database import engine; engine.connect()"
```

4. **Verify ANTHROPIC_API_KEY is set:**
```bash
docker-compose exec backend env | grep ANTHROPIC
```

### Frontend Not Loading

**Problem:** http://localhost:5173 shows error or blank page

**Solutions:**

1. **Check frontend logs:**
```bash
docker-compose logs frontend
```

2. **Verify frontend is running:**
```bash
curl http://localhost:5173
```

3. **Check if backend is accessible:**
```bash
curl http://localhost:8000/health
```

4. **Rebuild frontend:**
```bash
docker-compose build frontend
docker-compose restart frontend
```

### Hot Reload Not Working

**Problem:** Code changes don't trigger automatic reload

**Solutions:**

1. **Verify volumes are mounted:**
```bash
docker-compose config | grep volumes
```

2. **Check file permissions:**
```bash
ls -la backend/
ls -la frontend/
```

3. **Restart services:**
```bash
docker-compose restart
```

4. **For Windows/WSL2 users:**
   - Ensure code is in WSL2 filesystem, not Windows filesystem
   - Or add `CHOKIDAR_USEPOLLING=true` to frontend environment

### Database Connection Errors

**Problem:** Backend can't connect to database

**Solutions:**

1. **Check DATABASE_URL format:**
```bash
docker-compose exec backend env | grep DATABASE_URL
```

2. **For PostgreSQL, verify service is healthy:**
```bash
docker-compose ps db
docker-compose logs db
```

3. **Test database connection:**
```bash
# SQLite
docker-compose exec backend ls -la /app/data/

# PostgreSQL
docker-compose exec db psql -U produck -d produck -c "SELECT 1;"
```

4. **Reset database:**
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/init_db.py
```

### Permission Denied Errors

**Problem:** Permission errors when accessing files or volumes

**Solutions:**

1. **Check volume permissions:**
```bash
docker-compose exec backend ls -la /app/data/
```

2. **Fix ownership (if needed):**
```bash
docker-compose exec backend chown -R appuser:appuser /app/data/
```

3. **On Linux, check SELinux:**
```bash
# Add :z flag to volume mounts in docker-compose.yml
volumes:
  - ./backend:/app/backend:z
```

### Out of Disk Space

**Problem:** Docker runs out of disk space

**Solutions:**

1. **Check disk usage:**
```bash
docker system df
```

2. **Clean up unused resources:**
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything (CAUTION)
docker system prune -a --volumes
```

3. **Check volume sizes:**
```bash
docker volume ls
docker volume inspect produck-data
```

### Container Keeps Restarting

**Problem:** Container restarts in a loop

**Solutions:**

1. **Check logs for crash reason:**
```bash
docker-compose logs --tail=100 backend
```

2. **Disable restart policy temporarily:**
```bash
# Edit docker-compose.yml, change restart: always to restart: "no"
docker-compose up
```

3. **Run container interactively:**
```bash
docker-compose run backend bash
# Then manually run the startup command to see errors
```

### Network Issues

**Problem:** Services can't communicate with each other

**Solutions:**

1. **Verify network exists:**
```bash
docker network ls | grep produck
```

2. **Check service connectivity:**
```bash
docker-compose exec frontend ping backend
docker-compose exec backend ping db
```

3. **Recreate network:**
```bash
docker-compose down
docker network prune
docker-compose up
```

### Build Failures

**Problem:** `docker-compose build` fails

**Solutions:**

1. **Check Docker daemon is running:**
```bash
docker info
```

2. **Clear build cache:**
```bash
docker builder prune
docker-compose build --no-cache
```

3. **Check .dockerignore isn't excluding required files:**
```bash
cat .dockerignore
cat frontend/.dockerignore
```

4. **Ensure base images are accessible:**
```bash
docker pull python:3.11-slim
docker pull node:20-alpine
```

---

## Architecture Overview

### Container Structure

```
┌─────────────────────────────────────────────────────────────┐
│                        Host Machine                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Docker Compose Network                     │ │
│  │                                                          │ │
│  │  ┌──────────────┐    ┌──────────────┐   ┌───────────┐ │ │
│  │  │   Frontend   │───▶│   Backend    │──▶│ Database  │ │ │
│  │  │   (React)    │    │   (FastAPI)  │   │ (SQLite/  │ │ │
│  │  │   Port 5173  │    │   Port 8000  │   │  Postgres)│ │ │
│  │  └──────────────┘    └──────────────┘   └───────────┘ │ │
│  │         │                    │                  │       │ │
│  │         │                    │                  │       │ │
│  │    [Volume:src]        [Volume:src]      [Volume:data] │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  User Access: http://localhost:5173                         │
└─────────────────────────────────────────────────────────────┘
```

### Services

**Backend (FastAPI):**
- Base image: `python:3.11-slim`
- Port: 8000
- Development: Uvicorn with --reload
- Production: Gunicorn with 4 Uvicorn workers
- Volumes: Source code (dev), database (prod)

**Frontend (React + Vite):**
- Base image: `node:20-alpine` (dev), `nginx:alpine` (prod)
- Port: 5173 (dev), 80 mapped to 5173 (prod)
- Development: Vite dev server with HMR
- Production: Nginx serving static assets
- Volumes: Source code and node_modules (dev only)

**Database (Optional PostgreSQL):**
- Base image: `postgres:15-alpine`
- Port: 5432 (internal only)
- Volume: Persistent data storage
- Default: SQLite in backend container

### Volumes

- `produck-data` - Database and uploaded files
- `postgres-data` - PostgreSQL data (if using PostgreSQL)
- Development: Source code mounted for hot-reload

### Networks

- `produck-network` - Private bridge network for inter-service communication

---

## Configuration Reference

### Environment Variables

**Application:**
```env
ENVIRONMENT=development              # development or production
SECRET_KEY=your-secret-key          # Session signing key (required)
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR
```

**Database:**
```env
DATABASE_URL=sqlite:///./data/produck.db                    # SQLite (default)
# DATABASE_URL=postgresql://produck:password@db:5432/produck  # PostgreSQL
DB_PASSWORD=your-db-password        # PostgreSQL password (if using PostgreSQL)
```

**AI Service:**
```env
ANTHROPIC_API_KEY=sk-ant-...        # Required for AI features
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

**Frontend:**
```env
VITE_API_BASE_URL=http://localhost:8000
NODE_ENV=development                # development or production
```

**Docker Build:**
```env
BUILD_TARGET=development            # development or production
```

### Docker Compose Files

- `docker-compose.yml` - Base configuration for all environments
- `docker-compose.dev.yml` - Development overrides (hot-reload, volumes)
- `docker-compose.prod.yml` - Production overrides (optimization, limits)

**Usage:**
```bash
# Development (default)
docker-compose up

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

### Resource Limits (Production)

Default limits in `docker-compose.prod.yml`:

- **Backend:** 1 CPU, 1GB RAM
- **Frontend:** 0.5 CPU, 512MB RAM  
- **PostgreSQL:** 1 CPU, 2GB RAM

Adjust in `docker-compose.prod.yml` or override with environment variables.

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [ProDuckt README](README.md)
- [ProDuckt Project Structure](PROJECT_STRUCTURE.md)

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/noam-r/produckt/issues)
- **Discussions:** [GitHub Discussions](https://github.com/noam-r/produckt/discussions)

---

**Happy Dockering! 🐳**
