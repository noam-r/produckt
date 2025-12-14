# Monthly Budget Reset System

This document describes the monthly budget reset system that automatically resets user spending counters at the beginning of each month while preserving historical data and budget limits.

## Overview

The monthly budget reset system consists of several components:

1. **MonthlyBudgetResetService** - Core service that handles the reset logic
2. **MonthlyBudgetScheduler** - Service for scheduling reset jobs
3. **Job Executor Integration** - Background job execution
4. **CLI Script** - Command-line interface for manual triggering
5. **Cron Integration** - Automated scheduling

## Components

### MonthlyBudgetResetService

Located in `backend/services/monthly_budget_reset_service.py`

Key methods:
- `reset_monthly_budgets(year, month)` - Performs the actual reset
- `should_run_reset(year, month)` - Checks if reset is needed
- `get_previous_month_spending_summary()` - Gets spending statistics
- `cleanup_old_spending_records()` - Removes old historical data

### MonthlyBudgetScheduler

Located in `backend/services/monthly_budget_scheduler.py`

Key methods:
- `schedule_monthly_reset()` - Creates a reset job
- `should_schedule_reset()` - Checks if scheduling is needed
- `schedule_if_needed()` - Conditionally schedules reset

### Job Integration

The reset is implemented as a background job (`JobType.MONTHLY_BUDGET_RESET`) that:
- Runs asynchronously via the job worker
- Provides progress updates
- Handles errors gracefully
- Logs all operations

## Usage

### Manual Execution

Use the CLI script to manually trigger a reset:

```bash
# Schedule a reset job (only if needed)
python scripts/monthly_budget_reset.py

# Force scheduling even if already done this month
python scripts/monthly_budget_reset.py --force

# Also cleanup old records
python scripts/monthly_budget_reset.py --cleanup
```

### Automated Scheduling

Set up a cron job to run monthly:

```bash
# Edit crontab
crontab -e

# Add this line to run at 2:00 AM on the 1st of every month
0 2 1 * * cd /path/to/produckt && python scripts/monthly_budget_reset.py --cleanup >> /var/log/produckt/monthly-reset.log 2>&1
```

Or use the provided example:
```bash
cp scripts/cron-monthly-reset.example scripts/cron-monthly-reset
# Edit paths in the file
crontab scripts/cron-monthly-reset
```

### Programmatic Usage

```python
from backend.services.monthly_budget_scheduler import MonthlyBudgetScheduler
from backend.database import SessionLocal

db = SessionLocal()
scheduler = MonthlyBudgetScheduler(db)

# Schedule if needed
job = scheduler.schedule_if_needed()
if job:
    print(f"Reset job scheduled: {job.id}")
else:
    print("Reset not needed")

db.close()
```

## Reset Process

The monthly reset process:

1. **Identifies all users** in the system
2. **Checks existing records** for the target month
3. **Resets spending counters** to $0.00 for the new month
4. **Creates new records** for users without existing records
5. **Preserves historical data** from previous months
6. **Maintains budget limits** unchanged
7. **Cleans up old records** (optional, keeps 24 months by default)

## Properties Verified

The system maintains these correctness properties:

- **Budget Reset Consistency**: When a new month begins, spending counters reset to zero while preserving budget limits
- **Historical Preservation**: Previous month spending data is never modified
- **Budget Limit Preservation**: User budget limits remain unchanged during reset
- **Record Completeness**: All users have spending records for the new month after reset

## Monitoring

The system provides detailed logging and statistics:

- Number of users processed
- Records reset vs. created
- Previous month spending summary
- Cleanup statistics
- Error handling and recovery

## Error Handling

The system handles various error conditions:

- Database connection failures
- Concurrent reset attempts
- Invalid date parameters
- Missing organizations
- Job execution failures

All errors are logged with full context for debugging.

## Testing

Property-based tests verify the correctness of the reset logic:

```bash
# Run the budget reset property test
python -m pytest tests/test_services/test_budget_service.py::TestBudgetServiceProperties::test_budget_reset_consistency -v
```

## Configuration

Key configuration options:

- **Cleanup retention**: Default 24 months of historical data
- **Job polling**: Background worker polls every 2 seconds
- **Progress reporting**: Updates provided during execution
- **Logging level**: Configurable via environment variables

## Security

- Only system-level operations (no user-specific organization required)
- Audit logging for all reset operations
- Idempotent operations (safe to run multiple times)
- Transactional consistency (all-or-nothing updates)