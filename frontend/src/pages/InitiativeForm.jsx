import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Breadcrumbs,
  Link,
  Divider,
} from '@mui/material';
import { Save, Cancel, Lightbulb } from '@mui/icons-material';
import {
  useInitiative,
  useCreateInitiative,
  useUpdateInitiative,
} from '../hooks/useInitiatives';
import MainLayout from '../layouts/MainLayout';

// Status options
const statusOptions = [
  { value: 'DRAFT', label: 'Draft' },
  { value: 'IN_DISCOVERY', label: 'In Discovery' },
  { value: 'IN_QA', label: 'In Q&A' },
  { value: 'READY_FOR_MRD', label: 'Ready for MRD' },
  { value: 'COMPLETED', label: 'Completed' },
];

export default function InitiativeForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditMode = !!id;

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'DRAFT',
  });

  // Structured fields for new initiatives
  const [structuredData, setStructuredData] = useState({
    what: '',           // What do you want to build?
    who: '',            // Who is it for?
    why: '',            // Why is this important/needed?
    benefits: '',       // Expected benefits/outcomes
    risks: '',          // Potential risks/challenges
  });

  const [errors, setErrors] = useState({});

  const { data: initiative, isLoading: loadingInitiative } = useInitiative(id);
  const createInitiative = useCreateInitiative();
  const updateInitiative = useUpdateInitiative();

  const isLoading = createInitiative.isPending || updateInitiative.isPending;

  // Load initiative data in edit mode
  useEffect(() => {
    if (initiative) {
      setFormData({
        title: initiative.title || '',
        description: initiative.description || '',
        status: initiative.status || 'DRAFT',
      });
    }
  }, [initiative]);

  const handleChange = (field) => (e) => {
    setFormData({ ...formData, [field]: e.target.value });
    if (errors[field]) {
      setErrors({ ...errors, [field]: '' });
    }
  };

  const handleStructuredChange = (field) => (e) => {
    setStructuredData({ ...structuredData, [field]: e.target.value });
    if (errors[field]) {
      setErrors({ ...errors, [field]: '' });
    }
  };

  // Build description from structured data
  const buildDescription = () => {
    const parts = [];
    if (structuredData.what) parts.push(`**What:** ${structuredData.what}`);
    if (structuredData.who) parts.push(`**Who:** ${structuredData.who}`);
    if (structuredData.why) parts.push(`**Why:** ${structuredData.why}`);
    if (structuredData.benefits) parts.push(`**Expected Benefits:** ${structuredData.benefits}`);
    if (structuredData.risks) parts.push(`**Risks & Challenges:** ${structuredData.risks}`);
    return parts.join('\n\n');
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }

    // For new initiatives, require all structured fields
    if (!isEditMode) {
      if (!structuredData.what.trim()) {
        newErrors.what = 'Please describe what you want to build';
      }
      if (!structuredData.who.trim()) {
        newErrors.who = 'Please identify who this is for';
      }
      if (!structuredData.why.trim()) {
        newErrors.why = 'Please explain why this is important';
      }
      if (!structuredData.benefits.trim()) {
        newErrors.benefits = 'Please describe the expected benefits';
      }
      if (!structuredData.risks.trim()) {
        newErrors.risks = 'Please identify potential risks or challenges';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    try {
      const submitData = { ...formData };

      // For new initiatives, build description from structured data
      if (!isEditMode) {
        submitData.description = buildDescription();
      }

      if (isEditMode) {
        await updateInitiative.mutateAsync({
          id,
          data: submitData,
        });
        navigate(`/initiatives/${id}`);
      } else {
        const result = await createInitiative.mutateAsync(submitData);
        navigate(`/initiatives/${result.id}`);
      }
    } catch (err) {
      setErrors({
        submit: err.response?.data?.detail || 'Failed to save initiative',
      });
    }
  };

  const handleCancel = () => {
    if (isEditMode) {
      navigate(`/initiatives/${id}`);
    } else {
      navigate('/initiatives');
    }
  };

  if (loadingInitiative) {
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
          {isEditMode && initiative && (
            <Link
              underline="hover"
              color="inherit"
              href={`/initiatives/${id}`}
              onClick={(e) => {
                e.preventDefault();
                navigate(`/initiatives/${id}`);
              }}
            >
              {initiative.title}
            </Link>
          )}
          <Typography color="text.primary">
            {isEditMode ? 'Edit' : 'New Initiative'}
          </Typography>
        </Breadcrumbs>

        {/* Form Card */}
        <Card elevation={2}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Lightbulb color="primary" />
              <Typography variant="h5" fontWeight="600">
                {isEditMode ? 'Edit Initiative' : 'Create New Initiative'}
              </Typography>
            </Box>

            {!isEditMode && (
              <Alert severity="info" sx={{ mb: 4 }}>
                <Typography variant="subtitle2" fontWeight="600" gutterBottom>
                  Guided Initiative Creation
                </Typography>
                <Typography variant="body2">
                  Answer these structured questions to create a high-quality initiative. This structured input helps the AI generate more relevant discovery questions and produces better MRDs.
                </Typography>
              </Alert>
            )}

            {errors.submit && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {errors.submit}
              </Alert>
            )}

            <form onSubmit={handleSubmit}>
              {/* Title - Always shown */}
              <Box sx={{ mb: 4 }}>
                <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                  Initiative Title *
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  A clear, concise name (e.g., "Mobile Push Notifications", "Enterprise SSO Integration")
                </Typography>
                <TextField
                  fullWidth
                  value={formData.title}
                  onChange={handleChange('title')}
                  error={!!errors.title}
                  helperText={errors.title}
                  required
                  autoFocus
                  disabled={isLoading}
                  placeholder="Enter initiative title"
                />
              </Box>

              {/* Structured fields for NEW initiatives */}
              {!isEditMode && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <Divider>
                    <Typography variant="overline" fontWeight="600" color="text.secondary">
                      Initiative Details
                    </Typography>
                  </Divider>

                  {/* What */}
                  <Box>
                    <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                      What do you want to build? *
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      Describe the feature, product, or capability you want to create
                    </Typography>
                    <TextField
                      fullWidth
                      value={structuredData.what}
                      onChange={handleStructuredChange('what')}
                      error={!!errors.what}
                      helperText={errors.what}
                      required
                      multiline
                      rows={4}
                      disabled={isLoading}
                      placeholder="Example: A real-time push notification system for our mobile app that allows users to receive instant updates about important events like order status changes, messages from support, and promotional offers."
                    />
                  </Box>

                  {/* Who */}
                  <Box>
                    <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                      Who is it for? *
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      Identify your target users or customers
                    </Typography>
                    <TextField
                      fullWidth
                      value={structuredData.who}
                      onChange={handleStructuredChange('who')}
                      error={!!errors.who}
                      helperText={errors.who}
                      required
                      multiline
                      rows={3}
                      disabled={isLoading}
                      placeholder="Example: Active mobile app users (primarily iOS and Android), with focus on users who have opted-in for notifications. Secondary audience includes customer support team who will use this to send targeted messages."
                    />
                  </Box>

                  {/* Why */}
                  <Box>
                    <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                      Why is this important? *
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      Explain the problem you're solving and why now
                    </Typography>
                    <TextField
                      fullWidth
                      value={structuredData.why}
                      onChange={handleStructuredChange('why')}
                      error={!!errors.why}
                      helperText={errors.why}
                      required
                      multiline
                      rows={4}
                      disabled={isLoading}
                      placeholder="Example: Users currently miss time-sensitive updates because they have to manually check the app. Competitors offer push notifications and we're losing customers to them. Support data shows 40% of users request this feature. Will increase engagement and reduce support tickets."
                    />
                  </Box>

                  {/* Benefits */}
                  <Box>
                    <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                      What are the expected benefits? *
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      Describe measurable outcomes and business value
                    </Typography>
                    <TextField
                      fullWidth
                      value={structuredData.benefits}
                      onChange={handleStructuredChange('benefits')}
                      error={!!errors.benefits}
                      helperText={errors.benefits}
                      required
                      multiline
                      rows={4}
                      disabled={isLoading}
                      placeholder="Example: Increase daily active users by 25%, reduce time-to-action on urgent orders by 50%, decrease 'where is my order' support tickets by 30%, improve customer satisfaction scores, create new marketing channel for promotions."
                    />
                  </Box>

                  {/* Risks */}
                  <Box>
                    <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                      What are the potential risks or challenges? *
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      Identify known constraints, technical challenges, or concerns
                    </Typography>
                    <TextField
                      fullWidth
                      value={structuredData.risks}
                      onChange={handleStructuredChange('risks')}
                      error={!!errors.risks}
                      helperText={errors.risks}
                      required
                      multiline
                      rows={4}
                      disabled={isLoading}
                      placeholder="Example: Need to handle notification permissions carefully to avoid opt-out. Must comply with iOS/Android platform guidelines. Risk of notification fatigue if over-used. Requires backend infrastructure changes. Need to handle offline/delayed delivery gracefully."
                    />
                  </Box>
                </Box>
              )}

              {/* Description field for EDIT mode only */}
              {isEditMode && (
                <Box sx={{ mb: 4 }}>
                  <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                    Description
                  </Typography>
                  <TextField
                    fullWidth
                    value={formData.description}
                    onChange={handleChange('description')}
                    error={!!errors.description}
                    helperText={errors.description}
                    multiline
                    rows={8}
                    disabled={isLoading}
                  />
                </Box>
              )}

              {/* Status for edit mode */}
              {isEditMode && (
                <FormControl
                  fullWidth
                  margin="normal"
                  error={!!errors.status}
                  required
                  sx={{ mb: 4 }}
                >
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={formData.status}
                    label="Status"
                    onChange={handleChange('status')}
                    disabled={isLoading}
                  >
                    {statusOptions.map((option) => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}

              <Divider sx={{ my: 4 }} />

              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  startIcon={isLoading ? <CircularProgress size={20} /> : <Save />}
                  disabled={isLoading}
                >
                  {isLoading ? 'Saving...' : isEditMode ? 'Save Changes' : 'Create Initiative'}
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  startIcon={<Cancel />}
                  onClick={handleCancel}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
              </Box>
            </form>
          </CardContent>
        </Card>
      </Box>
    </MainLayout>
  );
}
