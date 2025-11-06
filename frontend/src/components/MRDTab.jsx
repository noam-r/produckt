import { useState } from 'react';
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
  Divider,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  AutoAwesome,
  Download,
  Refresh,
  Info,
  ArrowDropDown,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useQuery } from '@tanstack/react-query';
import { initiativesApi } from '../api/initiatives';
import { useJobPolling } from '../hooks/useJobPolling';
import JobProgressModal from './JobProgressModal';
import apiClient from '../api/client';

export default function MRDTab({ initiativeId }) {
  const [mrdJobId, setMrdJobId] = useState(null);
  const [error, setError] = useState(null);
  const [exportMenuAnchor, setExportMenuAnchor] = useState(null);
  const [isExportingPdf, setIsExportingPdf] = useState(false);

  // Fetch MRD
  const {
    data: mrd,
    isLoading,
    error: queryError,
    refetch,
  } = useQuery({
    queryKey: ['mrd', initiativeId],
    queryFn: () => initiativesApi.getMRD(initiativeId),
    retry: false,
  });

  // MRD generation job polling
  const mrdJobPolling = useJobPolling(mrdJobId, {
    onComplete: async (resultData) => {
      setMrdJobId(null);
      // Refetch the MRD data
      await refetch();
    },
    onError: (err) => {
      setMrdJobId(null);
      setError(err.message);
    }
  });

  const isGenerating = mrdJobPolling.isPolling;

  const handleGenerateMRD = async () => {
    setError(null);
    try {
      const response = await apiClient.post(
        `/api/agents/initiatives/${initiativeId}/generate-mrd`
      );
      // Response contains job_id
      setMrdJobId(response.data.job_id);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to start MRD generation');
    }
  };

  const handleExportMarkdown = async () => {
    setExportMenuAnchor(null);
    try {
      const content = await initiativesApi.getMRDContent(initiativeId);
      const blob = new Blob([content.content], { type: 'text/markdown' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mrd-${initiativeId}.md`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to export MRD as Markdown');
    }
  };

  const handleExportPdf = async () => {
    setExportMenuAnchor(null);
    setIsExportingPdf(true);

    try {
      // Call backend PDF generation endpoint
      const response = await apiClient.get(
        `/api/agents/initiatives/${initiativeId}/mrd/pdf`,
        { responseType: 'blob' }
      );

      // Create download link
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mrd-${initiativeId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('PDF export error:', err);
      alert('Failed to export MRD as PDF');
    } finally {
      setIsExportingPdf(false);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (queryError && queryError.response?.status === 404) {
    return (
      <Box sx={{ textAlign: 'center', py: 6 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 3, maxWidth: 600, mx: 'auto' }}>
            {error}
          </Alert>
        )}
        <AutoAwesome sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          No MRD Generated Yet
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Generate a comprehensive Market Requirements Document based on your initiative details
          and answered questions
        </Typography>
        <Button
          variant="contained"
          startIcon={isGenerating ? <CircularProgress size={20} /> : <AutoAwesome />}
          onClick={handleGenerateMRD}
          disabled={isGenerating}
          size="large"
        >
          {isGenerating ? 'Generating MRD...' : 'Generate MRD'}
        </Button>
        <Alert severity="info" sx={{ mt: 3, maxWidth: 600, mx: 'auto' }}>
          Note: MRD generation works best when you've answered most of the discovery questions.
          The more questions answered, the more comprehensive your MRD will be.
        </Alert>

        {/* MRD generation progress modal */}
        <JobProgressModal
          open={isGenerating}
          title="Generating MRD"
          progressMessage={mrdJobPolling.progressMessage}
          progressPercent={mrdJobPolling.progress}
        />
      </Box>
    );
  }

  if (queryError) {
    return (
      <Alert severity="error">
        Failed to load MRD: {queryError.message}
      </Alert>
    );
  }

  return (
    <Box>
      {/* MRD Metadata */}
      <Card elevation={2} sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h6" fontWeight="600">
              MRD Information
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                startIcon={<Refresh />}
                onClick={handleGenerateMRD}
                disabled={isGenerating}
              >
                Regenerate
              </Button>
              <Button
                variant="contained"
                startIcon={<Download />}
                endIcon={<ArrowDropDown />}
                onClick={(e) => setExportMenuAnchor(e.currentTarget)}
                disabled={isExportingPdf}
              >
                {isExportingPdf ? 'Exporting...' : 'Export'}
              </Button>
              <Menu
                anchorEl={exportMenuAnchor}
                open={Boolean(exportMenuAnchor)}
                onClose={() => setExportMenuAnchor(null)}
              >
                <MenuItem onClick={handleExportMarkdown}>
                  Export as Markdown
                </MenuItem>
                <MenuItem onClick={handleExportPdf}>
                  Export as PDF
                </MenuItem>
              </Menu>
            </Box>
          </Box>

          <Grid container spacing={3}>
            <Grid item xs={12} md={3}>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Version
                </Typography>
                <Typography variant="h5" fontWeight="600">
                  {mrd.version}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={3}>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Word Count
                </Typography>
                <Typography variant="h5" fontWeight="600">
                  {mrd.word_count?.toLocaleString()}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={3}>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Completeness
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="h5" fontWeight="600">
                    {mrd.completeness_score}%
                  </Typography>
                  <Chip
                    label={mrd.completeness_score >= 80 ? 'Good' : mrd.completeness_score >= 60 ? 'Fair' : 'Needs Work'}
                    color={mrd.completeness_score >= 80 ? 'success' : mrd.completeness_score >= 60 ? 'warning' : 'error'}
                    size="small"
                  />
                </Box>
              </Box>
            </Grid>
            <Grid item xs={12} md={3}>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Readiness
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="h5" fontWeight="600">
                    {mrd.readiness_at_generation}%
                  </Typography>
                  <Tooltip title="Based on answered questions at generation time">
                    <IconButton size="small">
                      <Info fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </Box>
            </Grid>
          </Grid>

          <Box sx={{ mt: 3 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Generated: {new Date(mrd.generated_at).toLocaleString()}
            </Typography>
            {mrd.assumptions_made && mrd.assumptions_made.length > 0 && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                <Typography variant="subtitle2" fontWeight="600" gutterBottom>
                  Assumptions Made ({mrd.assumptions_made.length})
                </Typography>
                <Typography variant="body2">
                  Some questions were marked as unknown. The MRD includes assumptions based on
                  available information.
                </Typography>
              </Alert>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Quality Disclaimer */}
      {mrd.quality_disclaimer && (
        <Alert severity="info" sx={{ mb: 3 }}>
          {mrd.quality_disclaimer}
        </Alert>
      )}

      {/* MRD Content */}
      <Card elevation={2}>
        <CardContent>
          <Paper
            elevation={0}
            sx={{
              p: 4,
              bgcolor: 'background.paper',
              width: '100%',
              maxWidth: '100%',
              '& .table-wrapper': {
                pageBreakInside: 'avoid',
                marginBottom: 3,
                marginTop: 2,
              },
              '& h1': {
                fontSize: '2rem',
                fontWeight: 600,
                mt: 3,
                mb: 2,
                color: 'primary.main',
                pageBreakAfter: 'avoid',
                pageBreakInside: 'avoid',
              },
              '& h2': {
                fontSize: '1.5rem',
                fontWeight: 600,
                mt: 3,
                mb: 2,
                color: 'text.primary',
                pageBreakAfter: 'avoid',
              },
              '& h3': {
                fontSize: '1.25rem',
                fontWeight: 500,
                mt: 2,
                mb: 1,
                color: 'text.primary',
                pageBreakAfter: 'avoid',
              },
              '& p': {
                mb: 2,
                lineHeight: 1.7,
                color: 'text.primary',
              },
              '& ul, & ol': {
                mb: 2,
                pl: 3,
              },
              '& li': {
                mb: 1,
                color: 'text.primary',
              },
              '& code': {
                bgcolor: 'action.hover',
                color: 'text.primary',
                px: 1,
                py: 0.5,
                borderRadius: 1,
                fontSize: '0.875rem',
              },
              '& pre': {
                bgcolor: 'action.hover',
                color: 'text.primary',
                p: 2,
                borderRadius: 1,
                overflow: 'auto',
                mb: 2,
              },
              '& blockquote': {
                borderLeft: '4px solid',
                borderColor: 'primary.main',
                pl: 2,
                ml: 0,
                fontStyle: 'italic',
                color: 'text.secondary',
              },
              '& table': {
                width: '100%',
                borderCollapse: 'collapse',
                mb: 3,
                mt: 2,
                pageBreakInside: 'auto',
              },
              '& thead': {
                pageBreakAfter: 'avoid',
              },
              '& tbody': {
              },
              '& th, & td': {
                border: '1px solid',
                borderColor: 'divider',
                p: 1.5,
                textAlign: 'left',
                verticalAlign: 'top',
                color: 'text.primary',
              },
              '& th': {
                bgcolor: 'action.hover',
                fontWeight: 600,
              },
              '& tr': {
                pageBreakInside: 'avoid',
                pageBreakAfter: 'auto',
              },
            }}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                table: ({node, ...props}) => (
                  <div className="table-wrapper">
                    <table {...props} />
                  </div>
                ),
              }}
            >
              {mrd.content}
            </ReactMarkdown>
          </Paper>
        </CardContent>
      </Card>

      {/* MRD generation progress modal */}
      <JobProgressModal
        open={isGenerating}
        title="Generating MRD"
        progressMessage={mrdJobPolling.progressMessage}
        progressPercent={mrdJobPolling.progress}
      />

      {/* PDF export progress modal */}
      <JobProgressModal
        open={isExportingPdf}
        title="Exporting PDF"
        progressMessage="Rendering content and generating PDF..."
        progressPercent={null}
      />
    </Box>
  );
}
