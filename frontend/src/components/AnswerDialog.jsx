import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  ToggleButtonGroup,
  ToggleButton,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Chip,
} from '@mui/material';
import { CheckCircle, Help, Block, Save, Cancel } from '@mui/icons-material';
import { useAnswerQuestion } from '../hooks/useQuestions';

// Answer type options (values must match backend enum: title case)
const answerTypes = [
  { value: 'Answered', label: 'Answered', icon: <CheckCircle />, color: 'success' },
  { value: 'Unknown', label: 'Unknown', icon: <Help />, color: 'warning' },
  { value: 'Skipped', label: 'Skipped', icon: <Block />, color: 'default' },
];

// Category color mapping
const categoryColors = {
  Business_Dev: 'primary',
  Technical: 'secondary',
  Product: 'info',
  Operations: 'warning',
  Financial: 'error',
};

// Priority color mapping
const priorityColors = {
  P0: 'error',
  P1: 'warning',
  P2: 'info',
};

export default function AnswerDialog({ open, onClose, question, initiativeId }) {
  const [answerType, setAnswerType] = useState('Answered');
  const [answerText, setAnswerText] = useState('');
  const [error, setError] = useState('');

  const answerQuestion = useAnswerQuestion();

  // Reset form when dialog opens with new question
  useEffect(() => {
    if (question) {
      setAnswerType(question.answer?.answer_status || 'Answered');
      setAnswerText(question.answer?.answer_text || '');
      setError('');
    }
  }, [question]);

  const handleAnswerTypeChange = (event, newType) => {
    if (newType !== null) {
      setAnswerType(newType);
      setError('');
    }
  };

  const handleSubmit = async () => {
    // Validation
    if (answerType === 'Answered' && !answerText.trim()) {
      setError('Please provide an answer');
      return;
    }

    if (answerType === 'Unknown' && !answerText.trim()) {
      setError('Please explain what is unknown or provide assumptions');
      return;
    }

    try {
      await answerQuestion.mutateAsync({
        initiativeId,
        questionId: question.id,
        answerData: {
          answer_status: answerType,
          answer_text: answerText.trim() || null,
        },
      });
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save answer');
    }
  };

  const handleCancel = () => {
    onClose();
  };

  if (!question) return null;

  const isLoading = answerQuestion.isPending;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
          <Typography variant="h6" sx={{ flex: 1 }}>
            Answer Question
          </Typography>
          <Chip
            label={question.category.replace('_', ' ')}
            color={categoryColors[question.category]}
            size="small"
          />
          <Chip
            label={question.priority}
            color={priorityColors[question.priority]}
            size="small"
          />
        </Box>
      </DialogTitle>

      <DialogContent>
        {/* Question Text */}
        <Box sx={{ mb: 3, p: 2, bgcolor: 'action.hover', borderRadius: 2 }}>
          <Typography variant="body1" fontWeight="500">
            {question.question_text}
          </Typography>
        </Box>

        {/* Answer Type Selector */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Answer Type
          </Typography>
          <ToggleButtonGroup
            value={answerType}
            exclusive
            onChange={handleAnswerTypeChange}
            fullWidth
            disabled={isLoading}
          >
            {answerTypes.map((type) => (
              <ToggleButton key={type.value} value={type.value} color={type.color}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {type.icon}
                  {type.label}
                </Box>
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>

        {/* Answer Text Field */}
        {answerType !== 'Skipped' && (
          <Box sx={{ mb: 2 }}>
            <TextField
              fullWidth
              label={
                answerType === 'Answered'
                  ? 'Your Answer'
                  : 'What is unknown? (Include assumptions if applicable)'
              }
              multiline
              rows={6}
              value={answerText}
              onChange={(e) => {
                setAnswerText(e.target.value);
                setError('');
              }}
              disabled={isLoading}
              required={answerType !== 'Skipped'}
              helperText={
                answerType === 'Answered'
                  ? 'Provide a detailed answer to this question'
                  : 'Explain what information is missing or any assumptions you\'re making'
              }
            />
          </Box>
        )}

        {/* Helper Text for Skipped */}
        {answerType === 'Skipped' && (
          <Alert severity="info" sx={{ mb: 2 }}>
            This question will be marked as skipped and won't affect MRD generation readiness.
          </Alert>
        )}

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Iteration Info */}
        <Typography variant="caption" color="text.secondary">
          Iteration {question.iteration} • Created {new Date(question.created_at).toLocaleDateString()}
        </Typography>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={handleCancel}
          disabled={isLoading}
          startIcon={<Cancel />}
        >
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={isLoading}
          startIcon={isLoading ? <CircularProgress size={20} /> : <Save />}
        >
          {isLoading ? 'Saving...' : 'Save Answer'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
