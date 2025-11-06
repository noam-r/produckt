import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogTitle,
  CircularProgress,
  Typography,
  Box,
  LinearProgress
} from '@mui/material';

/**
 * Blocking modal that shows job progress.
 * Cannot be dismissed while job is in progress.
 */
export default function JobProgressModal({
  open,
  title = 'Processing...',
  progressMessage,
  progressPercent
}) {
  const percentValue = progressPercent ? parseInt(progressPercent) : null;

  return (
    <Dialog
      open={open}
      disableEscapeKeyDown
      PaperProps={{
        sx: { minWidth: 400 }
      }}
    >
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 3 }}>
          <CircularProgress size={60} sx={{ mb: 3 }} />

          {progressMessage && (
            <Typography variant="body1" sx={{ mb: 2, textAlign: 'center' }}>
              {progressMessage}
            </Typography>
          )}

          {percentValue !== null && (
            <Box sx={{ width: '100%', mt: 2 }}>
              <LinearProgress
                variant="determinate"
                value={percentValue}
                sx={{ height: 8, borderRadius: 4 }}
              />
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ mt: 1, display: 'block', textAlign: 'center' }}
              >
                {percentValue}% complete
              </Typography>
            </Box>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  );
}
