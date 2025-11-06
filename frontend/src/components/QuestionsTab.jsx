import { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  CircularProgress,
  Alert,
  LinearProgress,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
} from '@mui/material';
import {
  ExpandMore,
  CheckCircle,
  Help,
  Block,
  Edit,
  AutoAwesome,
  Refresh,
  Assessment,
} from '@mui/icons-material';
import { useQuestions } from '../hooks/useQuestions';
import { useGenerateQuestions } from '../hooks/useInitiatives';
import AnswerDialog from './AnswerDialog';

// Category options
const categoryOptions = [
  { value: '', label: 'All Categories' },
  { value: 'Business_Dev', label: 'Business Development' },
  { value: 'Technical', label: 'Technical' },
  { value: 'Product', label: 'Product' },
  { value: 'Operations', label: 'Operations' },
  { value: 'Financial', label: 'Financial' },
];

// Priority options
const priorityOptions = [
  { value: '', label: 'All Priorities' },
  { value: 'P0', label: 'P0 - Critical' },
  { value: 'P1', label: 'P1 - Important' },
  { value: 'P2', label: 'P2 - Optional' },
];

// Category colors
const categoryColors = {
  Business_Dev: 'primary',
  Technical: 'secondary',
  Product: 'info',
  Operations: 'warning',
  Financial: 'error',
};

// Priority colors
const priorityColors = {
  P0: 'error',
  P1: 'warning',
  P2: 'info',
};

// Answer type colors (keys must match backend enum: title case)
const answerTypeColors = {
  Answered: 'success',
  Unknown: 'warning',
  Skipped: 'default',
};

