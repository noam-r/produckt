#!/bin/bash

# ProDuckt Docker Backup Script
# Creates a complete backup of Docker volumes, database, and configuration

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="produck-backup-${TIMESTAMP}"
TEMP_DIR="/tmp/${BACKUP_NAME}"

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

cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        log_info "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT

# Main backup process
main() {
    log_info "Starting ProDuckt Docker backup..."
    log_info "Backup name: ${BACKUP_NAME}"

    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$TEMP_DIR"

    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose not found. Please install Docker Compose."
        exit 1
    fi

    # Check if services are running
    if ! docker-compose ps | grep -q "Up"; then
        log_warn "No running services detected. Backup will include stopped containers."
    fi

    # Detect database type
    DATABASE_TYPE="sqlite"
    if grep -q "postgresql://" .env 2>/dev/null || docker-compose ps | grep -q "db.*Up"; then
        DATABASE_TYPE="postgresql"
    fi

    log_info "Detected database type: ${DATABASE_TYPE}"

    # Backup configuration files
    log_info "Backing up configuration files..."
    mkdir -p "$TEMP_DIR/config"
    
    [ -f .env ] && cp .env "$TEMP_DIR/config/.env"
    [ -f docker-compose.yml ] && cp docker-compose.yml "$TEMP_DIR/config/"
    [ -f docker-compose.override.yml ] && cp docker-compose.override.yml "$TEMP_DIR/config/"
    [ -f docker-compose.dev.yml ] && cp docker-compose.dev.yml "$TEMP_DIR/config/"
    [ -f docker-compose.prod.yml ] && cp docker-compose.prod.yml "$TEMP_DIR/config/"

    # Backup database
    log_info "Backing up database..."
    mkdir -p "$TEMP_DIR/database"

    if [ "$DATABASE_TYPE" = "sqlite" ]; then
        # SQLite backup
        log_info "Backing up SQLite database..."
        
        # Try to get database from running container
        if docker-compose ps | grep -q "backend.*Up"; then
            docker-compose exec -T backend sqlite3 /app/data/produck.db ".backup /app/data/backup-temp.db" 2>/dev/null || true
            docker cp $(docker-compose ps -q backend):/app/data/backup-temp.db "$TEMP_DIR/database/produck.db" 2>/dev/null || true
            docker-compose exec -T backend rm -f /app/data/backup-temp.db 2>/dev/null || true
        fi
        
        # Fallback: backup entire volume
        if [ ! -f "$TEMP_DIR/database/produck.db" ]; then
            log_warn "Could not backup from running container, backing up volume..."
            docker run --rm \
                -v produck-data:/data \
                -v "$TEMP_DIR/database":/backup \
                alpine sh -c "cp -r /data/* /backup/ 2>/dev/null || true"
        fi
        
    else
        # PostgreSQL backup
        log_info "Backing up PostgreSQL database..."
        
        if docker-compose ps | grep -q "db.*Up"; then
            docker-compose exec -T db pg_dump -U produck produck > "$TEMP_DIR/database/produck-postgres.sql" 2>/dev/null || {
                log_error "Failed to backup PostgreSQL database"
                exit 1
            }
            
            # Also backup roles and globals
            docker-compose exec -T db pg_dumpall -U produck --globals-only > "$TEMP_DIR/database/globals.sql" 2>/dev/null || true
        else
            log_error "PostgreSQL container is not running. Cannot backup database."
            exit 1
        fi
    fi

    # Backup volumes
    log_info "Backing up Docker volumes..."
    mkdir -p "$TEMP_DIR/volumes"

    # Backup produck-data volume
    if docker volume ls | grep -q "produck-data"; then
        log_info "Backing up produck-data volume..."
        docker run --rm \
            -v produck-data:/data \
            -v "$TEMP_DIR/volumes":/backup \
            alpine tar czf /backup/produck-data.tar.gz -C /data . 2>/dev/null || {
                log_warn "Failed to backup produck-data volume"
            }
    fi

    # Backup postgres-data volume (if exists)
    if docker volume ls | grep -q "postgres-data"; then
        log_info "Backing up postgres-data volume..."
        docker run --rm \
            -v postgres-data:/data \
            -v "$TEMP_DIR/volumes":/backup \
            alpine tar czf /backup/postgres-data.tar.gz -C /data . 2>/dev/null || {
                log_warn "Failed to backup postgres-data volume"
            }
    fi

    # Create metadata file
    log_info "Creating backup metadata..."
    cat > "$TEMP_DIR/metadata.txt" <<EOF
ProDuckt Docker Backup
======================
Backup Date: $(date)
Backup Name: ${BACKUP_NAME}
Database Type: ${DATABASE_TYPE}
Docker Compose Version: $(docker-compose version --short 2>/dev/null || echo "unknown")
Git Commit: $(git rev-parse HEAD 2>/dev/null || echo "unknown")
Git Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

Services Status:
$(docker-compose ps 2>/dev/null || echo "No services running")

Volumes:
$(docker volume ls | grep produck 2>/dev/null || echo "No volumes found")

Backup Contents:
$(find "$TEMP_DIR" -type f -exec ls -lh {} \; | awk '{print $9, $5}')
EOF

    # Create compressed archive
    log_info "Creating compressed archive..."
    tar czf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" -C /tmp "$BACKUP_NAME"

    # Calculate backup size
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" | cut -f1)
    
    log_info "Backup completed successfully!"
    log_info "Backup file: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
    log_info "Backup size: $BACKUP_SIZE"
    
    # Show backup contents
    echo ""
    log_info "Backup contents:"
    tar tzf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" | head -20
    
    # Cleanup old backups (keep last 7)
    log_info "Cleaning up old backups (keeping last 7)..."
    ls -t "$BACKUP_DIR"/produck-backup-*.tar.gz | tail -n +8 | xargs -r rm -f
    
    echo ""
    log_info "To restore this backup, run:"
    echo "  ./scripts/restore-docker.sh $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
}

# Run main function
main "$@"
