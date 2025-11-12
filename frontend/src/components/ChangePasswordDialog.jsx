import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Alert,
  IconButton,
  InputAdornment,
  Box,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import { Visibility, VisibilityOff, CheckCircle, Cancel } from '@mui/icons-material';
import { authApi } from '../api/auth';

export default function ChangePasswordDialog({ open, onClose, forceChange = false }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  // Password validation rules
  const validationRules = [
    { label: 'At least 8 characters long', test: (pwd) => pwd.length >= 8 },
    { label: 'Contains uppercase letter (A-Z)', test: (pwd) => /[A-Z]/.test(pwd) },
    { label: 'Contains lowercase letter (a-z)', test: (pwd) => /[a-z]/.test(pwd) },
    { label: 'Contains digit (0-9)', test: (pwd) => /\d/.test(pwd) },
    { label: 'Contains special character (!@#$%^&*(),.?":{}|<>)', test: (pwd) => /[!@#$%^&*(),.?":{}|<>]/.test(pwd) },
    { label: 'No more than 3 identical characters in a row (e.g., aaaa)', test: (pwd) => !/(.)\1{3,}/.test(pwd) },
    { label: 'Not a common password (e.g., password123, admin)', test: (pwd) => {
      const weak = ['password', 'password123', '12345678', 'qwerty', 'abc123', 'password1', '123456789', 'admin123', 'letmein', 'welcome', '1234', '1111', '0000', 'admin', 'root', 'test'];
      return !weak.includes(pwd.toLowerCase());
    }},
    { label: 'Different from current password', test: (pwd, curr) => pwd !== curr, needsCurrent: true },
  ];

  const getPasswordStrength = (pwd) => {
    const passedRules = validationRules.filter((rule) => {
      if (rule.needsCurrent) return true; // Don't count this in strength
      return rule.test(pwd);
    }).length;
    return passedRules;
  };

  const isPasswordValid = (pwd, curr = '') => {
    return validationRules.every((rule) => {
      if (rule.needsCurrent) return rule.test(pwd, curr);
      return rule.test(pwd);
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    // Validation
    if (!currentPassword || !newPassword || !confirmPassword) {
      setError('Please fill in all fields');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    if (!isPasswordValid(newPassword, currentPassword)) {
      setError('New password does not meet complexity requirements');
      return;
    }

    setLoading(true);
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });

      setSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');

      // If forced password change, reload the page to refresh session
      if (forceChange) {
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        setTimeout(() => {
          onClose();
        }, 1500);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (forceChange) {
      // Cannot close if password change is forced
      return;
    }
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setError('');
    setSuccess(false);
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      disableEscapeKeyDown={forceChange}
    >
      <DialogTitle>
        {forceChange ? 'Password Change Required' : 'Change Password'}
      </DialogTitle>
      <DialogContent>
        {forceChange && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            You must change your password before continuing. Your current password is a default
            password and is not secure.
          </Alert>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Password changed successfully! {forceChange && 'Reloading...'}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            fullWidth
            type={showCurrentPassword ? 'text' : 'password'}
            label="Current Password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            margin="normal"
            required
            disabled={loading || success}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    edge="end"
                  >
                    {showCurrentPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            type={showNewPassword ? 'text' : 'password'}
            label="New Password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            margin="normal"
            required
            disabled={loading || success}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowNewPassword(!showNewPassword)} edge="end">
                    {showNewPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            type={showConfirmPassword ? 'text' : 'password'}
            label="Confirm New Password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            margin="normal"
            required
            disabled={loading || success}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    edge="end"
                  >
                    {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Password Requirements:
            </Typography>
            <List dense>
              {validationRules.map((rule, idx) => {
                const passed = rule.needsCurrent
                  ? rule.test(newPassword, currentPassword)
                  : rule.test(newPassword);
                // Only show green check if password is not empty and rule passes
                const showPassed = newPassword && passed;
                return (
                  <ListItem key={idx} sx={{ py: 0 }}>
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      {showPassed ? (
                        <CheckCircle color="success" fontSize="small" />
                      ) : (
                        <Cancel color="error" fontSize="small" />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={rule.label}
                      primaryTypographyProps={{
                        variant: 'body2',
                        color: showPassed ? 'success.main' : 'text.secondary',
                      }}
                    />
                  </ListItem>
                );
              })}
            </List>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        {!forceChange && (
          <Button onClick={handleClose} disabled={loading || success}>
            Cancel
          </Button>
        )}
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={loading || success || !isPasswordValid(newPassword, currentPassword) || newPassword !== confirmPassword}
        >
          {loading ? 'Changing...' : 'Change Password'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
