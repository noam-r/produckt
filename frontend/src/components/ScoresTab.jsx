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
} from '@mui/material';
import {
  AutoAwesome,
  TrendingUp,
  CheckCircle,
  Refresh,
  Download,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { initiativesApi } from '../api/initiatives';
import { useCalculateScores } from '../hooks/useInitiatives';

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
  const [calculating, setCalculating] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

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

  const calculateScores = useCalculateScores();

  const handleCalculateScores = async () => {
    setCalculating(true);
    try {
      await calculateScores.mutateAsync(initiativeId);
      await refetch();
    } catch (err) {
      // Error handling in mutation
    } finally {
      setCalculating(false);
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
          onClick={handleCalculateScores}
          disabled={calculating}
          size="large"
        >
          {calculating ? 'Calculating Scores...' : 'Calculate Scores'}
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

      {/* Score Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          <Card elevation={3} sx={{ height: '100%' }}>
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

          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Feasibility
                  </Typography>
                  <Typography variant="h5" fontWeight="600">
                    {scores.feasibility}/10
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={(scores.feasibility / 10) * 100}
                  sx={{ height: 8, borderRadius: 4, mb: 1 }}
                  color="primary"
                />
                <Typography variant="caption" color="text.secondary">
                  Can we build it?
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={4}>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Desirability
                  </Typography>
                  <Typography variant="h5" fontWeight="600">
                    {scores.desirability}/10
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={(scores.desirability / 10) * 100}
                  sx={{ height: 8, borderRadius: 4, mb: 1 }}
                  color="secondary"
                />
                <Typography variant="caption" color="text.secondary">
                  Do users want it?
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={4}>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Viability
                  </Typography>
                  <Typography variant="h5" fontWeight="600">
                    {scores.viability}/10
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={(scores.viability / 10) * 100}
                  sx={{ height: 8, borderRadius: 4, mb: 1 }}
                  color="success"
                />
                <Typography variant="caption" color="text.secondary">
                  Is it sustainable?
                </Typography>
              </Box>
            </Grid>
          </Grid>

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
      <Dialog open={calculating} maxWidth="sm" fullWidth>
        <DialogContent sx={{ textAlign: 'center', py: 4 }}>
          <CircularProgress size={60} sx={{ mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Calculating Scores
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Analyzing initiative data and generating RICE & FDV scores...
          </Typography>
        </DialogContent>
      </Dialog>
    </Box>
  );
}
