import { useState, useEffect, useImperativeHandle, forwardRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Grid,
  LinearProgress,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  CheckCircle,
  Warning,
  Error,
  AutoAwesome,
  Description,
  TrendingUp,
  Assessment,
  QuestionAnswer,
  ArrowForward,
} from '@mui/icons-material';
import apiClient from '../api/client';
import { useJobPolling } from '../hooks/useJobPolling';
import JobProgressModal from './JobProgressModal';

const EvaluationTab = forwardRef(function EvaluationTab({ initiativeId, onNavigateToMRD, onNavigateToQuestions }, ref) {
  const [evaluation, setEvaluation] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generatedQuestionsCount, setGeneratedQuestionsCount] = useState(null);
  const [showSuccessDialog, setShowSuccessDialog] = useState(false);

  // Job polling state
  const [questionJobId, setQuestionJobId] = useState(null);
  const [evalJobId, setEvalJobId] = useState(null);

  // Question generation job polling
  const questionJobPolling = useJobPolling(questionJobId, {
    onComplete: (resultData) => {
      setQuestionJobId(null);
      setGeneratedQuestionsCount(resultData.questions_count);
      setShowSuccessDialog(true);
    },
    onError: (error) => {
      setQuestionJobId(null);
      setError(error.message);
    }
  });

  // Evaluation job polling
  const evalJobPolling = useJobPolling(evalJobId, {
    onComplete: async (resultData) => {
      setEvalJobId(null);
      // Fetch the evaluation data
      try {
        const response = await apiClient.get(
          `/api/agents/initiatives/${initiativeId}/evaluate-readiness`
        );
        setEvaluation(response.data);
      } catch (err) {
        setError('Failed to load evaluation results');
      }
    },
    onError: (error) => {
      setEvalJobId(null);
      setError(error.message);
    }
  });

  // Load existing evaluation on mount
  useEffect(() => {
    const loadExistingEvaluation = async () => {
      setIsLoading(true);
      try {
        const response = await apiClient.get(
          `/api/agents/initiatives/${initiativeId}/evaluate-readiness`
        );
        setEvaluation(response.data);
      } catch (err) {
        // 404 is expected if no evaluation exists yet
        if (err.response?.status !== 404) {
          console.error('Error loading evaluation:', err);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadExistingEvaluation();
  }, [initiativeId]);

  const handleEvaluateReadiness = async () => {
    setError(null);
    setGeneratedQuestionsCount(null); // Clear success dialog data when re-evaluating
    setShowSuccessDialog(false);
    try {
      const response = await apiClient.post(
        `/api/agents/initiatives/${initiativeId}/evaluate-readiness`
      );
      // Response contains job_id
      setEvalJobId(response.data.job_id);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to start readiness evaluation');
    }
  };

  // Expose triggerEvaluation method to parent via ref
  useImperativeHandle(ref, () => ({
    triggerEvaluation: handleEvaluateReadiness
  }));

  const handleGenerateMoreQuestions = async () => {
    setError(null);
    try {
      const response = await apiClient.post(
        `/api/agents/initiatives/${initiativeId}/generate-questions`
      );
      // Response contains job_id
      setQuestionJobId(response.data.job_id);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to start question generation');
    }
  };

  const handleCloseSuccessDialog = () => {
    setShowSuccessDialog(false);
  };

  const handleGoToQuestions = () => {
    setShowSuccessDialog(false);
    if (onNavigateToQuestions) {
      onNavigateToQuestions();
    }
  };

  const handleReEvaluate = () => {
    setShowSuccessDialog(false);
    handleEvaluateReadiness();
  };

  const handleProceedToMRD = () => {
    if (onNavigateToMRD) {
      onNavigateToMRD();
    }
  };

  // Show loading state on initial load
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const isEvaluating = evalJobPolling.isPolling;
  const isGeneratingQuestions = questionJobPolling.isPolling;

  // Show empty state with button to trigger evaluation
  if (!evaluation) {
    return (
      <Box>
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Assessment sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            Evaluate MRD Readiness
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph sx={{ maxWidth: 600, mx: 'auto' }}>
            Run an AI-powered analysis to assess whether your initiative has enough information
            to generate a high-quality Market Requirements Document.
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph sx={{ maxWidth: 600, mx: 'auto' }}>
            The AI will analyze all Q&A data, identify knowledge gaps, and recommend next steps.
          </Typography>
          <Button
            variant="contained"
            size="large"
            startIcon={<Assessment />}
            onClick={handleEvaluateReadiness}
            sx={{ mt: 2 }}
          >
            Evaluate Readiness
          </Button>
        </Box>
      </Box>
    );
  }

  // Determine risk icon and color
  const getRiskDisplay = () => {
    const risk = evaluation.risk_level;
    if (risk === 'Low') return { icon: <CheckCircle />, color: 'success' };
    if (risk === 'Medium') return { icon: <Warning />, color: 'warning' };
    return { icon: <Error />, color: 'error' };
  };

  const riskDisplay = getRiskDisplay();

  // Determine if should recommend more questions or proceed
  const shouldGenerateMore = evaluation.recommendations?.action === 'generate_more_questions';

  return (
    <Box>
      {/* Overall Readiness Score */}
      <Card elevation={2} sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight="600" gutterBottom>
            MRD Readiness Assessment
          </Typography>

          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h2" fontWeight="700" color={riskDisplay.color}>
                  {evaluation.readiness_score}%
                </Typography>
                <Typography variant="body1" color="text.secondary" gutterBottom>
                  {evaluation.readiness_level}
                </Typography>
                <Chip
                  icon={riskDisplay.icon}
                  label={`${evaluation.risk_level} Risk`}
                  color={riskDisplay.color}
                  sx={{ mt: 1 }}
                />
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="body2" fontWeight="600" gutterBottom>
                AI Analysis Summary
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {evaluation.summary}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Missing Critical Information */}
      {evaluation.missing_critical_info && evaluation.missing_critical_info.length > 0 && (
        <Card elevation={2} sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight="600" gutterBottom>
              Missing Critical Information
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              The following knowledge gaps were identified by AI analysis
            </Typography>

            <List>
              {evaluation.missing_critical_info.map((gap, index) => (
                <Box key={index}>
                  <ListItem sx={{ px: 0, alignItems: 'flex-start' }}>
                    <ListItemIcon sx={{ mt: 0.5 }}>
                      {gap.severity === 'High' && <Error color="error" />}
                      {gap.severity === 'Medium' && <Warning color="warning" />}
                      {gap.severity === 'Low' && <Warning color="info" />}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                          <Chip label={gap.category} size="small" />
                          <Chip label={gap.severity} size="small" color={
                            gap.severity === 'High' ? 'error' : gap.severity === 'Medium' ? 'warning' : 'info'
                          } />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" fontWeight="600" sx={{ mt: 1 }}>
                            {gap.gap}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            Impact: {gap.impact}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < evaluation.missing_critical_info.length - 1 && <Divider />}
                </Box>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Weak MRD Sections */}
      {evaluation.weak_mrd_sections && evaluation.weak_mrd_sections.length > 0 && (
        <Card elevation={2} sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight="600" gutterBottom>
              MRD Sections at Risk
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              These sections will be incomplete or require significant assumptions
            </Typography>

            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {evaluation.weak_mrd_sections.map((section, index) => (
                <Chip key={index} label={section} color="warning" variant="outlined" />
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Required Assumptions */}
      {evaluation.required_assumptions && evaluation.required_assumptions.length > 0 && (
        <Card elevation={2} sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight="600" gutterBottom>
              Required Assumptions
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              If you proceed to MRD, these assumptions will be documented
            </Typography>

            <List dense>
              {evaluation.required_assumptions.map((assumption, index) => (
                <ListItem key={index} sx={{ px: 0 }}>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <Warning fontSize="small" color="warning" />
                  </ListItemIcon>
                  <ListItemText
                    primary={assumption}
                    primaryTypographyProps={{ variant: 'body2' }}
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      <Card elevation={2} sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight="600" gutterBottom>
            AI Recommendation
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            {evaluation.recommendations?.reasoning}
          </Typography>

          {evaluation.recommendations?.if_more_questions && evaluation.recommendations.if_more_questions.length > 0 && (
            <Box sx={{ mt: 2, p: 2, bgcolor: 'info.50', borderRadius: 1 }}>
              <Typography variant="body2" fontWeight="600" gutterBottom>
                If you generate more questions, focus on:
              </Typography>
              <List dense>
                {evaluation.recommendations.if_more_questions.map((topic, index) => (
                  <ListItem key={index} sx={{ px: 0, py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <Assessment fontSize="small" color="info" />
                    </ListItemIcon>
                    <ListItemText
                      primary={topic}
                      primaryTypographyProps={{ variant: 'body2' }}
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <Card elevation={2}>
        <CardContent>
          <Typography variant="h6" fontWeight="600" gutterBottom>
            Next Steps
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Choose your next action based on the AI assessment
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Paper
                elevation={0}
                sx={{
                  p: 3,
                  border: 2,
                  borderColor: shouldGenerateMore ? 'primary.main' : 'divider',
                  bgcolor: shouldGenerateMore ? 'primary.50' : 'background.paper',
                  textAlign: 'center',
                }}
              >
                <AutoAwesome sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
                <Typography variant="h6" gutterBottom>
                  Generate More Questions
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  AI will analyze gaps and create 3-8 targeted follow-up questions
                </Typography>
                <Button
                  variant={shouldGenerateMore ? 'contained' : 'outlined'}
                  startIcon={<TrendingUp />}
                  fullWidth
                  onClick={handleGenerateMoreQuestions}
                  disabled={isGeneratingQuestions}
                >
                  {isGeneratingQuestions ? 'Generating...' : 'Generate Questions'}
                </Button>
                {shouldGenerateMore && (
                  <Chip
                    label="Recommended"
                    color="primary"
                    size="small"
                    sx={{ mt: 1 }}
                  />
                )}
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper
                elevation={0}
                sx={{
                  p: 3,
                  border: 2,
                  borderColor: !shouldGenerateMore ? 'success.main' : 'divider',
                  bgcolor: !shouldGenerateMore ? 'success.50' : 'background.paper',
                  textAlign: 'center',
                }}
              >
                <Description sx={{ fontSize: 48, color: 'success.main', mb: 1 }} />
                <Typography variant="h6" gutterBottom>
                  Proceed to MRD
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Generate the MRD with current knowledge and documented assumptions
                </Typography>
                <Button
                  variant={!shouldGenerateMore ? 'contained' : 'outlined'}
                  color="success"
                  startIcon={<Description />}
                  fullWidth
                  onClick={handleProceedToMRD}
                >
                  Go to MRD
                </Button>
                {!shouldGenerateMore && (
                  <Chip
                    label="Recommended"
                    color="success"
                    size="small"
                    sx={{ mt: 1 }}
                  />
                )}
              </Paper>
            </Grid>
          </Grid>

          {evaluation.readiness_score < 60 && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Note: Proceeding with significant knowledge gaps may result in an MRD with many assumptions and uncertainties. Consider generating more questions first.
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Job progress modals */}
      <JobProgressModal
        open={isGeneratingQuestions}
        title="Generating Questions"
        progressMessage={questionJobPolling.progressMessage}
        progressPercent={questionJobPolling.progress}
      />

      <JobProgressModal
        open={isEvaluating}
        title="Evaluating Readiness"
        progressMessage={evalJobPolling.progressMessage}
        progressPercent={evalJobPolling.progress}
      />

      {/* Success modal after questions are generated */}
      <Dialog
        open={showSuccessDialog}
        onClose={handleCloseSuccessDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CheckCircle color="success" />
            <Typography variant="h6">Questions Generated Successfully!</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" paragraph>
            {generatedQuestionsCount} {generatedQuestionsCount === 1 ? 'question has' : 'questions have'} been created based on your initiative's knowledge gaps.
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            What would you like to do next?
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 3 }}>
            <Paper
              elevation={0}
              sx={{
                p: 2,
                border: 1,
                borderColor: 'primary.main',
                bgcolor: 'primary.50',
                cursor: 'pointer',
                '&:hover': { bgcolor: 'primary.100' }
              }}
              onClick={handleGoToQuestions}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <QuestionAnswer color="primary" sx={{ fontSize: 40 }} />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1" fontWeight="600">
                    Answer New Questions
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Go to the Questions tab to review and answer the newly generated questions
                  </Typography>
                </Box>
                <ArrowForward color="primary" />
              </Box>
            </Paper>

            <Paper
              elevation={0}
              sx={{
                p: 2,
                border: 1,
                borderColor: 'divider',
                cursor: 'pointer',
                '&:hover': { bgcolor: 'action.hover' }
              }}
              onClick={handleReEvaluate}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Assessment color="action" sx={{ fontSize: 40 }} />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1" fontWeight="600">
                    Re-evaluate Readiness
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Get an updated readiness assessment based on all your current answers
                  </Typography>
                </Box>
                <ArrowForward />
              </Box>
            </Paper>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseSuccessDialog}>Stay Here</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
});

export default EvaluationTab;
