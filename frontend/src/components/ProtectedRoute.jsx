import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ChangePasswordDialog from './ChangePasswordDialog';

export default function ProtectedRoute({ children }) {
  const { user, initialCheckDone } = useAuth();

  console.log('ProtectedRoute - initialCheckDone:', initialCheckDone, 'user:', user);

  // If we have a user (from cache or server), check if password change is required
  if (user) {
    console.log('ProtectedRoute - user authenticated, rendering children');

    // Show forced password change dialog if required
    if (user.force_password_change) {
      return (
        <>
          {children}
          <ChangePasswordDialog open={true} onClose={() => {}} forceChange={true} />
        </>
      );
    }

    return children;
  }

  // Only redirect to login after initial check is done
  // This prevents redirect during the brief moment while checking session
  if (initialCheckDone && !user) {
    console.log('ProtectedRoute - no user after check, redirecting to login');
    return <Navigate to="/login" replace />;
  }

  // During initial check (very brief, usually instant with cache), render nothing
  // The HTML loader will show during this time
  console.log('ProtectedRoute - waiting for initial check');
  return null;
}
