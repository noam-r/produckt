import { useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Breadcrumbs,
  Link,
  IconButton,
  Menu,
  MenuItem,
  Stepper,
  Step,
  StepLabel,
  Paper,
  LinearProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack,
  Edit,
  MoreVert,
  Delete,
  AutoAwesome,
  CheckCircle,
  Description,
  Assessment,
  ArrowForward,
  HelpOutline,
  Refresh,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useInitiative, useDeleteInitiative, useGenerateQuestions } from '../hooks/useInitiatives';
import { useQuestions } from '../hooks/useQuestions';
import { initiativesApi } from '../api/initiatives';
import { authApi } from '../api/auth';
import MainLayout from '../layouts/MainLayout';
import QuestionsTab from '../components/QuestionsTab';
import EvaluationTab from '../components/EvaluationTab';
import MRDTab from '../components/MRDTab';
import ScoresTab from '../components/ScoresTab';

// Status color mapping
const statusColors = {
  DRAFT: 'default',
  IN_DISCOVERY: 'info',
  IN_QA: 'warning',
  READY_FOR_MRD: 'secondary',
  COMPLETED: 'success',
};

// Workflow steps
const workflowSteps = [
  { label: 'Initiative Created', key: 'created' },
  { label: 'Questions Generated', key: 'questions' },
  { label: 'Questions Answered', key: 'answered' },
  { label: 'Readiness Evaluated', key: 'evaluated' },
  { label: 'MRD Generated', key: 'mrd' },
  { label: 'Scored', key: 'scored' },
];

// Tab panels
function TabPanel({ children, value, index }) {
  return (
    <Box
      role="tabpanel"
      hidden={value !== index}
      sx={{ py: 3 }}
    >
      {value === index && children}
    </Box>
  );
}

