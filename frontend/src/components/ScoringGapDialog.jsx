import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  FormLabel,
  Chip,
  Paper,
} from '@mui/material';
import {
  Warning,
  CheckCircle,
  ArrowForward,
  ArrowBack,
  Close,
  HelpOutline,
} from '@mui/icons-material';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { initiativesApi } from '../api/initiatives';

/**
 * ScoringGapDialog - Multi-step wizard for filling scoring data gaps.
 *
 * Workflow:
 * 1. Show gap analysis summary
 * 2. For each gap question, collect estimated answer + confidence
 * 3. Submit all answers
 * 4. Trigger score recalculation
 */
export default function ScoringGapDialog({ open, onClose, gapAnalysis, initiativeId }) {
  const storageKey = `gap-answers-${initiativeId}`;

  // Load saved answers from localStorage on mount
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });
  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  // Flatten gap questions into a single array
  const allQuestions = gapAnalysis?.blocking_gaps?.flatMap((gap) =>
    gap.questions.map((q) => ({
      ...q,
      framework: gap.framework,
      component: gap.component,
      issue_summary: gap.issue_summary,
    }))
  ) || [];

  const totalSteps = allQuestions.length + 1; // +1 for summary step
  const isSummaryStep = currentStep === 0;
  const isLastQuestionStep = currentStep === allQuestions.length;

  // Mutation to submit gap question answer
  const submitAnswerMutation = useMutation({
    mutationFn: ({ questionId, answerText, confidence }) =>
      initiativesApi.answerGapQuestion(initiativeId, questionId, answerText, confidence),
  });

  const handleAnswerChange = (questionIndex, field, value) => {
    setAnswers((prev) => {
      const updated = {
        ...prev,
        [questionIndex]: {
          ...prev[questionIndex],
          [field]: value,
        },
      };
      // Save to localStorage whenever answers change
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch (e) {
        console.error('Failed to save answers to localStorage:', e);
      }
      return updated;
    });
  };

  const handleNext = () => {
    // Validate current question has answer and confidence
    if (!isSummaryStep) {
      const questionIndex = currentStep - 1;
      const answer = answers[questionIndex];

      if (!answer?.answer_text?.trim()) {
        setError('Please provide an estimated answer');
        // Scroll to top to show the error
        setTimeout(() => {
          document.querySelector('.MuiDialogContent-root')?.scrollTo({ top: 0, behavior: 'smooth' });
        }, 100);
        return;
      }

      if (!answer?.confidence) {
        setError('Please select a confidence level');
        // Scroll to confidence selector
        setTimeout(() => {
          document.querySelector('.MuiDialogContent-root')?.scrollTo({ top: document.querySelector('.MuiDialogContent-root')?.scrollHeight || 0, behavior: 'smooth' });
        }, 100);
        return;
      }
    }

    setError('');
    setCurrentStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setError('');
    setCurrentStep((prev) => prev - 1);
  };

  const handleSubmit = async () => {
    setError('');

    try {
      // Submit all answers sequentially
      for (let i = 0; i < allQuestions.length; i++) {
        const question = allQuestions[i];
        const answer = answers[i];

        if (answer?.answer_text && answer?.confidence) {
          await submitAnswerMutation.mutateAsync({
            questionId: question.question_id,
            answerText: answer.answer_text,
            confidence: answer.confidence,
          });
        }
      }

      // Clear saved answers from localStorage on success
      try {
        localStorage.removeItem(storageKey);
      } catch (e) {
        console.error('Failed to clear saved answers:', e);
      }

      // Close dialog and signal success - parent will handle score calculation
      onClose(true);
    } catch (err) {
      setError(err.message || 'Failed to submit answers');
    }
  };

  const renderSummaryStep = () => {
    // Count how many questions already have answers saved
    const answeredCount = Object.keys(answers).filter(
      (key) => answers[key]?.answer_text && answers[key]?.confidence
    ).length;
    const hasProgress = answeredCount > 0;

    // Determine if this is for confidence improvement or missing data
    const currentConfidence = gapAnalysis?.current_confidence;
    const isImprovingConfidence = currentConfidence !== undefined && currentConfidence < 80;

    return (
      <Box sx={{ textAlign: 'center', py: 2 }}>
        {/* Icon and main message */}
        <Box sx={{ mb: 3 }}>
          <Warning sx={{ fontSize: 64, color: isImprovingConfidence ? 'info.main' : 'warning.main', mb: 2 }} />
          <Typography variant="h5" fontWeight="600" gutterBottom>
            {isImprovingConfidence
              ? `Improve Confidence (Currently ${currentConfidence}%)`
              : `We Need ${allQuestions.length} More Data Point${allQuestions.length > 1 ? 's' : ''}`}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 500, mx: 'auto' }}>
            {isImprovingConfidence
              ? 'Answer these questions to increase your RICE confidence score and get more reliable estimates.'
              : 'To calculate your RICE and FDV scores, we\'re missing some key quantitative data. Don\'t worry - rough estimates will work!'}
          </Typography>
          {hasProgress && (
            <Alert severity="success" sx={{ mt: 2, mx: 'auto', maxWidth: 500 }}>
              <Typography variant="body2">
                <strong>Progress saved:</strong> You've answered {answeredCount} of {allQuestions.length} questions. Click continue to pick up where you left off.
              </Typography>
            </Alert>
          )}
        </Box>

      {/* Simplified gap preview */}
      <Box sx={{ mb: 3, mx: 'auto', maxWidth: 600 }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontWeight: 600 }}>
          Missing information for:
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'center' }}>
          {gapAnalysis?.blocking_gaps?.map((gap, index) => (
            <Chip
              key={index}
              label={`${gap.framework} ${gap.component}`}
              size="small"
              color={gap.framework === 'RICE' ? 'primary' : 'secondary'}
              variant="outlined"
            />
          ))}
        </Box>
      </Box>

      {/* What happens next */}
      <Paper elevation={2} sx={{ p: 3, mb: 3, mx: 'auto', maxWidth: 500, bgcolor: 'primary.50' }}>
        <Typography variant="body2" fontWeight="600" gutterBottom>
          What Happens Next:
        </Typography>
        <Box component="ol" sx={{ textAlign: 'left', pl: 2, m: 0 }}>
          <Typography component="li" variant="body2" sx={{ mb: 1 }}>
            Answer {allQuestions.length} quick question{allQuestions.length > 1 ? 's' : ''} (rough estimates are fine)
          </Typography>
          <Typography component="li" variant="body2" sx={{ mb: 1 }}>
            We'll calculate your scores with a confidence adjustment
          </Typography>
          <Typography component="li" variant="body2">
            You can refine your estimates anytime later
          </Typography>
        </Box>
      </Paper>

        {/* Impact note */}
        <Alert severity="info" sx={{ mx: 'auto', maxWidth: 500 }}>
          <Typography variant="caption">
            <strong>Impact:</strong> Estimated answers will reduce RICE Confidence by{' '}
            {Math.min(30, allQuestions.length * 10)}% to reflect uncertainty.
          </Typography>
        </Alert>
      </Box>
    );
  };

  const renderQuestionStep = () => {
    const questionIndex = currentStep - 1;
    const question = allQuestions[questionIndex];
    const answer = answers[questionIndex] || {};

    return (
      <Box>
        {/* Context chips */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Chip
            label={question.framework}
            size="small"
            color={question.framework === 'RICE' ? 'primary' : 'secondary'}
          />
          <Chip label={question.component} size="small" variant="outlined" />
        </Box>

        {/* Question */}
        <Typography variant="h5" fontWeight="600" gutterBottom sx={{ mb: 3 }}>
          {question.text}
        </Typography>

        {/* Helpful context */}
        {question.hint && (
          <Paper elevation={0} sx={{ p: 2, mb: 3, bgcolor: 'info.50', border: '1px solid', borderColor: 'info.200' }}>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
              <HelpOutline sx={{ color: 'info.main', fontSize: 20, mt: 0.5 }} />
              <Box>
                <Typography variant="body2" fontWeight="600" color="info.dark" gutterBottom>
                  Helpful Context:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {question.hint}
                </Typography>
              </Box>
            </Box>
          </Paper>
        )}

        {/* Example */}
        {question.example_answer && (
          <Box sx={{ mb: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1, borderLeft: '3px solid', borderColor: 'grey.400' }}>
            <Typography variant="caption" color="text.secondary" fontWeight="600" gutterBottom display="block">
              Example:
            </Typography>
            <Typography variant="body2" fontStyle="italic" color="text.secondary">
              "{question.example_answer}"
            </Typography>
          </Box>
        )}

        {/* Answer input */}
        <TextField
          fullWidth
          multiline
          rows={4}
          label="Your Best Estimate"
          placeholder="Don't worry about being exact - a rough estimate is perfectly fine..."
          value={answer.answer_text || ''}
          onChange={(e) => {
            handleAnswerChange(questionIndex, 'answer_text', e.target.value);
            setError(''); // Clear error when user starts typing
          }}
          sx={{ mb: 3 }}
          required
          error={error && !answer?.answer_text?.trim()}
          helperText={error && !answer?.answer_text?.trim() ? error : ''}
        />

        {/* Confidence selector */}
        <Paper
          elevation={0}
          sx={{
            p: 2,
            bgcolor: 'grey.50',
            ...(error && !answer.confidence && {
              border: '2px solid',
              borderColor: 'error.main',
              bgcolor: 'error.50',
            })
          }}
        >
          <FormControl component="fieldset" fullWidth error={error && !answer.confidence}>
            <FormLabel component="legend" required>
              <Typography variant="body2" fontWeight="600" gutterBottom>
                How confident are you in this estimate? *
              </Typography>
            </FormLabel>
            {error && !answer.confidence && (
              <Alert severity="error" sx={{ mb: 2, mt: 1 }}>
                {error}
              </Alert>
            )}
            <RadioGroup
              row
              value={answer.confidence || ''}
              onChange={(e) => {
                handleAnswerChange(questionIndex, 'confidence', e.target.value);
                setError(''); // Clear error when user selects confidence
              }}
              sx={{ gap: 2, mt: 1 }}
            >
              <FormControlLabel
                value="Low"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2" fontWeight="600">Low</Typography>
                    <Typography variant="caption" color="text.secondary">Rough guess</Typography>
                  </Box>
                }
              />
              <FormControlLabel
                value="Medium"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2" fontWeight="600">Medium</Typography>
                    <Typography variant="caption" color="text.secondary">Informed estimate</Typography>
                  </Box>
                }
              />
              <FormControlLabel
                value="High"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2" fontWeight="600">High</Typography>
                    <Typography variant="caption" color="text.secondary">Based on data</Typography>
                  </Box>
                }
              />
            </RadioGroup>
          </FormControl>
        </Paper>
      </Box>
    );
  };

  return (
    <Dialog
      open={open}
      onClose={() => onClose(false)}
      maxWidth="md"
      fullWidth
      PaperProps={{ sx: { minHeight: '60vh' } }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">
            {isSummaryStep
              ? 'Almost There!'
              : `Question ${currentStep} of ${allQuestions.length}`}
          </Typography>
          <Button onClick={() => onClose(false)} size="small" sx={{ minWidth: 'auto' }}>
            <Close />
          </Button>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {/* Simplified progress indicator */}
        {!isSummaryStep && (
          <Box sx={{ mb: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Question {currentStep} of {allQuestions.length}
            </Typography>
          </Box>
        )}

        {isSummaryStep && renderSummaryStep()}
        {!isSummaryStep && renderQuestionStep()}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2, justifyContent: 'space-between' }}>
        {!isSummaryStep && (
          <Button startIcon={<ArrowBack />} onClick={handleBack} size="large">
            Back
          </Button>
        )}

        {isSummaryStep && (
          <Button onClick={() => onClose(false)} size="large">
            Skip for Now
          </Button>
        )}

        <Box sx={{ flex: '1 1 auto' }} />

        {!isLastQuestionStep && (
          <Button
            variant="contained"
            size="large"
            endIcon={<ArrowForward />}
            onClick={handleNext}
          >
            {isSummaryStep ? 'Let\'s Fill the Gaps' : 'Next'}
          </Button>
        )}

        {isLastQuestionStep && (
          <Button
            variant="contained"
            color="success"
            size="large"
            startIcon={submitAnswerMutation.isPending ? <CircularProgress size={20} /> : <CheckCircle />}
            onClick={handleSubmit}
            disabled={submitAnswerMutation.isPending}
          >
            {submitAnswerMutation.isPending ? 'Calculating...' : 'Calculate My Scores'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
