#!/bin/bash

# ProDuckt Docker Restore Script
# Restores a backup created by backup-docker.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_prompt() {
    echo -e "${BLUE}[PROMPT]${NC} $1"
}

cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        log_info "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT

# Check arguments
if [ $# -eq 0 ]; then
    log_error "Usage: $0 <backup-file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lh ./backups/produck-backup-*.tar.gz 2>/dev/null || echo "  No backups found in ./backups/"
    exit 1
fi

BACKUP_FILE="$1"

# Validate backup file
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Configuration
TEMP_DIR="/tmp/produck-restore-$$"
BACKUP_NAME=$(basename "$BACKUP_FILE" .tar.gz)

# Main restore process
main() {
    log_info "Starting ProDuckt Docker restore..."
    log_info "Backup file: $BACKUP_FILE"
    
    # Extract backup
    log_info "Extracting backup archive..."
    mkdir -p "$TEMP_DIR"
    tar xzf "$BACKUP_FILE" -C "$TEMP_DIR"
    
    # Find the backup directory (it should be the only directory in TEMP_DIR)
    BACKUP_DIR=$(find "$TEMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -1)
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "Invalid backup archive structure"
        exit 1
    fi
    
    # Show backup metadata
    if [ -f "$BACKUP_DIR/metadata.txt" ]; then
        echo ""
        log_info "Backup metadata:"
        cat "$BACKUP_DIR/metadata.txt"
        echo ""
    fi
    
    # Confirm restore
    log_warn "This will stop running services and restore data from backup."
    log_warn "Current data will be replaced!"
    log_prompt "Do you want to continue? (yes/no): "
    read -r CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        log_info "Restore cancelled."
        exit 0
    fi
    
    # Stop running services
    log_info "Stopping Docker services..."
    docker-compose down || true
    
    # Detect database type from backup
    DATABASE_TYPE="sqlite"
    if [ -f "$BACKUP_DIR/database/produck-postgres.sql" ]; then
        DATABASE_TYPE="postgresql"
    fi
    
    log_info "Detected database type: ${DATABASE_TYPE}"
    
    # Restore configuration files
    log_info "Restoring configuration files..."
    
    if [ -d "$BACKUP_DIR/config" ]; then
        # Backup current config before overwriting
        if [ -f .env ]; then
            cp .env .env.backup-before-restore
            log_info "Current .env backed up to .env.backup-before-restore"
        fi
        
        # Restore config files
        [ -f "$BACKUP_DIR/config/.env" ] && cp "$BACKUP_DIR/config/.env" .env
        [ -f "$BACKUP_DIR/config/docker-compose.override.yml" ] && \
            cp "$BACKUP_DIR/config/docker-compose.override.yml" docker-compose.override.yml
        
        log_info "Configuration files restored"
    fi
    
    # Restore volumes
    if [ -d "$BACKUP_DIR/volumes" ]; then
        log_info "Restoring Docker volumes..."
        
        # Restore produck-data volume
        if [ -f "$BACKUP_DIR/volumes/produck-data.tar.gz" ]; then
            log_info "Restoring produck-data volume..."
            
            # Remove existing volume
            docker volume rm produck-data 2>/dev/null || true
            
            # Create new volume and restore data
            docker volume create produck-data
            docker run --rm \
                -v produck-data:/data \
                -v "$BACKUP_DIR/volumes":/backup \
                alpine sh -c "cd /data && tar xzf /backup/produck-data.tar.gz"
            
            log_info "produck-data volume restored"
        fi
        
        # Restore postgres-data volume
        if [ -f "$BACKUP_DIR/volumes/postgres-data.tar.gz" ]; then
            log_info "Restoring postgres-data volume..."
            
            # Remove existing volume
            docker volume rm postgres-data 2>/dev/null || true
            
            # Create new volume and restore data
            docker volume create postgres-data
            docker run --rm \
                -v postgres-data:/data \
                -v "$BACKUP_DIR/volumes":/backup \
                alpine sh -c "cd /data && tar xzf /backup/postgres-data.tar.gz"
            
            log_info "postgres-data volume restored"
        fi
    fi
    
    # Start services
    log_info "Starting Docker services..."
    docker-compose up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to start..."
    sleep 10
    
    # Restore database
    if [ -d "$BACKUP_DIR/database" ]; then
        log_info "Restoring database..."
        
        if [ "$DATABASE_TYPE" = "sqlite" ]; then
            # SQLite restore
            if [ -f "$BACKUP_DIR/database/produck.db" ]; then
                log_info "Restoring SQLite database..."
                
                # Stop backend to prevent locks
                docker-compose stop backend
                
                # Copy database file
                docker cp "$BACKUP_DIR/database/produck.db" \
                    $(docker-compose ps -q backend):/app/data/produck.db
                
                # Fix permissions
                docker-compose run --rm backend chown appuser:appuser /app/data/produck.db
                
                # Start backend
                docker-compose start backend
                
                log_info "SQLite database restored"
            fi
        else
            # PostgreSQL restore
            if [ -f "$BACKUP_DIR/database/produck-postgres.sql" ]; then
                log_info "Restoring PostgreSQL database..."
                
                # Wait for PostgreSQL to be ready
                log_info "Waiting for PostgreSQL to be ready..."
                sleep 15
                
                # Stop backend to prevent connections
                docker-compose stop backend
                
                # Drop and recreate database
                docker-compose exec -T db psql -U produck -c "DROP DATABASE IF EXISTS produck;" postgres || true
                docker-compose exec -T db psql -U produck -c "CREATE DATABASE produck;" postgres
                
                # Restore globals (roles, etc.)
                if [ -f "$BACKUP_DIR/database/globals.sql" ]; then
                    docker-compose exec -T db psql -U produck postgres < "$BACKUP_DIR/database/globals.sql" || true
                fi
                
                # Restore database
                docker-compose exec -T db psql -U produck produck < "$BACKUP_DIR/database/produck-postgres.sql"
                
                # Start backend
                docker-compose start backend
                
                log_info "PostgreSQL database restored"
            fi
        fi
    fi
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Verify restore
    log_info "Verifying restore..."
    
    # Check service status
    docker-compose ps
    
    # Test backend health
    if curl -f http://localhost:8000/health &>/dev/null; then
        log_info "✓ Backend is healthy"
    else
        log_warn "✗ Backend health check failed"
    fi
    
    # Test frontend
    if curl -f http://localhost:5173 &>/dev/null; then
        log_info "✓ Frontend is accessible"
    else
        log_warn "✗ Frontend is not accessible"
    fi
    
    echo ""
    log_info "Restore completed!"
    log_info "Please verify that your data and configuration are correct."
    log_info "Access ProDuckt at: http://localhost:5173"
    
    # Show logs if there are errors
    if ! docker-compose ps | grep -q "Up (healthy)"; then
        echo ""
        log_warn "Some services are not healthy. Showing recent logs:"
        docker-compose logs --tail=50
    fi
}

# Run main function
main "$@"
