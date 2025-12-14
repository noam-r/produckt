import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  LinearProgress,
  Alert,
  CircularProgress,
  Paper,
  Divider,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Snackbar,
} from '@mui/material';
import {
  Person as PersonIcon,
  AccountBalance as BudgetIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  TrendingUp as TrendingUpIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/auth';
import MainLayout from '../layouts/MainLayout';

export default function UserProfile() {
  const { user } = useAuth();
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);

  // Helper function to safely convert budget values to numbers
  const safeNumber = (value) => {
    if (typeof value === 'number') return value;
    if (typeof value === 'string') return parseFloat(value) || 0;
    return 0;
  };
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
  });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  // Fetch detailed user profile with budget info
  const { data: userProfile, isLoading, error } = useQuery({
    queryKey: ['userProfile'],
    queryFn: authApi.getProfile,
  });

  const handleChangePassword = async () => {
    try {
      await authApi.changePassword(passwordData);
      setChangePasswordOpen(false);
      setPasswordData({ current_password: '', new_password: '' });
      setSnackbar({
        open: true,
        message: 'Password changed successfully',
        severity: 'success',
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Failed to change password',
        severity: 'error',
      });
    }
  };

  const getBudgetStatusColor = (utilization) => {
    if (utilization >= 90) return 'error';
    if (utilization >= 80) return 'warning';
    return 'success';
  };

  const getBudgetStatusIcon = (utilization) => {
    if (utilization >= 90) return <WarningIcon color="error" />;
    if (utilization >= 80) return <WarningIcon color="warning" />;
    return <CheckCircleIcon color="success" />;
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

  if (error) {
    return (
      <MainLayout>
        <Alert severity="error">
          Failed to load profile: {error.message}
        </Alert>
      </MainLayout>
    );
  }

  const budget = userProfile?.budget;
  const utilizationPercentage = safeNumber(budget?.utilization_percentage) || 0;

  return (
    <MainLayout>
      <Box>
        <Typography variant="h4" fontWeight="600" gutterBottom>
          User Profile
        </Typography>

        <Grid container spacing={3}>
          {/* Personal Information */}
          <Grid item xs={12} md={6}>
            <Card elevation={2}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <PersonIcon color="primary" />
                  <Typography variant="h6" fontWeight="600">
                    Personal Information
                  </Typography>
                </Box>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Name
                    </Typography>
                    <Typography variant="body1" fontWeight="500">
                      {userProfile?.name || 'N/A'}
                    </Typography>
                  </Box>

                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Email
                    </Typography>
                    <Typography variant="body1" fontWeight="500">
                      {userProfile?.email || 'N/A'}
                    </Typography>
                  </Box>

                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Organization
                    </Typography>
                    <Typography variant="body1" fontWeight="500">
                      {userProfile?.organization_name || 'N/A'}
                    </Typography>
                  </Box>

                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Roles
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {userProfile?.roles?.length > 0 ? (
                        userProfile.roles.map((role) => (
                          <Chip
                            key={role.id}
                            label={role.name}
                            size="small"
                            color={role.name === 'admin' ? 'error' : 'default'}
                          />
                        ))
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          No roles assigned
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </Box>

                <Divider sx={{ my: 3 }} />

                <Button
                  variant="outlined"
                  startIcon={<EditIcon />}
                  onClick={() => setChangePasswordOpen(true)}
                  fullWidth
                >
                  Change Password
                </Button>
              </CardContent>
            </Card>
          </Grid>

          {/* Budget Information */}
          <Grid item xs={12} md={6}>
            <Card elevation={2}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <BudgetIcon color="primary" />
                  <Typography variant="h6" fontWeight="600">
                    Monthly Budget
                  </Typography>
                  {getBudgetStatusIcon(utilizationPercentage)}
                </Box>

                {budget ? (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    {/* Budget Overview */}
                    <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                      <Grid container spacing={2}>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            Monthly Budget
                          </Typography>
                          <Typography variant="h6" fontWeight="600" color="primary.main">
                            ${safeNumber(budget.monthly_budget_usd).toFixed(2)}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            Current Spending
                          </Typography>
                          <Typography variant="h6" fontWeight="600">
                            ${safeNumber(budget.current_spending_usd).toFixed(2)}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            Remaining Budget
                          </Typography>
                          <Typography 
                            variant="h6" 
                            fontWeight="600"
                            color={safeNumber(budget.remaining_budget_usd) > 0 ? 'success.main' : 'error.main'}
                          >
                            ${safeNumber(budget.remaining_budget_usd).toFixed(2)}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            Utilization
                          </Typography>
                          <Typography 
                            variant="h6" 
                            fontWeight="600"
                            color={getBudgetStatusColor(utilizationPercentage) + '.main'}
                          >
                            {utilizationPercentage.toFixed(1)}%
                          </Typography>
                        </Grid>
                      </Grid>
                    </Paper>

                    {/* Budget Progress Bar */}
                    <Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                          Budget Utilization
                        </Typography>
                        <Typography variant="body2" fontWeight="500">
                          {utilizationPercentage.toFixed(1)}%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={Math.min(utilizationPercentage, 100)}
                        color={getBudgetStatusColor(utilizationPercentage)}
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          backgroundColor: 'action.hover',
                          '& .MuiLinearProgress-bar': {
                            borderRadius: 4,
                          }
                        }}
                      />
                    </Box>

                    {/* Budget Warnings */}
                    {utilizationPercentage >= 80 && (
                      <Alert 
                        severity={utilizationPercentage >= 90 ? 'error' : 'warning'}
                        icon={<WarningIcon />}
                      >
                        {utilizationPercentage >= 90 
                          ? 'You have exceeded 90% of your monthly budget. Consider reducing AI usage or contact your administrator.'
                          : 'You have used over 80% of your monthly budget. Monitor your usage to avoid exceeding your limit.'
                        }
                      </Alert>
                    )}

                    {/* Budget Status */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <TrendingUpIcon color="action" fontSize="small" />
                      <Typography variant="body2" color="text.secondary">
                        Budget resets monthly on the 1st
                      </Typography>
                    </Box>
                  </Box>
                ) : (
                  <Alert severity="info">
                    Budget information is not available
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Change Password Dialog */}
        <Dialog open={changePasswordOpen} onClose={() => setChangePasswordOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Change Password</DialogTitle>
          <DialogContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
              <TextField
                label="Current Password"
                type="password"
                value={passwordData.current_password}
                onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
                fullWidth
                required
              />
              <TextField
                label="New Password"
                type="password"
                value={passwordData.new_password}
                onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                fullWidth
                required
                helperText="Minimum 8 characters with uppercase, lowercase, and number"
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setChangePasswordOpen(false)}>Cancel</Button>
            <Button
              onClick={handleChangePassword}
              variant="contained"
              disabled={!passwordData.current_password || !passwordData.new_password}
            >
              Change Password
            </Button>
          </DialogActions>
        </Dialog>

        {/* Snackbar for notifications */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert
            onClose={() => setSnackbar({ ...snackbar, open: false })}
            severity={snackbar.severity}
            sx={{ width: '100%' }}
          >
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Box>
    </MainLayout>
  );
}