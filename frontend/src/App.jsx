import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { queryClient } from './lib/queryClient';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import InitiativesList from './pages/InitiativesList';
import InitiativeDetail from './pages/InitiativeDetail';
import InitiativeForm from './pages/InitiativeForm';
import ContextManagement from './pages/ContextManagement';
import UsersManagement from './pages/UsersManagement';
import Analytics from './pages/Analytics';

function App() {
  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              {/* Protected routes */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/initiatives"
                element={
                  <ProtectedRoute>
                    <InitiativesList />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/initiatives/new"
                element={
                  <ProtectedRoute>
                    <InitiativeForm />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/initiatives/:id"
                element={
                  <ProtectedRoute>
                    <InitiativeDetail />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/initiatives/:id/edit"
                element={
                  <ProtectedRoute>
                    <InitiativeForm />
                  </ProtectedRoute>
                }
              />

              {/* Context route */}
              <Route
                path="/context"
                element={
                  <ProtectedRoute>
                    <ContextManagement />
                  </ProtectedRoute>
                }
              />

              {/* Admin routes */}
              <Route
                path="/admin/users"
                element={
                  <ProtectedRoute>
                    <UsersManagement />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/analytics"
                element={
                  <ProtectedRoute>
                    <Analytics />
                  </ProtectedRoute>
                }
              />

              {/* Default redirect */}
              <Route path="/" element={<Navigate to="/dashboard" replace />} />

              {/* 404 - catch all */}
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </BrowserRouter>
  );
}

export default App;