export default function InitiativeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [currentTab, setCurrentTab] = useState(0);
  const [anchorEl, setAnchorEl] = useState(null);
  const evaluationTabRef = useRef(null);

  const { data: initiative, isLoading, error } = useInitiative(id);
  const { data: questions } = useQuestions(id);
  const deleteInitiative = useDeleteInitiative();
  const generateQuestions = useGenerateQuestions();

  // Fetch user budget status
  const { data: userProfile } = useQuery({
    queryKey: ['userProfile'],
    queryFn: authApi.getProfile,
  });

  // Recalculate quality score mutation
  const recalculateQuality = useMutation({
    mutationFn: () => initiativesApi.recalculateQuality(id),
    onSuccess: () => {
      // Invalidate and refetch initiative data
      queryClient.invalidateQueries(['initiative', id]);
    },
  });

  // Fetch evaluation, MRD, and scores for progress tracking
  const { data: evaluation } = useQuery({
    queryKey: ['evaluation', id],
    queryFn: () => initiativesApi.getEvaluation(id),
    retry: false,
    enabled: !!id,
  });

  const { data: mrd } = useQuery({
    queryKey: ['mrd', id],
    queryFn: () => initiativesApi.getMRD(id),
    retry: false,
    enabled: !!id,
  });

  const { data: scores } = useQuery({
    queryKey: ['scores', id],
    queryFn: () => initiativesApi.getScores(id),
    retry: false,
    enabled: !!id,
  });

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  const handleNavigateAndEvaluate = () => {
    setCurrentTab(2); // Navigate to Evaluation tab
    // Trigger evaluation after a short delay to ensure tab is rendered
    setTimeout(() => {
      if (evaluationTabRef.current?.triggerEvaluation) {
        evaluationTabRef.current.triggerEvaluation();
      }
    }, 100);
  };

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleEdit = () => {
    handleMenuClose();
    navigate(`/initiatives/${id}/edit`);
  };

  const handleDelete = async () => {
    handleMenuClose();
    if (window.confirm('Are you sure you want to delete this initiative?')) {
      try {
        await deleteInitiative.mutateAsync(id);
        navigate('/initiatives');
      } catch (err) {
        alert('Failed to delete initiative');
      }
    }
  };

  const handleGenerateQuestions = async () => {
    try {
      await generateQuestions.mutateAsync(id);
    } catch (err) {
      // Error handled by hook
    }
  };

  // Calculate workflow progress
  const getWorkflowProgress = () => {
    if (!initiative) return { activeStep: 0, qualityScore: 0, workflowCompletion: 0 };

    const hasQuestions = questions && questions.length > 0;
    const answeredCount = questions?.filter((q) => q.answer?.answer_status === 'Answered').length || 0;
    const unknownCount = questions?.filter((q) => q.answer?.answer_status === 'Unknown').length || 0;
    const skippedCount = questions?.filter((q) => q.answer?.answer_status === 'Skipped').length || 0;
    const completedCount = answeredCount + unknownCount + skippedCount;
    const totalQuestions = questions?.length || 0;
    const allAnswered = hasQuestions && totalQuestions > 0 && completedCount === totalQuestions;
    const hasEvaluation = !!evaluation;
    const hasMRD = !!mrd;
    const hasScores = !!scores;

    let activeStep = 0;
    if (hasQuestions) activeStep = 1;
    if (allAnswered) activeStep = 2;
    if (hasEvaluation) activeStep = 3;
    if (hasMRD) activeStep = 4;
    if (hasScores) activeStep = 5;

    // Calculate workflow completion based on key milestones (4 steps total)
    const workflowStepsComplete = [hasQuestions, hasEvaluation, hasMRD, hasScores].filter(Boolean).length;
    const workflowCompletion = Math.round((workflowStepsComplete / 4) * 100);

    // Q&A Coverage score - measures how many questions have been answered
    // This is calculated dynamically based on current Q&A state (not a snapshot)
    const qaCoverageScore = initiative.readiness_score || 0;

    return {
      activeStep,
      qaCoverageScore,
      workflowCompletion,
      workflowStepsComplete,
      hasQuestions,
      allAnswered,
      completedCount,
      totalQuestions,
      hasEvaluation,
      hasMRD,
      hasScores
    };
  };

  const { activeStep, qaCoverageScore, workflowCompletion, workflowStepsComplete, hasQuestions, allAnswered, completedCount, totalQuestions, hasEvaluation, hasMRD, hasScores } =
    getWorkflowProgress();

  // Determine next action
  const getNextAction = () => {
    const budgetExceeded = userProfile?.budget?.utilization_percentage >= 95;
    
    if (!hasQuestions) {
      return {
        title: 'Generate Discovery Questions',
        description: budgetExceeded 
          ? 'Question generation is currently disabled due to budget limits. Contact your administrator.'
          : 'AI will analyze your initiative and create targeted discovery questions to gather more details.',
        action: budgetExceeded ? 'Budget Exceeded' : 'Generate Questions',
        icon: <AutoAwesome />,
        handler: budgetExceeded ? null : handleGenerateQuestions,
        isPending: generateQuestions.isPending,
        disabled: budgetExceeded,
      };
    }

    if (!allAnswered) {
      return {
        title: 'Answer Discovery Questions',
        description: `You have ${totalQuestions - completedCount} unanswered questions. Answer them to improve the quality of your MRD.`,
        action: 'Go to Questions',
        icon: <HelpOutline />,
        handler: () => setCurrentTab(1),
      };
    }

    if (!hasEvaluation) {
      return {
        title: 'Evaluate MRD Readiness',
        description: 'All questions answered! Evaluate knowledge gaps and decide if you need more discovery or are ready to generate the MRD.',
        action: 'Evaluate Readiness',
        icon: <Assessment />,
        handler: () => setCurrentTab(2),
      };
    }

    if (!hasMRD) {
      return {
        title: 'Generate MRD',
        description: 'Your initiative has been evaluated and is ready. Generate the Market Requirements Document.',
        action: 'Generate MRD',
        icon: <Description />,
        handler: () => setCurrentTab(3),
      };
    }

    if (!hasScores) {
      return {
        title: 'Calculate Initiative Scores',
        description: 'MRD is complete! Calculate RICE and FDV scores to prioritize this initiative.',
        action: 'Calculate Scores',
        icon: <Assessment />,
        handler: () => setCurrentTab(4),
      };
    }

    return {
      title: 'Initiative Complete',
      description: 'All steps completed! You can review the MRD, scores, or make updates as needed.',
      action: 'Review',
      icon: <CheckCircle />,
      handler: () => setCurrentTab(3),
    };
  };

  const nextAction = getNextAction();

  if (isLoading) {
    return (
      <MainLayout>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      </MainLayout>
    );
  }

  if (error) {
    return (
      <MainLayout>
        <Alert severity="error">
          Failed to load initiative: {error.message}
        </Alert>
      </MainLayout>
    );
  }

  if (!initiative) {
    return (
      <MainLayout>
        <Alert severity="info">Initiative not found</Alert>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <Box>
        {/* Breadcrumbs */}
        <Breadcrumbs sx={{ mb: 2 }}>
          <Link
            underline="hover"
            color="inherit"
            href="/dashboard"
            onClick={(e) => {
              e.preventDefault();
              navigate('/dashboard');
            }}
          >
            Dashboard
          </Link>
          <Link
            underline="hover"
            color="inherit"
            href="/initiatives"
            onClick={(e) => {
              e.preventDefault();
              navigate('/initiatives');
            }}
          >
            Initiatives
          </Link>
          <Typography color="text.primary">{initiative.title}</Typography>
        </Breadcrumbs>

        {/* Progress Indicator */}
        <Card elevation={2} sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
              <Box>
                <Typography variant="h6" fontWeight="600" gutterBottom>
                  Initiative Progress
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {workflowStepsComplete} of 4 workflow steps complete
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, alignItems: 'flex-end' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Workflow
                  </Typography>
                  <Chip
                    label={`${workflowCompletion}%`}
                    color={workflowCompletion === 100 ? 'success' : workflowCompletion >= 75 ? 'primary' : workflowCompletion >= 50 ? 'warning' : 'default'}
                    size="small"
                    sx={{ fontWeight: 600, minWidth: 60 }}
                  />
                </Box>
                {qaCoverageScore > 0 && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Tooltip title="Percentage of P0/P1/P2 questions answered (weighted: P0=50%, P1=30%, P2=20%). This reflects your current Q&A progress and updates dynamically as you answer questions.">
                      <Typography variant="body2" color="text.secondary" sx={{ cursor: 'help', textDecoration: 'underline dotted' }}>
                        Q&A Coverage
                      </Typography>
                    </Tooltip>
                    <Chip
                      label={`${qaCoverageScore}%`}
                      color={qaCoverageScore >= 80 ? 'success' : qaCoverageScore >= 50 ? 'warning' : 'error'}
                      size="small"
                      sx={{ fontWeight: 600, minWidth: 60 }}
                    />
                    <Tooltip title="Recalculate Q&A coverage score based on current answers">
                      <IconButton
                        size="small"
                        onClick={() => recalculateQuality.mutate()}
                        disabled={recalculateQuality.isPending}
                      >
                        <Refresh fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                )}
              </Box>
            </Box>

            <Stepper activeStep={activeStep} alternativeLabel>
              {workflowSteps.map((step, index) => (
                <Step key={step.key} completed={index < activeStep}>
                  <StepLabel>{step.label}</StepLabel>
                </Step>
              ))}
            </Stepper>

            <Box sx={{ mt: 3 }}>
              <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                Workflow Progress
              </Typography>
              <LinearProgress
                variant="determinate"
                value={workflowCompletion}
                sx={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: 'action.hover',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 4,
                    backgroundColor: workflowCompletion === 100 ? 'success.main' : 'primary.main'
                  }
                }}
              />
            </Box>
          </CardContent>
        </Card>

        {/* Call to Action */}
        <Paper elevation={2} sx={{ mb: 3, bgcolor: 'primary.50', border: 1, borderColor: 'primary.main' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box
                sx={{
                  p: 2,
                  borderRadius: 2,
                  bgcolor: 'primary.main',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                {nextAction.icon}
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" fontWeight="600" gutterBottom>
                  Next Step: {nextAction.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {nextAction.description}
                </Typography>
              </Box>
              <Button
                variant="contained"
                size="large"
                endIcon={<ArrowForward />}
                onClick={nextAction.handler}
                disabled={nextAction.isPending || nextAction.disabled}
                color={nextAction.disabled ? 'error' : 'primary'}
              >
                {nextAction.isPending ? 'Processing...' : nextAction.action}
              </Button>
            </Box>
          </CardContent>
        </Paper>

        {/* Header */}
        <Card elevation={2} sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <Box sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <Typography variant="h4" fontWeight="600">
                    {initiative.title}
                  </Typography>
                  <Chip
                    label={initiative.status.replace('_', ' ')}
                    color={statusColors[initiative.status]}
                  />
                </Box>
                <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Created: {new Date(initiative.created_at).toLocaleDateString()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Updated: {new Date(initiative.updated_at).toLocaleDateString()}
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="outlined"
                  startIcon={<Edit />}
                  onClick={handleEdit}
                >
                  Edit
                </Button>
                <IconButton onClick={handleMenuOpen}>
                  <MoreVert />
                </IconButton>
                <Menu
                  anchorEl={anchorEl}
                  open={Boolean(anchorEl)}
                  onClose={handleMenuClose}
                >
                  <MenuItem onClick={handleDelete}>
                    <Delete fontSize="small" sx={{ mr: 1 }} />
                    Delete Initiative
                  </MenuItem>
                </Menu>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Card elevation={2}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={currentTab} onChange={handleTabChange}>
              <Tab label="Overview" />
              <Tab label="Questions" />
              <Tab label="Evaluation" />
              <Tab label="MRD" />
              <Tab label="Scores" />
            </Tabs>
          </Box>

          <CardContent>
            <TabPanel value={currentTab} index={0}>
              <Typography variant="h6" gutterBottom fontWeight="600">
                Initiative Overview
              </Typography>
              <Box
                sx={{
                  mt: 2,
                  p: 3,
                  bgcolor: 'background.paper',
                  borderRadius: 1,
                  border: 1,
                  borderColor: 'divider',
                  '& p': {
                    mb: 2,
                    lineHeight: 1.7,
                  },
                  '& p:first-of-type > strong:first-child': {
                    fontWeight: 600,
                    display: 'block',
                    mt: 2,
                    mb: 1,
                    fontSize: '1.1em',
                  },
                  '& strong': {
                    fontWeight: 600,
                  },
                }}
              >
                <ReactMarkdown>
                  {initiative.description || 'No description provided'}
                </ReactMarkdown>
              </Box>
            </TabPanel>

            <TabPanel value={currentTab} index={1}>
              <QuestionsTab
                initiativeId={id}
                onNavigateToEvaluation={handleNavigateAndEvaluate}
              />
            </TabPanel>

            <TabPanel value={currentTab} index={2}>
              <EvaluationTab
                ref={evaluationTabRef}
                initiativeId={id}
                onNavigateToMRD={() => setCurrentTab(3)}
                onNavigateToQuestions={() => setCurrentTab(1)}
              />
            </TabPanel>

            <TabPanel value={currentTab} index={3}>
              <MRDTab initiativeId={id} />
            </TabPanel>

            <TabPanel value={currentTab} index={4}>
              <ScoresTab initiativeId={id} />
            </TabPanel>
          </CardContent>
        </Card>
      </Box>

      {/* Loading Dialog */}
      <Dialog
        open={generateQuestions.isPending}
        maxWidth="sm"
        fullWidth
        disableEscapeKeyDown
      >
        <DialogTitle>Generating Questions</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, py: 3 }}>
            <CircularProgress size={60} />
            <Typography variant="body1" color="text.secondary" textAlign="center">
              AI is analyzing your initiative and creating discovery questions...
            </Typography>
            <Typography variant="body2" color="text.secondary" textAlign="center">
              This may take a few moments
            </Typography>
          </Box>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
