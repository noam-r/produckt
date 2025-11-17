import { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Grid,
  LinearProgress,
  Chip,
  Divider,
  Paper,
  Dialog,
  DialogContent,
  Snackbar,
} from '@mui/material';
import {
  AutoAwesome,
  TrendingUp,
  CheckCircle,
  Refresh,
  Download,
  Warning,
  HelpOutline,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';
import { initiativesApi } from '../api/initiatives';
import { useCalculateScores } from '../hooks/useInitiatives';
import { useJobPolling } from '../hooks/useJobPolling';
import ScoringGapDialog from './ScoringGapDialog';

// Score interpretation
const getRiceScoreLevel = (score) => {
  if (score == null) return { label: 'Not Calculated', color: 'default' };
  if (score >= 75) return { label: 'High Priority', color: 'success' };
  if (score >= 40) return { label: 'Medium Priority', color: 'warning' };
  return { label: 'Low Priority', color: 'error' };
};

const getFdvScoreLevel = (score) => {
  if (score == null) return { label: 'Not Calculated', color: 'default' };
  if (score >= 7) return { label: 'Highly Viable', color: 'success' };
  if (score >= 5) return { label: 'Viable', color: 'info' };
  if (score >= 3) return { label: 'Questionable', color: 'warning' };
  return { label: 'Not Viable', color: 'error' };
};

export default function ScoresTab({ initiativeId }) {
  const [exportingPdf, setExportingPdf] = useState(false);
  const [gapDialogOpen, setGapDialogOpen] = useState(false);
  const [gapAnalysis, setGapAnalysis] = useState(null);
  const [currentJobId, setCurrentJobId] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [showAllWarnings, setShowAllWarnings] = useState(false);
  const queryClient = useQueryClient();

  // Fetch scores
  const {
    data: scores,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['scores', initiativeId],
    queryFn: () => initiativesApi.getScores(initiativeId),
    retry: false,
  });

  // Poll job status
  const {
    isPolling: calculating,
    progress,
    progressMessage,
  } = useJobPolling(currentJobId, {
    pollInterval: 1000, // Poll every second
    onComplete: async (result) => {
      console.log('Job completed:', result);
      setCurrentJobId(null);

      // Check if this was a gap analysis job
      if (result && result.gap_analysis) {
        const hasImprovementQuestions = result.gap_analysis.blocking_gaps && result.gap_analysis.blocking_gaps.length > 0;
        const currentConfidence = result.gap_analysis.current_confidence;
        const message = result.gap_analysis.message;

        if (hasImprovementQuestions) {
          // Show improvement questions to increase confidence
          setGapAnalysis(result.gap_analysis);
          setGapDialogOpen(true);
        } else {
          // Confidence already high - no improvement needed
          await refetch();
          setSuccessMessage(message || `Confidence is already ${currentConfidence}% - no improvement needed!`);
        }
      } else {
        // This was a score calculation job - just refresh
        await refetch();
        setSuccessMessage('Scores updated successfully!');
      }
    },
    onError: (error) => {
      console.error('Job failed:', error);
      setCurrentJobId(null);
      alert(`Job failed: ${error.message || error}`);
    },
  });

  const handleAnalyzeAndCalculate = async () => {
    try {
      // Start score calculation job
      const response = await initiativesApi.calculateScores(initiativeId);
      setCurrentJobId(response.job_id);
    } catch (err) {
      console.error('Failed to start score calculation:', err);
      alert('Failed to start score calculation');
    }
  };

  const handleCalculateScores = async () => {
    try {
      // Start score calculation job
      const response = await initiativesApi.calculateScores(initiativeId);
      setCurrentJobId(response.job_id);
    } catch (err) {
      console.error('Failed to start score calculation:', err);
      alert('Failed to start score calculation');
    }
  };

  const handleImproveConfidence = async () => {
    try {
      // Start gap analysis job
      const response = await initiativesApi.analyzeScoringGaps(initiativeId);
      setCurrentJobId(response.job_id);

      // Poll until gap analysis completes
      // The useJobPolling hook will handle this automatically
      // When complete, it will trigger onComplete which shows the gap dialog
    } catch (err) {
      console.error('Failed to start gap analysis:', err);
      alert('Failed to start gap analysis');
    }
  };

  const handleGapDialogClose = async (submitted) => {
    setGapDialogOpen(false);
    if (submitted) {
      // User submitted gap answers - now recalculate scores
      await handleCalculateScores();
    }
  };

  const handleExportPdf = async () => {
    setExportingPdf(true);
    try {
      const response = await initiativesApi.exportScoresPdf(initiativeId);
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `scorecard-${initiativeId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('PDF export error:', err);
      alert('Failed to export scorecard as PDF');
    } finally {
      setExportingPdf(false);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && error.response?.status === 404) {
    return (
      <Box sx={{ textAlign: 'center', py: 6 }}>
        <TrendingUp sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          No Scores Calculated Yet
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Calculate RICE and FDV scores to prioritize this initiative against others
        </Typography>
        <Button
          variant="contained"
          startIcon={calculating ? <CircularProgress size={20} /> : <AutoAwesome />}
          onClick={handleAnalyzeAndCalculate}
          disabled={calculating}
          size="large"
        >
          {calculating ? 'Analyzing...' : 'Calculate Scores'}
        </Button>
        <Alert severity="info" sx={{ mt: 3, maxWidth: 600, mx: 'auto' }}>
          Note: Scores are calculated based on your initiative details, answered questions, and
          generated MRD. Make sure you have an MRD before calculating scores.
        </Alert>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error">
        Failed to load scores: {error.message}
      </Alert>
    );
  }

  const riceLevel = getRiceScoreLevel(scores.rice_score);
  const fdvLevel = getFdvScoreLevel(scores.fdv_score);

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" fontWeight="600">
          Initiative Scoring
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            startIcon={exportingPdf ? <CircularProgress size={20} /> : <Download />}
            onClick={handleExportPdf}
            disabled={exportingPdf}
            variant="outlined"
          >
            Export PDF
          </Button>
          <Button
            startIcon={<Refresh />}
            onClick={handleCalculateScores}
            disabled={calculating}
          >
            Recalculate
          </Button>
        </Box>
      </Box>

      {/* Estimation Warning */}
      {scores.data_quality?.estimated_answers_count > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          <Typography variant="body2" gutterBottom>
            <strong>Scores Based on Estimates</strong>
          </Typography>
          <Typography variant="body2">
            This scorecard includes {scores.data_quality.estimated_answers_count} estimated answer(s).
            RICE Confidence has been reduced by {scores.data_quality.confidence_penalty_applied} to reflect
            data uncertainty. Consider replacing estimates with precise data to improve scoring accuracy.
          </Typography>
        </Alert>
      )}

      {/* Data Quality Warnings */}
      {scores.warnings && scores.warnings.length > 0 && (
        <Alert
          severity="info"
          sx={{ mb: 3 }}
          action={
            <Box sx={{ display: 'flex', gap: 1, flexDirection: 'column' }}>
              {scores.rice_score == null && (
                <Button
                  variant="contained"
                  color="primary"
                  size="medium"
                  onClick={handleAnalyzeAndCalculate}
                  disabled={calculating}
                  sx={{
                    fontWeight: 600,
                    boxShadow: 2,
                    minWidth: 120
                  }}
                >
                  {calculating ? 'Calculating...' : 'Calculate'}
                </Button>
              )}
              {scores.rice_score != null && scores.confidence < 80 && (
                <Button
                  variant="outlined"
                  color="primary"
                  size="medium"
                  onClick={handleImproveConfidence}
                  disabled={calculating}
                  sx={{
                    fontWeight: 600,
                    minWidth: 180
                  }}
                >
                  Improve Confidence
                </Button>
              )}
            </Box>
          }
        >
          <Typography variant="body2" fontWeight="600" gutterBottom>
            Data Quality Notes:
          </Typography>
          {(showAllWarnings ? scores.warnings : scores.warnings.slice(0, 3)).map((warning, index) => (
            <Typography key={index} variant="body2" sx={{ mt: 0.5 }}>
              • {warning}
            </Typography>
          ))}
          {scores.warnings.length > 3 && (
            <Button
              size="small"
              onClick={() => setShowAllWarnings(!showAllWarnings)}
              sx={{ mt: 1, textTransform: 'none' }}
            >
              {showAllWarnings ? `Show less` : `Show all (${scores.warnings.length} notes)`}
            </Button>
          )}
        </Alert>
      )}

      {/* Score Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          <Card elevation={3} sx={{ height: '100%', position: 'relative' }}>
            <CardContent>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="overline" color="text.secondary" gutterBottom>
                  RICE Score
                </Typography>
                <Typography variant="h2" fontWeight="600" color="primary.main" sx={{ my: 2 }}>
                  {scores.rice_score != null ? scores.rice_score.toFixed(1) : '—'}
                </Typography>
                <Chip label={riceLevel.label} color={riceLevel.color} size="large" />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                  (Reach × Impact × Confidence) / Effort
                </Typography>

                {/* Show CTA button if score cannot be calculated */}
                {scores.rice_score == null && (
                  <Box sx={{ mt: 3 }}>
                    <Button
                      variant="contained"
                      color="primary"
                      size="large"
                      startIcon={<HelpOutline />}
                      onClick={handleAnalyzeAndCalculate}
                      disabled={calculating}
                      sx={{
                        px: 4,
                        py: 1.5,
                        fontSize: '1rem',
                        fontWeight: 600,
                        boxShadow: 3
                      }}
                    >
                      {calculating ? 'Calculating...' : 'Calculate Score'}
                    </Button>
                    <Typography variant="body2" display="block" color="text.secondary" sx={{ mt: 1.5 }}>
                      Scores will be calculated with available data. Confidence will reflect data quality.
                    </Typography>
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12}>
          <Card elevation={3} sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="overline" color="text.secondary" gutterBottom>
                  FDV Score
                </Typography>
                <Typography variant="h2" fontWeight="600" color="secondary.main" sx={{ my: 2 }}>
                  {scores.fdv_score?.toFixed(1)}
                </Typography>
                <Chip label={fdvLevel.label} color={fdvLevel.color} size="large" />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                  (Feasibility + Desirability + Viability) / 3
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* RICE Breakdown */}
      <Card elevation={2} sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight="600" gutterBottom>
            RICE Score Breakdown
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            RICE helps prioritize initiatives based on reach, impact, confidence, and effort
          </Typography>

          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Reach
                </Typography>
                <Typography variant="h4" fontWeight="600" gutterBottom>
                  {scores.reach != null ? scores.reach.toLocaleString() : '—'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {scores.reach != null ? 'per quarter' : 'insufficient data'}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Impact
                </Typography>
                <Typography variant="h4" fontWeight="600" gutterBottom>
                  {scores.impact != null ? scores.impact.toFixed(1) : '—'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  scale: 0.25 - 3.0
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Confidence
                </Typography>
                <Typography variant="h4" fontWeight="600" gutterBottom>
                  {scores.confidence != null ? `${scores.confidence}%` : '—'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  certainty level
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Effort
                </Typography>
                <Typography variant="h4" fontWeight="600" gutterBottom>
                  {scores.effort != null ? scores.effort.toFixed(1) : '—'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  person-months
                </Typography>
              </Box>
            </Grid>
          </Grid>

          <Divider sx={{ my: 3 }} />

          {scores.rice_reasoning && (
            <Box>
              <Typography variant="subtitle2" fontWeight="600" gutterBottom>
                Scoring Rationale
              </Typography>
              <Box sx={{ mt: 2 }}>
                {scores.rice_reasoning.reach && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" fontWeight="600" color="primary.main" gutterBottom>
                      Reach
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-line' }}>
                      {scores.rice_reasoning.reach}
                    </Typography>
                  </Box>
                )}
                {scores.rice_reasoning.impact && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" fontWeight="600" color="primary.main" gutterBottom>
                      Impact
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-line' }}>
                      {scores.rice_reasoning.impact}
                    </Typography>
                  </Box>
                )}
                {scores.rice_reasoning.confidence && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" fontWeight="600" color="primary.main" gutterBottom>
                      Confidence
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-line' }}>
                      {scores.rice_reasoning.confidence}
                    </Typography>
                  </Box>
                )}
                {scores.rice_reasoning.effort && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" fontWeight="600" color="primary.main" gutterBottom>
                      Effort
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-line' }}>
                      {scores.rice_reasoning.effort}
                    </Typography>
                  </Box>
                )}
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* FDV Breakdown */}
      <Card elevation={2}>
        <CardContent>
          <Typography variant="h6" fontWeight="600" gutterBottom>
            FDV Score Breakdown
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            FDV evaluates feasibility, desirability, and viability on a scale of 1-10
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
            {/* Left side: Numeric breakdown */}
            <Box sx={{ flex: '1 1 50%', display: 'flex', flexDirection: 'column', gap: 3, justifyContent: 'center' }}>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="body1" fontWeight="500" color="text.secondary">
                    Feasibility
                  </Typography>
                  <Typography variant="h4" fontWeight="600">
                    {scores.feasibility}/10
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={(scores.feasibility / 10) * 100}
                  sx={{ height: 10, borderRadius: 5, mb: 1 }}
                  color="primary"
                />
                <Typography variant="body2" color="text.secondary">
                  Can we build it?
                </Typography>
              </Box>

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="body1" fontWeight="500" color="text.secondary">
                    Desirability
                  </Typography>
                  <Typography variant="h4" fontWeight="600">
                    {scores.desirability}/10
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={(scores.desirability / 10) * 100}
                  sx={{ height: 10, borderRadius: 5, mb: 1 }}
                  color="secondary"
                />
                <Typography variant="body2" color="text.secondary">
                  Do users want it?
                </Typography>
              </Box>

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="body1" fontWeight="500" color="text.secondary">
                    Viability
                  </Typography>
                  <Typography variant="h4" fontWeight="600">
                    {scores.viability}/10
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={(scores.viability / 10) * 100}
                  sx={{ height: 10, borderRadius: 5, mb: 1 }}
                  color="success"
                />
                <Typography variant="body2" color="text.secondary">
                  Is it sustainable?
                </Typography>
              </Box>
            </Box>

            {/* Right side: Radar chart */}
            <Box sx={{ flex: '1 1 50%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <Typography variant="subtitle2" fontWeight="600" gutterBottom sx={{ textAlign: 'center' }}>
                FDV Visual Profile
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart
                  data={[
                    { dimension: 'Feasibility', value: scores.feasibility || 0, fullMark: 10 },
                    { dimension: 'Desirability', value: scores.desirability || 0, fullMark: 10 },
                    { dimension: 'Viability', value: scores.viability || 0, fullMark: 10 },
                  ]}
                  cx="50%"
                  cy="50%"
                  outerRadius="70%"
                >
                  <PolarGrid stroke="#e0e0e0" />
                  <PolarAngleAxis
                    dataKey="dimension"
                    tick={{ fill: '#666', fontSize: 14, fontWeight: 500 }}
                  />
                  <PolarRadiusAxis
                    angle={90}
                    domain={[0, 10]}
                    tick={{ fill: '#999', fontSize: 12 }}
                    tickCount={6}
                  />
                  <Radar
                    name="FDV Score"
                    dataKey="value"
                    stroke="#1976d2"
                    fill="#1976d2"
                    fillOpacity={0.5}
                    strokeWidth={2}
                  />
                  <Tooltip
                    formatter={(value) => [`${value}/10`, 'Score']}
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #ddd',
                      borderRadius: 4,
                    }}
                  />
                  <Legend
                    wrapperStyle={{ paddingTop: 20 }}
                    iconType="circle"
                  />
                </RadarChart>
              </ResponsiveContainer>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 1 }}>
                A balanced triangle indicates a well-rounded initiative. Skewed shapes reveal areas needing attention.
              </Typography>
            </Box>
          </Box>

          <Divider sx={{ my: 3 }} />

          {scores.fdv_reasoning && (
            <Box>
              <Typography variant="subtitle2" fontWeight="600" gutterBottom>
                Scoring Rationale
              </Typography>
              <Box sx={{ mt: 2 }}>
                {scores.fdv_reasoning.feasibility && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" fontWeight="600" color="primary.main" gutterBottom>
                      Feasibility
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-line' }}>
                      {scores.fdv_reasoning.feasibility}
                    </Typography>
                  </Box>
                )}
                {scores.fdv_reasoning.desirability && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" fontWeight="600" color="secondary.main" gutterBottom>
                      Desirability
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-line' }}>
                      {scores.fdv_reasoning.desirability}
                    </Typography>
                  </Box>
                )}
                {scores.fdv_reasoning.viability && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" fontWeight="600" color="success.main" gutterBottom>
                      Viability
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-line' }}>
                      {scores.fdv_reasoning.viability}
                    </Typography>
                  </Box>
                )}
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Metadata */}
      <Box sx={{ mt: 3, textAlign: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          Calculated: {new Date(scores.created_at).toLocaleString()}
        </Typography>
      </Box>

      {/* Calculation Modal */}
      <Dialog open={calculating && !gapDialogOpen} maxWidth="sm" fullWidth>
        <DialogContent sx={{ textAlign: 'center', py: 4 }}>
          <CircularProgress
            variant={progress > 0 ? "determinate" : "indeterminate"}
            value={progress || 0}
            size={60}
            sx={{ mb: 2 }}
          />
          <Typography variant="h6" gutterBottom>
            {progressMessage || 'Calculating Scores'}
          </Typography>
          {progress > 0 && (
            <Typography variant="body2" color="text.secondary">
              {progress}% complete
            </Typography>
          )}
          {!progress && (
            <Typography variant="body2" color="text.secondary">
              Please wait...
            </Typography>
          )}
        </DialogContent>
      </Dialog>

      {/* Gap Analysis Dialog */}
      {gapAnalysis && (
        <ScoringGapDialog
          open={gapDialogOpen}
          onClose={handleGapDialogClose}
          gapAnalysis={gapAnalysis}
          initiativeId={initiativeId}
        />
      )}

      {/* Success Notification */}
      <Snackbar
        open={!!successMessage}
        autoHideDuration={6000}
        onClose={() => setSuccessMessage('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSuccessMessage('')} severity="success" sx={{ width: '100%' }}>
          {successMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}
