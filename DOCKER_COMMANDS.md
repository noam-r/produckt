# Docker Compose Command Reference

Quick reference guide for common Docker Compose commands used with ProDuckt.

## Table of Contents

- [Service Management](#service-management)
- [Development Usage](#development-usage)
- [Production Usage](#production-usage)
- [Database Management](#database-management)
- [Logs and Debugging](#logs-and-debugging)
- [Building and Updating](#building-and-updating)
- [Cleanup and Maintenance](#cleanup-and-maintenance)
- [Troubleshooting Commands](#troubleshooting-commands)

---

## Service Management

### Starting Services

```bash
# Start all services in foreground (see logs in terminal)
docker-compose up

# Start all services in background (detached mode)
docker-compose up -d

# Start specific service only
docker-compose up backend
docker-compose up frontend

# Start with rebuild (if Dockerfile or dependencies changed)
docker-compose up --build

# Start and force recreate containers
docker-compose up --force-recreate
```

### Stopping Services

```bash
# Stop all running services (keeps containers)
docker-compose stop

# Stop specific service
docker-compose stop backend
docker-compose stop frontend

# Stop and remove containers (keeps volumes and images)
docker-compose down

# Stop, remove containers AND volumes (DELETES DATA!)
docker-compose down -v

# Stop, remove containers, volumes, and images
docker-compose down -v --rmi all
```

### Restarting Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart backend
docker-compose restart frontend

# Restart with rebuild
docker-compose down
docker-compose up -d --build
```

### Viewing Service Status

```bash
# List all containers with status and health
docker-compose ps

# List all containers (including stopped)
docker-compose ps -a

# View real-time resource usage (CPU, memory, network, disk)
docker stats

# View detailed container information
docker-compose ps --format json
docker inspect $(docker-compose ps -q backend)
```

---

## Development Usage

### Starting Development Environment

```bash
# Start with development configuration (default)
docker-compose up

# Start in background
docker-compose up -d

# View logs while running in background
docker-compose logs -f
```

### Hot Reload Development

```bash
# Start services with source code mounted for hot reload
docker-compose up

# Backend changes auto-reload (Uvicorn --reload)
# Frontend changes auto-refresh (Vite HMR)

# If hot reload stops working, restart services
docker-compose restart
```

### Running Commands in Development

```bash
# Execute Python commands in backend
docker-compose exec backend python scripts/init_db.py
docker-compose exec backend alembic upgrade head
docker-compose exec backend pytest

# Open Python REPL
docker-compose exec backend python

# Open bash shell in backend
docker-compose exec backend bash

# Execute npm commands in frontend
docker-compose exec frontend npm install package-name
docker-compose exec frontend npm run build

# Open shell in frontend
docker-compose exec frontend sh
```

### Installing New Dependencies

```bash
# Install Python package
docker-compose exec backend pip install package-name
# Then add to requirements.txt and rebuild
echo "package-name==1.0.0" >> requirements.txt
docker-compose build backend

# Install npm package
docker-compose exec frontend npm install package-name
# Then rebuild
docker-compose build frontend

# Or rebuild all services
docker-compose build
```

---

## Production Usage

### Building Production Images

```bash
# Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Build with no cache (clean build)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache

# Build specific service
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build backend
```

### Starting Production Services

```bash
# Start production services in background
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View production logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Check production service status
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

### Stopping Production Services

```bash
# Stop production services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Stop and remove volumes (CAUTION: deletes data)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down -v
```

### Production Deployment Workflow

```bash
# 1. Pull latest code
git pull origin main

# 2. Update environment variables if needed
nano .env

# 3. Build new images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# 4. Stop old containers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# 5. Start new containers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 6. Verify services are healthy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 7. Check logs for errors
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100
```

---

## Database Management

### Running Migrations

```bash
# Run all pending migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# View migration history
docker-compose exec backend alembic history

# View current migration version
docker-compose exec backend alembic current

# Rollback one migration
docker-compose exec backend alembic downgrade -1

# Rollback to specific version
docker-compose exec backend alembic downgrade <revision_id>
```

### Database Initialization

```bash
# Initialize database with roles and admin user
docker-compose exec backend python scripts/init_db.py

# Seed additional test data
docker-compose exec backend python scripts/seed_db.py

# Reset database completely
docker-compose down -v
docker-compose up -d
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/init_db.py
```

### Backup and Restore

**SQLite (default):**

```bash
# Backup database from container to host
docker cp $(docker-compose ps -q backend):/app/data/produck.db ./backup-$(date +%Y%m%d-%H%M%S).db

# Restore database from host to container
docker cp ./backup-20241120-143000.db $(docker-compose ps -q backend):/app/data/produck.db
docker-compose restart backend

# Create backup inside container
docker-compose exec backend cp /app/data/produck.db /app/data/produck.db.backup

# List backups
docker-compose exec backend ls -lh /app/data/*.backup
```

**PostgreSQL:**

```bash
# Backup PostgreSQL database
docker-compose exec db pg_dump -U produck produck > backup-$(date +%Y%m%d-%H%M%S).sql

# Backup with compression
docker-compose exec db pg_dump -U produck produck | gzip > backup-$(date +%Y%m%d-%H%M%S).sql.gz

# Restore PostgreSQL database
docker-compose exec -T db psql -U produck produck < backup-20241120-143000.sql

# Restore from compressed backup
gunzip -c backup-20241120-143000.sql.gz | docker-compose exec -T db psql -U produck produck

# Create database dump with custom format (faster restore)
docker-compose exec db pg_dump -U produck -Fc produck > backup-$(date +%Y%m%d-%H%M%S).dump

# Restore from custom format
docker-compose exec -T db pg_restore -U produck -d produck < backup-20241120-143000.dump
```

### Database Access

```bash
# Access SQLite database
docker-compose exec backend sqlite3 /app/data/produck.db

# Access PostgreSQL database
docker-compose exec db psql -U produck produck

# Run SQL query directly
docker-compose exec backend sqlite3 /app/data/produck.db "SELECT * FROM users;"
docker-compose exec db psql -U produck produck -c "SELECT * FROM users;"

# Export query results to CSV
docker-compose exec db psql -U produck produck -c "COPY (SELECT * FROM users) TO STDOUT CSV HEADER" > users.csv
```

---

## Logs and Debugging

### Viewing Logs

```bash
# View logs from all services
docker-compose logs

# Follow logs in real-time (like tail -f)
docker-compose logs -f

# View logs from specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs db

# Follow logs from specific service
docker-compose logs -f backend

# View last N lines of logs
docker-compose logs --tail=50
docker-compose logs --tail=100 backend

# View logs since specific time
docker-compose logs --since 10m        # Last 10 minutes
docker-compose logs --since 1h         # Last hour
docker-compose logs --since 2024-11-20 # Since specific date

# View logs with timestamps
docker-compose logs -t

# Combine options
docker-compose logs -f --tail=50 -t backend
```

### Debugging Services

```bash
# Check service health status
docker-compose ps

# Test backend health endpoint
docker-compose exec backend curl http://localhost:8000/health
curl http://localhost:8000/health

# Test frontend
curl http://localhost:5173

# View container resource usage
docker stats

# Inspect container configuration
docker inspect $(docker-compose ps -q backend)

# View container processes
docker-compose top
docker-compose top backend

# View container environment variables
docker-compose exec backend env
docker-compose exec backend env | grep ANTHROPIC
```

### Interactive Debugging

```bash
# Open bash shell in backend
docker-compose exec backend bash

# Open Python REPL
docker-compose exec backend python

# Run Python script interactively
docker-compose exec backend python -i scripts/init_db.py

# Open shell in frontend
docker-compose exec frontend sh

# Run commands without starting service
docker-compose run backend bash
docker-compose run frontend sh

# Run one-off command
docker-compose run backend python scripts/test.py
```

---

## Building and Updating

### Building Images

```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build backend
docker-compose build frontend

# Build without using cache (clean build)
docker-compose build --no-cache

# Build with progress output
docker-compose build --progress=plain

# Build in parallel (faster)
docker-compose build --parallel
```

### Pulling and Updating

```bash
# Pull latest base images
docker-compose pull

# Pull specific service base image
docker pull python:3.11-slim
docker pull node:20-alpine

# Update and restart services
git pull origin main
docker-compose build
docker-compose up -d

# Force recreate containers with new images
docker-compose up -d --force-recreate
```

### Rebuilding Services

```bash
# Rebuild and restart all services
docker-compose up -d --build

# Rebuild specific service and restart
docker-compose up -d --build backend

# Complete rebuild (no cache)
docker-compose build --no-cache
docker-compose up -d --force-recreate
```

---

## Cleanup and Maintenance

### Removing Containers

```bash
# Remove stopped containers
docker-compose rm

# Remove stopped containers without confirmation
docker-compose rm -f

# Stop and remove all containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove containers, volumes, and images
docker-compose down -v --rmi all
```

### Cleaning Up Docker Resources

```bash
# Remove unused containers
docker container prune

# Remove unused images
docker image prune

# Remove unused images (including tagged)
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune

# Remove all unused resources (containers, images, volumes, networks)
docker system prune

# Remove everything including volumes (CAUTION!)
docker system prune -a --volumes

# View disk usage
docker system df

# View detailed disk usage
docker system df -v
```

### Managing Volumes

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect produck-data
docker volume inspect postgres-data

# Remove specific volume (CAUTION: deletes data)
docker volume rm produck-data

# Backup volume
docker run --rm -v produck-data:/data -v $(pwd):/backup alpine tar czf /backup/produck-data-backup.tar.gz -C /data .

# Restore volume
docker run --rm -v produck-data:/data -v $(pwd):/backup alpine tar xzf /backup/produck-data-backup.tar.gz -C /data
```

### Managing Images

```bash
# List images
docker images

# List images for ProDuckt
docker images | grep produck

# Remove specific image
docker rmi produck-backend
docker rmi produck-frontend

# Remove dangling images (untagged)
docker image prune

# Remove all unused images
docker image prune -a

# View image history
docker history produck-backend
```

---

## Troubleshooting Commands

### Diagnosing Issues

```bash
# Check if Docker daemon is running
docker info

# Check Docker Compose version
docker-compose --version

# Validate docker-compose.yml syntax
docker-compose config

# View resolved configuration
docker-compose config

# Check which ports are in use
lsof -i :8000
lsof -i :5173
netstat -tulpn | grep 8000

# Check container exit codes
docker-compose ps -a

# View container logs for errors
docker-compose logs backend | grep -i error
docker-compose logs frontend | grep -i error
```

### Network Troubleshooting

```bash
# List Docker networks
docker network ls

# Inspect ProDuckt network
docker network inspect produck-network

# Test connectivity between services
docker-compose exec frontend ping backend
docker-compose exec backend ping db

# Test DNS resolution
docker-compose exec frontend nslookup backend
docker-compose exec backend nslookup db

# View network connections
docker-compose exec backend netstat -an
```

### Performance Troubleshooting

```bash
# Monitor resource usage in real-time
docker stats

# View container resource limits
docker inspect $(docker-compose ps -q backend) | grep -A 10 Memory

# Check disk usage
docker system df
df -h

# Check volume sizes
docker volume ls
du -sh /var/lib/docker/volumes/*

# View container processes
docker-compose top
docker-compose top backend
```

### Fixing Common Issues

```bash
# Reset everything (CAUTION: deletes all data)
docker-compose down -v
docker system prune -a --volumes
docker-compose build --no-cache
docker-compose up

# Fix permission issues
docker-compose exec backend chown -R appuser:appuser /app/data

# Recreate containers
docker-compose up -d --force-recreate

# Restart Docker daemon (Linux)
sudo systemctl restart docker

# Restart Docker Desktop (macOS/Windows)
# Use Docker Desktop UI or:
killall Docker && open /Applications/Docker.app
```

### Getting Help

```bash
# View docker-compose help
docker-compose --help

# View help for specific command
docker-compose up --help
docker-compose logs --help
docker-compose exec --help

# View Docker help
docker --help
docker run --help
```

---

## Quick Reference Cheat Sheet

### Most Common Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Rebuild and restart
docker-compose up -d --build

# Run migrations
docker-compose exec backend alembic upgrade head

# Access backend shell
docker-compose exec backend bash

# View service status
docker-compose ps

# Clean up
docker-compose down -v
docker system prune -a
```

### Development Workflow

```bash
# 1. Start development environment
docker-compose up

# 2. Make code changes (auto-reload enabled)

# 3. View logs
docker-compose logs -f backend

# 4. Run migrations if needed
docker-compose exec backend alembic upgrade head

# 5. Stop services
docker-compose down
```

### Production Workflow

```bash
# 1. Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# 2. Start production services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. Check health
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 4. View logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100

# 5. Monitor resources
docker stats
```

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [ProDuckt Docker Guide](DOCKER.md)
- [ProDuckt README](README.md)

---

**Quick Tip:** Create shell aliases for frequently used commands:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias dcu='docker-compose up'
alias dcd='docker-compose down'
alias dcl='docker-compose logs -f'
alias dcr='docker-compose restart'
alias dcb='docker-compose build'
alias dcp='docker-compose ps'
alias dce='docker-compose exec'
```
