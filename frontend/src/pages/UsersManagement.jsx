import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Alert,
  Snackbar,
  CircularProgress,
  Tooltip,
  OutlinedInput,
  InputAdornment,
  Checkbox,
  ListItemText,
  LinearProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  VpnKey as KeyIcon,
  ContentCopy as CopyIcon,
  Refresh as RefreshIcon,
  AccountBalance as BudgetIcon,
} from '@mui/icons-material';
import adminApi from '../api/admin';
import { generateSecurePassword } from '../utils/passwordGenerator';
import MainLayout from '../layouts/MainLayout';

export default function UsersManagement() {
  const queryClient = useQueryClient();
  const [openDialog, setOpenDialog] = useState(false);

  // Helper function to safely convert budget values to numbers
  const safeNumber = (value) => {
    if (typeof value === 'number') return value;
    if (typeof value === 'string') return parseFloat(value) || 0;
    return 0;
  };
  const [openPasswordDialog, setOpenPasswordDialog] = useState(false);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [openBudgetDialog, setOpenBudgetDialog] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  // Form state
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    password: '',
    generate_password: false,
    role_ids: [],
    is_active: true,
    force_password_change: false,
  });

  const [passwordData, setPasswordData] = useState({
    password: '',
    generate_password: false,
  });

  const [budgetData, setBudgetData] = useState({
    monthly_budget_usd: 100.00,
  });

  // Fetch users
  const { data: usersData, isLoading: loadingUsers } = useQuery({
    queryKey: ['users'],
    queryFn: adminApi.getUsers,
  });

  // Fetch roles
  const { data: roles, isLoading: loadingRoles } = useQuery({
    queryKey: ['roles'],
    queryFn: adminApi.getRoles,
  });

  // Create user mutation
  const createUserMutation = useMutation({
    mutationFn: adminApi.createUser,
    onSuccess: () => {
      queryClient.invalidateQueries(['users']);
      handleCloseDialog();
      setSnackbar({
        open: true,
        message: 'User created successfully',
        severity: 'success',
      });
    },
    onError: (error) => {
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Failed to create user',
        severity: 'error',
      });
    },
  });

  // Update user mutation
  const updateUserMutation = useMutation({
    mutationFn: ({ userId, data }) => adminApi.updateUser(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['users']);
      handleCloseDialog();
      setSnackbar({
        open: true,
        message: 'User updated successfully',
        severity: 'success',
      });
    },
    onError: (error) => {
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Failed to update user',
        severity: 'error',
      });
    },
  });

  // Change password mutation
  const changePasswordMutation = useMutation({
    mutationFn: ({ userId, data }) => adminApi.changePassword(userId, data),
    onSuccess: () => {
      handleClosePasswordDialog();
      setSnackbar({
        open: true,
        message: 'Password changed successfully',
        severity: 'success',
      });
    },
    onError: (error) => {
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Failed to change password',
        severity: 'error',
      });
    },
  });

  // Delete user mutation
  const deleteUserMutation = useMutation({
    mutationFn: adminApi.deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries(['users']);
      handleCloseDeleteDialog();
      setSnackbar({
        open: true,
        message: 'User deleted successfully',
        severity: 'success',
      });
    },
    onError: (error) => {
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Failed to delete user',
        severity: 'error',
      });
    },
  });

  // Update budget mutation
  const updateBudgetMutation = useMutation({
    mutationFn: ({ userId, data }) => adminApi.updateUserBudget(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['users']);
      handleCloseBudgetDialog();
      setSnackbar({
        open: true,
        message: 'Budget updated successfully',
        severity: 'success',
      });
    },
    onError: (error) => {
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Failed to update budget',
        severity: 'error',
      });
    },
  });

  // Dialog handlers
  const handleOpenCreateDialog = () => {
    setEditingUser(null);
    setFormData({
      email: '',
      name: '',
      password: '',
      generate_password: false,
      role_ids: [],
      is_active: true,
      force_password_change: false,
    });
    setOpenDialog(true);
  };

  const handleOpenEditDialog = (user) => {
    setEditingUser(user);
    setFormData({
      email: user.email,
      name: user.name,
      role_ids: user.roles.map(r => r.id),
      is_active: user.is_active,
      force_password_change: user.force_password_change || false,
    });
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingUser(null);
  };

  const handleOpenPasswordDialog = (user) => {
    setSelectedUser(user);
    setPasswordData({
      password: '',
      generate_password: false,
    });
    setOpenPasswordDialog(true);
  };

  const handleClosePasswordDialog = () => {
    setOpenPasswordDialog(false);
    setSelectedUser(null);
  };

  const handleOpenDeleteDialog = (user) => {
    setSelectedUser(user);
    setOpenDeleteDialog(true);
  };

  const handleCloseDeleteDialog = () => {
    setOpenDeleteDialog(false);
    setSelectedUser(null);
  };

  const handleOpenBudgetDialog = (user) => {
    setSelectedUser(user);
    setBudgetData({
      monthly_budget_usd: user.budget?.monthly_budget_usd || 100.00,
    });
    setOpenBudgetDialog(true);
  };

  const handleCloseBudgetDialog = () => {
    setOpenBudgetDialog(false);
    setSelectedUser(null);
  };

  // Form submission
  const handleSubmit = () => {
    if (editingUser) {
      updateUserMutation.mutate({
        userId: editingUser.id,
        data: {
          email: formData.email,
          name: formData.name,
          role_ids: formData.role_ids,
          is_active: formData.is_active,
          force_password_change: formData.force_password_change,
        },
      });
    } else {
      createUserMutation.mutate(formData);
    }
  };

  const handlePasswordSubmit = () => {
    changePasswordMutation.mutate({
      userId: selectedUser.id,
      data: passwordData,
    });
  };

  const handleDeleteConfirm = () => {
    deleteUserMutation.mutate(selectedUser.id);
  };

  const handleBudgetSubmit = () => {
    updateBudgetMutation.mutate({
      userId: selectedUser.id,
      data: budgetData,
    });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setSnackbar({
      open: true,
      message: 'Copied to clipboard',
      severity: 'info',
    });
  };

  if (loadingUsers || loadingRoles) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const users = usersData?.users || [];

  return (
    <MainLayout>
      <Box>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h4" fontWeight="600">
            User Management
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleOpenCreateDialog}
          >
            Create User
          </Button>
        </Box>

        <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Name</strong></TableCell>
              <TableCell><strong>Email</strong></TableCell>
              <TableCell><strong>Roles</strong></TableCell>
              <TableCell><strong>Budget Status</strong></TableCell>
              <TableCell><strong>Status</strong></TableCell>
              <TableCell align="right"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.id}>
                <TableCell>{user.name}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>
                  <Box display="flex" gap={0.5} flexWrap="wrap">
                    {user.roles.length > 0 ? (
                      user.roles.map((role) => (
                        <Chip
                          key={role.id}
                          label={role.name}
                          size="small"
                          color={role.name === 'admin' ? 'error' : 'default'}
                        />
                      ))
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        No roles
                      </Typography>
                    )}
                  </Box>
                </TableCell>
                <TableCell>
                  {user.budget ? (
                    <Box>
                      <Typography variant="body2" fontWeight="500">
                        ${safeNumber(user.budget.current_spending_usd).toFixed(2)} / ${safeNumber(user.budget.monthly_budget_usd).toFixed(2)}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                        <Box sx={{ width: 60, mr: 1 }}>
                          <LinearProgress
                            variant="determinate"
                            value={Math.min(user.budget.utilization_percentage, 100)}
                            color={
                              user.budget.utilization_percentage >= 90 ? 'error' :
                              user.budget.utilization_percentage >= 80 ? 'warning' : 'success'
                            }
                            sx={{ height: 4, borderRadius: 2 }}
                          />
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          {safeNumber(user.budget.utilization_percentage).toFixed(0)}%
                        </Typography>
                      </Box>
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No budget info
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Chip
                    label={user.is_active ? 'Active' : 'Inactive'}
                    color={user.is_active ? 'success' : 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="Edit">
                    <IconButton size="small" onClick={() => handleOpenEditDialog(user)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Change Password">
                    <IconButton size="small" onClick={() => handleOpenPasswordDialog(user)}>
                      <KeyIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Manage Budget">
                    <IconButton size="small" onClick={() => handleOpenBudgetDialog(user)}>
                      <BudgetIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton size="small" onClick={() => handleOpenDeleteDialog(user)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        </TableContainer>

        {/* Create/Edit User Dialog */}
        <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
          <DialogTitle>{editingUser ? 'Edit User' : 'Create New User'}</DialogTitle>
          <DialogContent>
            <Box display="flex" flexDirection="column" gap={2} pt={1}>
              <TextField
                label="Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                fullWidth
                required
              />
              <TextField
                label="Email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                fullWidth
                required
              />

              {!editingUser && (
                <>
                  <TextField
                  label="Password"
                  type="text"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  fullWidth
                  helperText="Minimum 8 characters. Make sure to copy this password and share it securely with the user."
                  InputProps={{
                    endAdornment: formData.password && (
                      <InputAdornment position="end">
                        <Tooltip title="Copy password">
                          <IconButton
                            onClick={() => copyToClipboard(formData.password)}
                            edge="end"
                            size="small"
                          >
                            <CopyIcon />
                          </IconButton>
                        </Tooltip>
                      </InputAdornment>
                    ),
                  }}
                />
                <Button
                  onClick={() => {
                    const newPassword = generateSecurePassword();
                    setFormData({ ...formData, password: newPassword });
                  }}
                  startIcon={<RefreshIcon />}
                  variant="outlined"
                  fullWidth
                >
                  Generate Secure Password
                </Button>
                {formData.password && (
                  <Alert severity="warning">
                    Make sure to save this password! It won't be shown again after you submit.
                  </Alert>
                )}
              </>
            )}

            <FormControl fullWidth>
              <InputLabel>Roles</InputLabel>
              <Select
                multiple
                value={formData.role_ids}
                onChange={(e) => setFormData({ ...formData, role_ids: e.target.value })}
                input={<OutlinedInput label="Roles" />}
                renderValue={(selected) =>
                  selected
                    .map(id => roles?.find(r => r.id === id)?.name)
                    .filter(Boolean)
                    .join(', ')
                }
              >
                {roles?.map((role) => (
                  <MenuItem key={role.id} value={role.id}>
                    <Checkbox checked={formData.role_ids.indexOf(role.id) > -1} />
                    <ListItemText primary={role.name} secondary={role.description} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
              }
              label="Active"
            />

            {editingUser && (
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.force_password_change}
                    onChange={(e) => setFormData({ ...formData, force_password_change: e.target.checked })}
                  />
                }
                label="Force Password Change on Next Login"
              />
            )}
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog}>Cancel</Button>
            <Button
              onClick={handleSubmit}
              variant="contained"
              disabled={createUserMutation.isPending || updateUserMutation.isPending}
            >
              {createUserMutation.isPending || updateUserMutation.isPending ? (
                <CircularProgress size={24} />
              ) : editingUser ? (
                'Update'
              ) : (
                'Create'
              )}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Change Password Dialog */}
        <Dialog open={openPasswordDialog} onClose={handleClosePasswordDialog} maxWidth="sm" fullWidth>
          <DialogTitle>Change Password for {selectedUser?.name}</DialogTitle>
          <DialogContent>
            <Box display="flex" flexDirection="column" gap={2} pt={1}>
            <TextField
              label="New Password"
              type="text"
              value={passwordData.password}
              onChange={(e) => setPasswordData({ ...passwordData, password: e.target.value })}
              fullWidth
              helperText="Minimum 8 characters. Make sure to copy this password and share it securely with the user."
              InputProps={{
                endAdornment: passwordData.password && (
                  <InputAdornment position="end">
                    <Tooltip title="Copy password">
                      <IconButton
                        onClick={() => copyToClipboard(passwordData.password)}
                        edge="end"
                        size="small"
                      >
                        <CopyIcon />
                      </IconButton>
                    </Tooltip>
                  </InputAdornment>
                ),
              }}
            />
            <Button
              onClick={() => {
                const newPassword = generateSecurePassword();
                setPasswordData({ ...passwordData, password: newPassword });
              }}
              startIcon={<RefreshIcon />}
              variant="outlined"
              fullWidth
            >
              Generate Secure Password
            </Button>
            {passwordData.password && (
              <Alert severity="warning">
                Make sure to save this password! It won't be shown again after you submit.
              </Alert>
            )}
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClosePasswordDialog}>Cancel</Button>
            <Button
              onClick={handlePasswordSubmit}
              variant="contained"
              disabled={changePasswordMutation.isPending || !passwordData.password}
            >
              {changePasswordMutation.isPending ? <CircularProgress size={24} /> : 'Change Password'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Budget Management Dialog */}
        <Dialog open={openBudgetDialog} onClose={handleCloseBudgetDialog} maxWidth="sm" fullWidth>
          <DialogTitle>Manage Budget for {selectedUser?.name}</DialogTitle>
          <DialogContent>
            <Box display="flex" flexDirection="column" gap={2} pt={1}>
              {selectedUser?.budget && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  Current spending: ${safeNumber(selectedUser.budget.current_spending_usd).toFixed(2)} / 
                  ${safeNumber(selectedUser.budget.monthly_budget_usd).toFixed(2)} 
                  ({safeNumber(selectedUser.budget.utilization_percentage).toFixed(1)}% used)
                </Alert>
              )}
              
              <TextField
                label="Monthly Budget (USD)"
                type="number"
                value={budgetData.monthly_budget_usd}
                onChange={(e) => setBudgetData({ 
                  ...budgetData, 
                  monthly_budget_usd: parseFloat(e.target.value) || 0 
                })}
                fullWidth
                inputProps={{ 
                  min: 0, 
                  max: 10000, 
                  step: 0.01 
                }}
                helperText="Budget range: $0.00 - $10,000.00"
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseBudgetDialog}>Cancel</Button>
            <Button
              onClick={handleBudgetSubmit}
              variant="contained"
              disabled={updateBudgetMutation.isPending || budgetData.monthly_budget_usd < 0 || budgetData.monthly_budget_usd > 10000}
            >
              {updateBudgetMutation.isPending ? <CircularProgress size={24} /> : 'Update Budget'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={openDeleteDialog} onClose={handleCloseDeleteDialog}>
          <DialogTitle>Delete User</DialogTitle>
          <DialogContent>
            <Typography>
              Are you sure you want to delete user <strong>{selectedUser?.name}</strong>?
              This action cannot be undone.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDeleteDialog}>Cancel</Button>
            <Button
              onClick={handleDeleteConfirm}
              color="error"
              variant="contained"
              disabled={deleteUserMutation.isPending}
            >
              {deleteUserMutation.isPending ? <CircularProgress size={24} /> : 'Delete'}
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
