import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './pages/Login';
import SignUp from './pages/SignUp';
import Home from './pages/Home';
import ImageAnalysis from './pages/ImageAnalysis';
import DiagnosisReport from './pages/DiagnosisReport';
import History from './pages/History';
import AnalysisHistory from './pages/AnalysisHistory';
import UserProfile from './pages/UserProfile';

// Redirects unauthenticated users to /login.
// Shows nothing while the auth state is still loading (prevents flash of login page).
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  return isAuthenticated ? children : <Navigate to="/" replace />;
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Login />} />
            <Route path="/signup" element={<SignUp />} />

            {/* Protected routes — require a valid JWT */}
            <Route path="/home"             element={<ProtectedRoute><Home /></ProtectedRoute>} />
            <Route path="/analysis"         element={<ProtectedRoute><ImageAnalysis /></ProtectedRoute>} />
            <Route path="/diagnosis"        element={<ProtectedRoute><DiagnosisReport /></ProtectedRoute>} />
            <Route path="/history"          element={<ProtectedRoute><History /></ProtectedRoute>} />
            <Route path="/analysis-history" element={<ProtectedRoute><AnalysisHistory /></ProtectedRoute>} />
            <Route path="/profile"          element={<ProtectedRoute><UserProfile /></ProtectedRoute>} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;