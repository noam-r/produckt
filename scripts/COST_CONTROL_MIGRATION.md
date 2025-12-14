# Cost Control Migration Scripts

This directory contains migration scripts for the cost control feature implementation. These scripts handle migrating existing users and initiatives to have the new cost control defaults.

## Available Scripts

### 1. `migrate_cost_controls_universal.py` (Recommended)

**Universal database-compatible migration script** that works with both PostgreSQL and SQLite.

**Features:**
- ✅ Automatic database type detection
- ✅ Database-agnostic error handling  
- ✅ Column and table existence checking using SQLAlchemy inspector
- ✅ PostgreSQL and SQLite compatible
- ✅ Comprehensive error messages with database-specific instructions

**Usage:**
```bash
# For PostgreSQL (production)
python scripts/migrate_cost_controls_universal.py

# For SQLite (development/testing)
DATABASE_URL=sqlite:///./produck.db python scripts/migrate_cost_controls_universal.py
```

### 2. `migrate_cost_controls.py`

**Standard migration script** that uses the configured database from environment/settings.

**Features:**
- ✅ Uses application's configured database URL
- ✅ Improved error handling for both PostgreSQL and SQLite
- ✅ ORM-based operations
- ✅ Comprehensive reporting

**Usage:**
```bash
# Uses DATABASE_URL from environment or .env file
python scripts/migrate_cost_controls.py
```

### 3. `migrate_cost_controls_simple.py`

**SQLite-specific migration script** that manually creates tables and columns.

**Features:**
- ✅ SQLite-only compatibility
- ✅ Manual DDL operations for testing
- ✅ Bypasses Alembic migration issues with SQLite foreign keys

**Usage:**
```bash
# SQLite only
python scripts/migrate_cost_controls_simple.py
```

## Database Compatibility

### PostgreSQL Production Usage

For production PostgreSQL databases, use the universal script:

```bash
# Ensure proper Alembic migrations are run first
alembic upgrade head

# Run the migration
python scripts/migrate_cost_controls_universal.py
```

**PostgreSQL-specific features:**
- Uses SQLAlchemy inspector for column/table detection
- Handles PostgreSQL-specific error messages
- Compatible with connection pooling
- Supports foreign key constraints

### SQLite Development Usage

For development with SQLite:

```bash
# Option 1: Universal script (recommended)
DATABASE_URL=sqlite:///./produck.db python scripts/migrate_cost_controls_universal.py

# Option 2: Simple script (if Alembic issues)
python scripts/migrate_cost_controls_simple.py
```

## What the Migration Does

All scripts perform the same core operations:

1. **Verify User Budgets**: Ensures all existing users have the default $100 monthly budget
2. **Verify Initiative Limits**: Ensures all existing initiatives have the default 50 question limit  
3. **Initialize Current Month**: Creates monthly spending records for the current month for all users
4. **Backfill Historical Data**: Processes existing LLM call data to populate historical spending records

## Prerequisites

Before running any migration script, ensure:

1. **Database Schema**: The cost control fields must exist in the database
   - For production: Run `alembic upgrade head`
   - For development: The simple script can create them automatically

2. **Application Dependencies**: All Python dependencies are installed
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Database Connection**: Proper database connection configuration in `.env` or environment

## Error Handling

The scripts include comprehensive error handling:

- **Missing Columns**: Detects when cost control columns haven't been migrated yet
- **Missing Tables**: Detects when the `user_monthly_spending` table doesn't exist
- **Database Connectivity**: Handles connection issues gracefully
- **Data Integrity**: Uses transactions to ensure data consistency

## Output Example

```
======================================================================
Cost Control Data Migration (Universal)
======================================================================
Detected database type: postgresql

1. Verifying user budget defaults...
   ✓ 0 users verified/updated with $100 default budget

2. Verifying initiative question limits...
   ✓ 0 initiatives verified/updated with 50 question limit

3. Initializing current month spending records...
   ✓ 6 current month spending records initialized

4. Backfilling historical spending data...
   - Created 2 new historical records
   - Updated 1 existing records
   ✓ 2 historical spending records created

======================================================================
Migration Summary
======================================================================
Total users with budgets:           6
Total initiatives with limits:      2
Total monthly spending records:     8

Budget distribution:
  $100.00: 6 users

Question limit distribution:
  50 questions: 2 initiatives

======================================================================
Cost Control Migration Complete!
======================================================================
```

## Troubleshooting

### "Budget columns not found"
- **Cause**: Alembic migrations haven't been run
- **Solution**: Run `alembic upgrade head` first

### "UserMonthlySpending table not found"  
- **Cause**: Cost control migration hasn't been applied
- **Solution**: Run `alembic upgrade head` first

### "Could not translate host name 'db'"
- **Cause**: Docker database not running or wrong DATABASE_URL
- **Solution**: Start Docker services or use SQLite for testing

### Permission Errors
- **Cause**: Database user lacks necessary permissions
- **Solution**: Ensure database user has INSERT/UPDATE permissions

## Requirements Fulfilled

This migration implementation fulfills the following requirements:

- **Requirement 1.3**: Set default $100 budget for all existing users
- **Requirement 5.1**: Set default 50 question limit for all existing initiatives

The migration scripts ensure that existing data is properly migrated to support the new cost control features without data loss or corruption.