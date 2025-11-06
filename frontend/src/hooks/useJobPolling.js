import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '../api/client';

/**
 * Hook for polling job status until completion or failure.
 *
 * @param {string} jobId - The job ID to poll
 * @param {object} options - Configuration options
 * @param {number} options.pollInterval - Milliseconds between polls (default: 3000)
 * @param {number} options.maxDuration - Max polling duration in ms (default: 600000 = 10 min)
 * @param {number} options.maxRetries - Max retry attempts on network errors (default: 5)
 * @param {function} options.onComplete - Callback when job completes successfully
 * @param {function} options.onError - Callback when job fails or times out
 * @returns {object} - { job, isPolling, progress, progressMessage, error, cancelPolling }
 */
export function useJobPolling(jobId, options = {}) {
  const {
    pollInterval = 3000, // Increased from 2s to 3s
    maxDuration = 600000, // 10 minutes
    maxRetries = 5,
    onComplete,
    onError
  } = options;

  const [job, setJob] = useState(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState(null);

  // Use refs to prevent multiple simultaneous polling loops
  const intervalIdRef = useRef(null);
  const timeoutIdRef = useRef(null);
  const isCancelledRef = useRef(false);
  const retryCountRef = useRef(0);

  // Store callbacks in refs to avoid re-running effect when they change
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  useEffect(() => {
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
  }, [onComplete, onError]);

  const cancelPolling = useCallback(() => {
    isCancelledRef.current = true;
    if (intervalIdRef.current) {
      clearInterval(intervalIdRef.current);
      intervalIdRef.current = null;
    }
    if (timeoutIdRef.current) {
      clearTimeout(timeoutIdRef.current);
      timeoutIdRef.current = null;
    }
    setIsPolling(false);
  }, []);

  useEffect(() => {
    if (!jobId) return;

    // Prevent multiple polling loops
    if (intervalIdRef.current || timeoutIdRef.current) {
      console.warn('Polling already in progress, skipping duplicate poll setup');
      return;
    }

    isCancelledRef.current = false;
    retryCountRef.current = 0;

    const poll = async () => {
      if (isCancelledRef.current) return;

      try {
        const response = await apiClient.get(`/api/jobs/${jobId}`);
        const jobData = response.data;

        if (isCancelledRef.current) return;

        // Reset retry count on successful poll
        retryCountRef.current = 0;

        setJob(jobData);

        if (jobData.status === 'completed') {
          cancelPolling();
          if (onCompleteRef.current) {
            onCompleteRef.current(jobData.result_data);
          }
        } else if (jobData.status === 'failed') {
          cancelPolling();
          const err = new Error(jobData.error_message || 'Job failed');
          setError(err);
          if (onErrorRef.current) {
            onErrorRef.current(err);
          }
        }
      } catch (err) {
        if (isCancelledRef.current) return;

        console.error('Error polling job:', err);
        retryCountRef.current += 1;

        // If we've exceeded max retries, give up
        if (retryCountRef.current >= maxRetries) {
          console.error(`Max retries (${maxRetries}) exceeded, stopping poll`);
          cancelPolling();
          const retryError = new Error(`Failed to poll job after ${maxRetries} attempts: ${err.message}`);
          setError(retryError);
          if (onErrorRef.current) {
            onErrorRef.current(retryError);
          }
        } else {
          console.log(`Retry ${retryCountRef.current}/${maxRetries} after error`);
          // Continue polling, will retry on next interval
        }
      }
    };

    // Start polling
    setIsPolling(true);
    setError(null);
    poll(); // Initial poll
    intervalIdRef.current = setInterval(poll, pollInterval);

    // Set max timeout
    timeoutIdRef.current = setTimeout(() => {
      if (!isCancelledRef.current) {
        cancelPolling();
        const timeoutError = new Error('Job polling timed out after 10 minutes');
        setError(timeoutError);
        if (onErrorRef.current) {
          onErrorRef.current(timeoutError);
        }
      }
    }, maxDuration);

    // Cleanup
    return () => {
      cancelPolling();
    };
  }, [jobId, pollInterval, maxDuration, maxRetries]);

  return {
    job,
    isPolling,
    progress: job?.progress_percent,
    progressMessage: job?.progress_message,
    error,
    cancelPolling
  };
}
