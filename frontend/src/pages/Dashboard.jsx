import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Chip,
  IconButton,
} from '@mui/material';
import {
  Lightbulb,
  TrendingUp,
  CheckCircle,
  HourglassEmpty,
  Add,
  ArrowForward,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { useInitiatives } from '../hooks/useInitiatives';
import MainLayout from '../layouts/MainLayout';

// Status color mapping
const statusColors = {
  DRAFT: 'default',
  IN_DISCOVERY: 'info',
  IN_QA: 'warning',
  READY_FOR_MRD: 'secondary',
  COMPLETED: 'success',
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: initiatives, isLoading, error } = useInitiatives();

  // Calculate metrics
  const totalInitiatives = initiatives?.length || 0;
  const inProgress = initiatives?.filter(
    (i) => i.status === 'IN_DISCOVERY' || i.status === 'IN_QA'
  ).length || 0;
  const completed = initiatives?.filter((i) => i.status === 'COMPLETED').length || 0;
  const draft = initiatives?.filter((i) => i.status === 'DRAFT').length || 0;

  // Get recent initiatives (last 5)
  const recentInitiatives = initiatives?.slice(0, 5) || [];

  const metrics = [
    {
      title: 'Total Initiatives',
      value: totalInitiatives,
      icon: <Lightbulb sx={{ fontSize: 40 }} />,
      color: 'primary.main',
      bgColor: 'primary.light',
    },
    {
      title: 'In Progress',
      value: inProgress,
      icon: <TrendingUp sx={{ fontSize: 40 }} />,
      color: 'info.main',
      bgColor: 'info.light',
    },
    {
      title: 'Completed',
      value: completed,
      icon: <CheckCircle sx={{ fontSize: 40 }} />,
      color: 'success.main',
      bgColor: 'success.light',
    },
    {
      title: 'Draft',
      value: draft,
      icon: <HourglassEmpty sx={{ fontSize: 40 }} />,
      color: 'warning.main',
      bgColor: 'warning.light',
    },
  ];

  return (
    <MainLayout>
      <Box>
        {/* Header */}
        <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h4" fontWeight="600" gutterBottom>
              Welcome back, {user?.name?.split(' ')[0] || 'User'}!
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Here's what's happening with your initiatives today
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<Add />}
            size="large"
            onClick={() => navigate('/initiatives/new')}
          >
            New Initiative
          </Button>
        </Box>

        {/* Metrics Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {metrics.map((metric) => (
            <Grid item xs={12} sm={6} md={3} key={metric.title}>
              <Card
                elevation={2}
                sx={{
                  height: '140px',
                  width: '100%',
                  transition: 'all 0.3s ease-in-out',
                  '&:hover': {
                    elevation: 4,
                    transform: 'translateY(-4px)',
                    boxShadow: 3,
                  },
                }}
              >
                <CardContent sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 'auto' }}>
                    <Box sx={{ flex: 1, pr: 2, minWidth: 0 }}>
                      <Typography
                        variant="overline"
                        sx={{
                          fontWeight: 600,
                          letterSpacing: '1px',
                          fontSize: '0.7rem',
                          lineHeight: 1.4,
                          color: 'text.secondary',
                          display: 'block',
                          mb: 2,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {metric.title}
                      </Typography>
                      <Typography
                        variant="h3"
                        sx={{
                          fontWeight: 700,
                          fontSize: '2.75rem',
                          lineHeight: 1,
                          color: 'text.primary',
                        }}
                      >
                        {metric.value}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        p: 1.75,
                        borderRadius: 2.5,
                        bgcolor: metric.bgColor,
                        color: metric.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: 1,
                        flexShrink: 0,
                        width: '64px',
                        height: '64px',
                      }}
                    >
                      {metric.icon}
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Recent Initiatives */}
        <Card elevation={2}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6" fontWeight="600">
                Recent Initiatives
              </Typography>
              <Button
                endIcon={<ArrowForward />}
                onClick={() => navigate('/initiatives')}
              >
                View All
              </Button>
            </Box>

            {isLoading && (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            )}

            {error && (
              <Alert severity="error">
                Failed to load initiatives: {error.message}
              </Alert>
            )}

            {!isLoading && !error && recentInitiatives.length === 0 && (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  No initiatives yet
                </Typography>
                <Button
                  variant="outlined"
                  startIcon={<Add />}
                  sx={{ mt: 2 }}
                  onClick={() => navigate('/initiatives/new')}
                >
                  Create Your First Initiative
                </Button>
              </Box>
            )}

            {!isLoading && !error && recentInitiatives.length > 0 && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {recentInitiatives.map((initiative) => (
                  <Card
                    key={initiative.id}
                    variant="outlined"
                    sx={{
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      '&:hover': {
                        boxShadow: 2,
                        borderColor: 'primary.main',
                      },
                    }}
                    onClick={() => navigate(`/initiatives/${initiative.id}`)}
                  >
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="h6" fontWeight="600" gutterBottom>
                            {initiative.title}
                          </Typography>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                            }}
                          >
                            {initiative.description || 'No description'}
                          </Typography>
                        </Box>
                        <Chip
                          label={initiative.status.replace('_', ' ')}
                          color={statusColors[initiative.status]}
                          size="small"
                          sx={{ ml: 2 }}
                        />
                      </Box>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>
    </MainLayout>
  );
}
