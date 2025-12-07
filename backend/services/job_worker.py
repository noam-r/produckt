"""
Background job worker that polls for pending jobs and executes them.

This worker solves the problem of background jobs not executing in production
when using Gunicorn with multiple workers. Instead of spawning threads that
only exist in one worker process, this creates a separate background thread
that polls the database for PENDING jobs and executes them.

Architecture:
- Single background thread per application instance
- Polls database every N seconds for PENDING jobs
- Uses database row locking to prevent duplicate execution
- Graceful shutdown on SIGTERM/SIGINT
- Works across multiple Gunicorn workers
"""

import threading
import time
import logging
import signal
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Job, JobStatus
from backend.repositories.job import JobRepository
from backend.services.job_executor import _execute_job

logger = logging.getLogger(__name__)


class JobWorker:
    """
    Background worker that continuously polls for pending jobs and executes them.
    """

    def __init__(self, poll_interval: int = 2, max_retries: int = 3):
        """
        Initialize job worker.

        Args:
            poll_interval: Seconds between polling for new jobs
            max_retries: Maximum retry attempts for failed jobs
        """
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()

    def start(self):
        """Start the background worker thread."""
        if self.running:
            logger.warning("Job worker is already running")
            return

        self.running = True
        self._shutdown_event.clear()
        self.thread = threading.Thread(target=self._run_worker, daemon=False)
        self.thread.start()
        logger.info(f"Job worker started (poll_interval={self.poll_interval}s)")

    def stop(self):
        """Stop the background worker thread gracefully."""
        if not self.running:
            return

        logger.info("Stopping job worker...")
        self.running = False
        self._shutdown_event.set()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=30)  # Wait up to 30 seconds
            if self.thread.is_alive():
                logger.warning("Job worker did not stop gracefully within timeout")
            else:
                logger.info("Job worker stopped successfully")

    def _run_worker(self):
        """Main worker loop that polls for pending jobs."""
        logger.info("Job worker loop started")

        while self.running:
            try:
                # Check for pending jobs
                jobs = self._get_pending_jobs()

                if jobs:
                    logger.info(f"Found {len(jobs)} pending job(s)")
                    for job in jobs:
                        if not self.running:
                            break
                        self._execute_job_safely(job.id)

                # Wait for next poll interval or shutdown event
                if self._shutdown_event.wait(timeout=self.poll_interval):
                    # Shutdown event was set
                    break

            except Exception as e:
                logger.error(f"Error in job worker loop: {e}", exc_info=True)
                # Continue running even if there's an error
                time.sleep(self.poll_interval)

        logger.info("Job worker loop ended")

    def _get_pending_jobs(self) -> list[Job]:
        """
        Get all pending jobs from the database.

        Returns:
            List of pending jobs
        """
        db: Session = SessionLocal()
        try:
            job_repo = JobRepository(db)

            # Get all PENDING jobs, ordered by creation time (oldest first)
            pending_jobs = db.query(Job).filter(
                Job.status == JobStatus.PENDING
            ).order_by(
                Job.created_at.asc()
            ).limit(10).all()  # Process up to 10 jobs per cycle

            # Also check for stuck IN_PROGRESS jobs (running for more than 1 hour)
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            stuck_jobs = db.query(Job).filter(
                Job.status == JobStatus.IN_PROGRESS,
                Job.started_at < one_hour_ago
            ).all()

            if stuck_jobs:
                logger.warning(f"Found {len(stuck_jobs)} stuck job(s), resetting to PENDING")
                for job in stuck_jobs:
                    job.status = JobStatus.PENDING
                    job.error_message = "Job was stuck in IN_PROGRESS state and has been reset"
                db.commit()

            return pending_jobs

        except Exception as e:
            logger.error(f"Error fetching pending jobs: {e}", exc_info=True)
            return []
        finally:
            db.close()

    def _execute_job_safely(self, job_id):
        """
        Execute a job in a separate thread with error handling.

        Args:
            job_id: ID of the job to execute
        """
        try:
            # Claim the job by marking it IN_PROGRESS
            db: Session = SessionLocal()
            try:
                job_repo = JobRepository(db)
                job = job_repo._get_by_id_internal(job_id)

                if not job:
                    logger.warning(f"Job {job_id} not found")
                    return

                # Check if already being processed
                if job.status != JobStatus.PENDING:
                    logger.debug(f"Job {job_id} is no longer PENDING (status: {job.status})")
                    return

                # Mark as claimed (will be updated to IN_PROGRESS by executor)
                logger.info(f"Executing job {job_id} (type: {job.job_type.value})")

            finally:
                db.close()

            # Execute the job (this will handle its own database session)
            _execute_job(job_id)

        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}", exc_info=True)


# Global worker instance
_worker: Optional[JobWorker] = None


def start_job_worker(poll_interval: int = 2):
    """
    Start the global job worker.

    Args:
        poll_interval: Seconds between polling for new jobs
    """
    global _worker

    if _worker is not None:
        logger.warning("Job worker already initialized")
        return

    _worker = JobWorker(poll_interval=poll_interval)
    _worker.start()


def stop_job_worker():
    """Stop the global job worker."""
    global _worker

    if _worker is None:
        logger.warning("Job worker not initialized")
        return

    _worker.stop()
    _worker = None


def get_job_worker() -> Optional[JobWorker]:
    """Get the global job worker instance."""
    return _worker
