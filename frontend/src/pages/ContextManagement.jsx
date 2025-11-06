import { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Grid,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Divider,
} from '@mui/material';
import {
  Save,
  History,
  CheckCircle,
  Delete,
  Refresh,
  Info,
} from '@mui/icons-material';
import MainLayout from '../layouts/MainLayout';
import { useCurrentContext, useContextVersions, useCreateContext, useMakeCurrent, useDeleteContext } from '../hooks/useContext';
import { useAuth } from '../context/AuthContext';

export default function ContextManagement() {
  const { user } = useAuth();
  const { data: currentContext, isLoading, error, refetch } = useCurrentContext();
  const { data: versions, isLoading: versionsLoading } = useContextVersions();
  const createContext = useCreateContext();
  const makeCurrent = useMakeCurrent();
  const deleteContext = useDeleteContext();

  const [formData, setFormData] = useState({
    company_mission: '',
    strategic_objectives: '',
    target_markets: '',
    competitive_landscape: '',
    technical_constraints: '',
  });

  const [showVersions, setShowVersions] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [versionToDelete, setVersionToDelete] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');

  // Check if user is Product Manager or Admin
  const canEdit = user?.role === 'Product_Manager' || user?.role === 'Admin';

  // Load current context into form automatically when data is available
  useEffect(() => {
    if (currentContext) {
      setFormData({
        company_mission: currentContext.company_mission || '',
        strategic_objectives: currentContext.strategic_objectives || '',
        target_markets: currentContext.target_markets || '',
        competitive_landscape: currentContext.competitive_landscape || '',
        technical_constraints: currentContext.technical_constraints || '',
      });
    }
  }, [currentContext]);

  // Load current context into form (for reset button)
  const handleLoadCurrent = () => {
    if (currentContext) {
      setFormData({
        company_mission: currentContext.company_mission || '',
        strategic_objectives: currentContext.strategic_objectives || '',
        target_markets: currentContext.target_markets || '',
        competitive_landscape: currentContext.competitive_landscape || '',
        technical_constraints: currentContext.technical_constraints || '',
      });
    }
  };

  // Handle form change
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  // Handle form submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSuccessMessage('');

    try {
      await createContext.mutateAsync(formData);
      setSuccessMessage('Context saved successfully! This is now the current version.');
      refetch();

      // Clear message after 5 seconds
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err) {
      // Error is handled by the mutation
    }
  };

  // Handle make version current
  const handleMakeCurrent = async (contextId) => {
    try {
      await makeCurrent.mutateAsync(contextId);
      setSuccessMessage('Version set as current successfully!');
      refetch();
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err) {
      // Error handled by mutation
    }
  };

  // Handle delete version
  const handleDeleteClick = (version) => {
    setVersionToDelete(version);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (versionToDelete) {
      try {
        await deleteContext.mutateAsync(versionToDelete.id);
        setSuccessMessage('Version deleted successfully!');
        setDeleteDialogOpen(false);
        setVersionToDelete(null);
        setTimeout(() => setSuccessMessage(''), 5000);
      } catch (err) {
        // Error handled by mutation
      }
    }
  };

  if (isLoading) {
    return (
      <MainLayout>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <Box>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" fontWeight="600" gutterBottom>
            Organization Context
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            Define your organization's context to help AI agents generate more relevant questions, MRDs, and scoring.
            Each save creates a new version, allowing you to track changes over time.
          </Typography>

          {!canEdit && (
            <Alert severity="info" sx={{ mt: 2 }}>
              You need Product Manager or Admin role to edit context.
            </Alert>
          )}
        </Box>

        {/* Success Message */}
        {successMessage && (
          <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccessMessage('')}>
            {successMessage}
          </Alert>
        )}

        {/* Error Message */}
        {(error || createContext.isError || makeCurrent.isError || deleteContext.isError) && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error?.message || createContext.error?.message || makeCurrent.error?.message || deleteContext.error?.message || 'An error occurred'}
          </Alert>
        )}

        {/* Current Version Info */}
        {currentContext && (
          <Card elevation={2} sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="h6" fontWeight="600" gutterBottom>
                    Current Version
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <Chip
                      label={`Version ${currentContext.version}`}
                      color="primary"
                      size="small"
                      icon={<CheckCircle />}
                    />
                    <Typography variant="body2" color="text.secondary">
                      Last updated: {new Date(currentContext.updated_at).toLocaleDateString()}
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Tooltip title="Load current version into form">
                    <IconButton onClick={handleLoadCurrent} color="primary">
                      <Refresh />
                    </IconButton>
                  </Tooltip>
                  <Button
                    startIcon={<History />}
                    onClick={() => setShowVersions(!showVersions)}
                    variant="outlined"
                  >
                    {showVersions ? 'Hide' : 'Show'} History
                  </Button>
                </Box>
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Version History */}
        {showVersions && (
          <Card elevation={2} sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="600" gutterBottom>
                Version History
              </Typography>
              {versionsLoading ? (
                <CircularProgress size={24} />
              ) : versions && versions.length > 0 ? (
                <Box sx={{ mt: 2 }}>
                  {versions.map((version) => (
                    <Box
                      key={version.id}
                      sx={{
                        p: 2,
                        mb: 1,
                        border: 1,
                        borderColor: version.is_current ? 'primary.main' : 'divider',
                        borderRadius: 1,
                        bgcolor: version.is_current ? 'primary.50' : 'background.paper',
                      }}
                    >
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Box>
                          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 1 }}>
                            <Typography variant="subtitle2" fontWeight="600">
                              Version {version.version}
                            </Typography>
                            {version.is_current && (
                              <Chip label="Current" color="primary" size="small" />
                            )}
                          </Box>
                          <Typography variant="body2" color="text.secondary">
                            Created: {new Date(version.created_at).toLocaleString()}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          {!version.is_current && canEdit && (
                            <>
                              <Button
                                size="small"
                                onClick={() => handleMakeCurrent(version.id)}
                                disabled={makeCurrent.isPending}
                              >
                                Set as Current
                              </Button>
                              <IconButton
                                size="small"
                                onClick={() => handleDeleteClick(version)}
                                disabled={deleteContext.isPending}
                                color="error"
                              >
                                <Delete />
                              </IconButton>
                            </>
                          )}
                        </Box>
                      </Box>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No version history available
                </Typography>
              )}
            </CardContent>
          </Card>
        )}

        {/* Context Form */}
        <Card elevation={2}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
              <Typography variant="h6" fontWeight="600">
                Edit Context
              </Typography>
              <Tooltip title="Saving will create a new version and set it as current">
                <Info fontSize="small" color="action" />
              </Tooltip>
            </Box>

            <Box component="form" onSubmit={handleSubmit}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {/* Company Mission */}
                <Box>
                  <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                    Company Mission
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                    Define your company's core purpose and values
                  </Typography>
                  <TextField
                    fullWidth
                    name="company_mission"
                    value={formData.company_mission}
                    onChange={handleChange}
                    multiline
                    rows={6}
                    placeholder="What is your company's mission? Example: 'Democratize access to AI for small businesses by providing affordable, easy-to-use tools that enable non-technical users to leverage machine learning in their daily operations.'"
                    disabled={!canEdit}
                    variant="outlined"
                  />
                </Box>

                {/* Strategic Objectives */}
                <Box>
                  <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                    Strategic Objectives
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                    List your main business objectives and goals
                  </Typography>
                  <TextField
                    fullWidth
                    name="strategic_objectives"
                    value={formData.strategic_objectives}
                    onChange={handleChange}
                    multiline
                    rows={6}
                    placeholder="What are your key strategic goals? Example: 'Achieve 100K active users by Q4 2024, expand to European markets in 2025, establish partnerships with 3 major enterprise customers, reduce churn rate to below 5%.'"
                    disabled={!canEdit}
                    variant="outlined"
                  />
                </Box>

                {/* Target Markets */}
                <Box>
                  <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                    Target Markets
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                    Describe your ideal customer segments and markets
                  </Typography>
                  <TextField
                    fullWidth
                    name="target_markets"
                    value={formData.target_markets}
                    onChange={handleChange}
                    multiline
                    rows={6}
                    placeholder="Who are you targeting? Example: 'Small to medium-sized businesses in healthcare and professional services, 10-500 employees, primarily US market with expansion to UK and Germany. Decision makers are typically operations managers and CTOs looking for workflow automation.'"
                    disabled={!canEdit}
                    variant="outlined"
                  />
                </Box>

                {/* Competitive Landscape */}
                <Box>
                  <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                    Competitive Landscape
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                    Identify key competitors and your differentiation
                  </Typography>
                  <TextField
                    fullWidth
                    name="competitive_landscape"
                    value={formData.competitive_landscape}
                    onChange={handleChange}
                    multiline
                    rows={6}
                    placeholder="Who are your main competitors? Example: 'Competing with Salesforce and HubSpot in CRM space, but differentiated by AI-first approach and SMB-friendly pricing. Unlike enterprise-focused competitors, we offer no-code setup and AI assistants that require minimal training.'"
                    disabled={!canEdit}
                    variant="outlined"
                  />
                </Box>

                {/* Technical Constraints */}
                <Box>
                  <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                    Technical Constraints
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                    List any technical requirements or limitations
                  </Typography>
                  <TextField
                    fullWidth
                    name="technical_constraints"
                    value={formData.technical_constraints}
                    onChange={handleChange}
                    multiline
                    rows={6}
                    placeholder="What are your technical limitations? Example: 'Must maintain HIPAA compliance for healthcare customers, support modern browsers only (no IE11), API rate limits of 1000 requests/minute, mobile-first responsive design required, must integrate with Slack and Microsoft Teams.'"
                    disabled={!canEdit}
                    variant="outlined"
                  />
                </Box>

                {/* Action Buttons */}
                <Box>
                  <Divider sx={{ mb: 3 }} />
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                    <Button
                      type="button"
                      variant="outlined"
                      onClick={handleLoadCurrent}
                      disabled={!currentContext || !canEdit}
                      size="large"
                    >
                      Reset to Current
                    </Button>
                    <Button
                      type="submit"
                      variant="contained"
                      startIcon={<Save />}
                      disabled={createContext.isPending || !canEdit}
                      size="large"
                    >
                      {createContext.isPending ? 'Saving...' : 'Save New Version'}
                    </Button>
                  </Box>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
          <DialogTitle>Delete Version?</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Are you sure you want to delete Version {versionToDelete?.version}? This action cannot be undone.
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleDeleteConfirm} color="error" disabled={deleteContext.isPending}>
              {deleteContext.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </MainLayout>
  );
}
