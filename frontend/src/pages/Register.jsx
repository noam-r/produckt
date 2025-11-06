import { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Link,
  Alert,
  CircularProgress,
  Container,
  IconButton,
  InputAdornment,
} from '@mui/material';
import { Visibility, VisibilityOff, LightMode, DarkMode } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

export default function Register() {
  const navigate = useNavigate();
  const { register, error: authError } = useAuth();
  const { mode, toggleTheme } = useTheme();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
    organizationName: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (field) => (e) => {
    setFormData({ ...formData, [field]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!formData.email || !formData.password || !formData.fullName || !formData.organizationName) {
      setError('Please fill in all required fields');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setLoading(true);
    const result = await register(
      formData.email,
      formData.password,
      formData.fullName,
      formData.organizationName
    );
    setLoading(false);

    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error || 'Registration failed');
    }
  };

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          py: 4,
        }}
      >
        {/* Theme Toggle Button */}
        <Box sx={{ position: 'absolute', top: 16, right: 16 }}>
          <IconButton onClick={toggleTheme} color="inherit">
            {mode === 'light' ? <DarkMode /> : <LightMode />}
          </IconButton>
        </Box>

        {/* Logo/Brand */}
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography variant="h3" component="h1" fontWeight="600" color="primary">
            ProDuckt
          </Typography>
          <Typography variant="subtitle1" color="text.secondary" sx={{ mt: 1 }}>
            AI-Powered Product Discovery
          </Typography>
        </Box>

        {/* Register Card */}
        <Card elevation={3}>
          <CardContent sx={{ p: 4 }}>
            <Typography variant="h5" component="h2" gutterBottom fontWeight="500">
              Create an account
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Get started with ProDuckt today
            </Typography>

            {/* Error Alert */}
            {(error || authError) && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error || authError}
              </Alert>
            )}

            {/* Register Form */}
            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Full Name"
                value={formData.fullName}
                onChange={handleChange('fullName')}
                margin="normal"
                autoComplete="name"
                autoFocus
                disabled={loading}
                required
              />

              <TextField
                fullWidth
                label="Email"
                type="email"
                value={formData.email}
                onChange={handleChange('email')}
                margin="normal"
                autoComplete="email"
                disabled={loading}
                required
              />

              <TextField
                fullWidth
                label="Organization Name"
                value={formData.organizationName}
                onChange={handleChange('organizationName')}
                margin="normal"
                autoComplete="organization"
                disabled={loading}
                required
                helperText="Your company or team name"
              />

              <TextField
                fullWidth
                label="Password"
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={handleChange('password')}
                margin="normal"
                autoComplete="new-password"
                disabled={loading}
                required
                helperText="Minimum 8 characters"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                        disabled={loading}
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <TextField
                fullWidth
                label="Confirm Password"
                type={showPassword ? 'text' : 'password'}
                value={formData.confirmPassword}
                onChange={handleChange('confirmPassword')}
                margin="normal"
                autoComplete="new-password"
                disabled={loading}
                required
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading}
                sx={{ mt: 3, mb: 2, py: 1.5 }}
              >
                {loading ? <CircularProgress size={24} /> : 'Create Account'}
              </Button>

              <Box sx={{ textAlign: 'center', mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Already have an account?{' '}
                  <Link
                    component={RouterLink}
                    to="/login"
                    underline="hover"
                    fontWeight="500"
                  >
                    Sign in
                  </Link>
                </Typography>
              </Box>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <Typography
          variant="body2"
          color="text.secondary"
          align="center"
          sx={{ mt: 4 }}
        >
          Powered by Claude 3.5 Sonnet
        </Typography>
      </Box>
    </Container>
  );
}
