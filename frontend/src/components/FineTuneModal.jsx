import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  CircularProgress,
  Alert,
  Paper,
} from '@mui/material';
import { AutoAwesome } from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function FineTuneModal({
  open,
  onClose,
  sectionName,
  sectionContent,
  onFineTune,
  isProcessing = false,
}) {
  const [instructions, setInstructions] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    if (!instructions.trim()) {
      setError('Please provide instructions for improving this section');
      return;
    }

    setError(null);
    await onFineTune(instructions);
  };

  const handleClose = () => {
    if (!isProcessing) {
      setInstructions('');
      setError(null);
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      disableEscapeKeyDown={isProcessing}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AutoAwesome color="primary" />
          <Typography variant="h6" component="span">
            Fine-Tune: {sectionName}
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Current Section Content */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" fontWeight="600" gutterBottom>
            Current Content
          </Typography>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              bgcolor: 'background.default',
              maxHeight: 300,
              overflow: 'auto',
              border: 1,
              borderColor: 'divider',
              '& p': {
                mb: 1,
                color: 'text.primary',
              },
              '& ul, & ol': {
                mb: 1,
                pl: 2,
              },
              '& li': {
                color: 'text.primary',
              },
              '& strong': {
                fontWeight: 600,
              },
              '& table': {
                width: '100%',
                borderCollapse: 'collapse',
                mb: 1,
              },
              '& th, & td': {
                border: '1px solid',
                borderColor: 'divider',
                p: 1,
                textAlign: 'left',
                color: 'text.primary',
              },
              '& th': {
                bgcolor: 'action.hover',
                fontWeight: 600,
              },
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {sectionContent}
            </ReactMarkdown>
          </Paper>
        </Box>

        {/* Instructions Input */}
        <Box>
          <Typography variant="subtitle2" fontWeight="600" gutterBottom>
            Improvement Instructions
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            placeholder="Describe how you'd like to improve this section. For example: 'Make it more concise', 'Add more details about technical implementation', 'Focus more on business value', etc."
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            disabled={isProcessing}
            sx={{ mb: 1 }}
          />
          <Typography variant="caption" color="text.secondary">
            Be specific about what you want to change. The AI will revise the section based on your instructions.
          </Typography>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={isProcessing}>
          Cancel
        </Button>
        <Button
          variant="contained"
          startIcon={isProcessing ? <CircularProgress size={20} /> : <AutoAwesome />}
          onClick={handleSubmit}
          disabled={isProcessing || !instructions.trim()}
        >
          {isProcessing ? 'Processing...' : 'Make Changes'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