export default function QuestionsTab({ initiativeId, onNavigateToEvaluation }) {
  const [categoryFilter, setCategoryFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [currentTab, setCurrentTab] = useState(0); // 0 = Unanswered, 1 = Answered
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [answerDialogOpen, setAnswerDialogOpen] = useState(false);
  const [regenerateDialogOpen, setRegenerateDialogOpen] = useState(false);
  const [keepUnanswered, setKeepUnanswered] = useState(true);
  const [expandedAccordions, setExpandedAccordions] = useState({});

  const { data: questions, isLoading, error } = useQuestions(initiativeId);
  const generateQuestions = useGenerateQuestions();

  // Separate answered and unanswered questions
  const unansweredQuestions = questions?.filter((q) => !q.answer) || [];
  const answeredQuestions = questions?.filter((q) => q.answer) || [];

  // Filter questions based on tab
  const tabQuestions = currentTab === 0 ? unansweredQuestions : answeredQuestions;

  // Filter questions based on filters
  const filteredQuestions = tabQuestions.filter((q) => {
    const matchesCategory = !categoryFilter || q.category === categoryFilter;
    const matchesPriority = !priorityFilter || q.priority === priorityFilter;
    return matchesCategory && matchesPriority;
  });

  // Calculate progress
  const totalQuestions = questions?.length || 0;
  const answeredCount =
    questions?.filter((q) => q.answer?.answer_status === 'Answered').length || 0;
  const unknownCount =
    questions?.filter((q) => q.answer?.answer_status === 'Unknown').length || 0;
  const skippedCount =
    questions?.filter((q) => q.answer?.answer_status === 'Skipped').length || 0;
  const unansweredCount = totalQuestions - answeredCount - unknownCount - skippedCount;

  const progressPercentage =
    totalQuestions > 0
      ? Math.round(((answeredCount + unknownCount + skippedCount) / totalQuestions) * 100)
      : 0;

  // Group questions by category
  const questionsByCategory = filteredQuestions.reduce((acc, question) => {
    const category = question.category;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(question);
    return acc;
  }, {});

  const handleAnswerClick = (question) => {
    setSelectedQuestion(question);
    setAnswerDialogOpen(true);
  };

  const handleAnswerDialogClose = () => {
    setAnswerDialogOpen(false);
    setSelectedQuestion(null);
  };

  const handleAccordionChange = (questionId, question) => (event, isExpanded) => {
    setExpandedAccordions((prev) => ({
      ...prev,
      [questionId]: isExpanded,
    }));

    // If expanding an unanswered question, immediately open the answer dialog
    if (isExpanded && !question.answer) {
      setSelectedQuestion(question);
      setAnswerDialogOpen(true);
    }
  };

  const handleGenerateQuestions = async () => {
    try {
      await generateQuestions.mutateAsync(initiativeId);
    } catch (err) {
      // Error handling is done in the hook
    }
  };

  const handleRegenerateQuestions = async () => {
    try {
      await generateQuestions.mutateAsync({
        id: initiativeId,
        keepUnanswered,
      });
      setRegenerateDialogOpen(false);
    } catch (err) {
      // Error handling is done in the hook
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error">
        Failed to load questions: {error.message}
      </Alert>
    );
  }

  if (!questions || questions.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 6 }}>
        <AutoAwesome sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          No Questions Yet
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Generate AI-powered discovery questions to understand this initiative better
        </Typography>
        <Button
          variant="contained"
          startIcon={<AutoAwesome />}
          onClick={handleGenerateQuestions}
          disabled={generateQuestions.isPending}
        >
          {generateQuestions.isPending ? 'Generating...' : 'Generate Questions'}
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Progress Section */}
      <Card elevation={2} sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" fontWeight="600">
              Question Progress
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              {onNavigateToEvaluation && answeredQuestions.length > 0 && (
                <Button
                  variant="contained"
                  startIcon={<Assessment />}
                  onClick={onNavigateToEvaluation}
                  color="primary"
                >
                  Assess Readiness
                </Button>
              )}
              <Button
                startIcon={<Refresh />}
                onClick={() => setRegenerateDialogOpen(true)}
                disabled={generateQuestions.isPending}
              >
                Regenerate
              </Button>
            </Box>
          </Box>

          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                {answeredCount + unknownCount + skippedCount} of {totalQuestions} completed
              </Typography>
              <Typography variant="body2" fontWeight="600">
                {progressPercentage}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={progressPercentage}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={6} sm={3}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" fontWeight="600" color="success.main">
                  {answeredCount}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Answered
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" fontWeight="600" color="warning.main">
                  {unknownCount}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Unknown
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" fontWeight="600" color="text.secondary">
                  {skippedCount}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Skipped
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" fontWeight="600" color="error.main">
                  {unansweredCount}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Unanswered
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Tabs for Unanswered/Answered */}
      <Card elevation={2} sx={{ mb: 3 }}>
        <Tabs
          value={currentTab}
          onChange={(e, newValue) => setCurrentTab(newValue)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab
            label={`Unanswered (${unansweredQuestions.length})`}
            icon={<Block fontSize="small" />}
            iconPosition="start"
          />
          <Tab
            label={`Answered (${answeredQuestions.length})`}
            icon={<CheckCircle fontSize="small" />}
            iconPosition="start"
          />
        </Tabs>

        {/* Filters */}
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Category</InputLabel>
              <Select
                value={categoryFilter}
                label="Category"
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                {categoryOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Priority</InputLabel>
              <Select
                value={priorityFilter}
                label="Priority"
                onChange={(e) => setPriorityFilter(e.target.value)}
              >
                {priorityOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </CardContent>
      </Card>

      {/* Questions List */}
      {filteredQuestions.length === 0 ? (
        <Card elevation={2}>
          <CardContent>
            <Typography variant="body1" color="text.secondary" textAlign="center" sx={{ py: 4 }}>
              {currentTab === 0
                ? 'No unanswered questions match your filters'
                : 'No answered questions match your filters'}
            </Typography>
          </CardContent>
        </Card>
      ) : (
        Object.entries(questionsByCategory).map(([category, categoryQuestions]) => (
          <Card key={category} elevation={2} sx={{ mb: 2 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Typography variant="h6" fontWeight="600">
                  {category.replace('_', ' ')}
                </Typography>
                <Chip
                  label={`${categoryQuestions.length} questions`}
                  size="small"
                  color={categoryColors[category]}
                />
              </Box>

              {categoryQuestions.map((question) => (
                <Accordion
                  key={question.id}
                  expanded={expandedAccordions[question.id] || false}
                  onChange={handleAccordionChange(question.id, question)}
                >
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1, mr: 2 }}>
                      {question.answer?.answer_status === 'Answered' && (
                        <CheckCircle fontSize="small" color="success" />
                      )}
                      {question.answer?.answer_status === 'Unknown' && (
                        <Help fontSize="small" color="warning" />
                      )}
                      {question.answer?.answer_status === 'Skipped' && (
                        <Block fontSize="small" color="disabled" />
                      )}
                      <Typography sx={{ flex: 1 }}>{question.question_text}</Typography>
                      <Chip
                        label={question.priority}
                        size="small"
                        color={priorityColors[question.priority]}
                      />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    {question.answer ? (
                      <>
                        <Box sx={{ mb: 2, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
                          <Typography variant="body2" fontWeight="500" gutterBottom>
                            Answer:
                          </Typography>
                          <Typography variant="body2">{question.answer.answer_text}</Typography>
                          {question.answer.answer_status && (
                            <Chip
                              label={question.answer.answer_status}
                              size="small"
                              color={answerTypeColors[question.answer.answer_status]}
                              sx={{ mt: 1 }}
                            />
                          )}
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Typography variant="caption" color="text.secondary">
                            Iteration {question.iteration}
                          </Typography>
                          <Button
                            startIcon={<Edit />}
                            size="small"
                            onClick={() => handleAnswerClick(question)}
                          >
                            Edit Answer
                          </Button>
                        </Box>
                      </>
                    ) : (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="caption" color="text.secondary">
                          Iteration {question.iteration}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" fontStyle="italic">
                          Click to answer this question
                        </Typography>
                      </Box>
                    )}
                  </AccordionDetails>
                </Accordion>
              ))}
            </CardContent>
          </Card>
        ))
      )}

      {/* Answer Dialog */}
      <AnswerDialog
        open={answerDialogOpen}
        onClose={handleAnswerDialogClose}
        question={selectedQuestion}
        initiativeId={initiativeId}
      />

      {/* Regenerate Dialog */}
      <Dialog open={regenerateDialogOpen} onClose={() => setRegenerateDialogOpen(false)}>
        <DialogTitle>Regenerate Questions</DialogTitle>
        <DialogContent>
          <Typography variant="body2" paragraph>
            This will generate a new set of discovery questions based on the current initiative
            details and any previous answers.
          </Typography>
          <Alert severity="warning" sx={{ mb: 2 }}>
            Note: This may take a few moments to complete.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRegenerateDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleRegenerateQuestions}
            disabled={generateQuestions.isPending}
          >
            {generateQuestions.isPending ? 'Regenerating...' : 'Regenerate'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
