import { Navigate } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  console.log('ProtectedRoute - loading:', loading, 'user:', user);

  // Show loading spinner while checking authentication
  if (loading) {
    console.log('ProtectedRoute - showing loading spinner');
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  // Redirect to login if not authenticated
  if (!user) {
    console.log('ProtectedRoute - no user, redirecting to login');
    return <Navigate to="/login" replace />;
  }

  // Render children if authenticated
  console.log('ProtectedRoute - user authenticated, rendering children');
  return children;
}
