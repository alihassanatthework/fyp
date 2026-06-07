import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './pages/Login';
import SignUp from './pages/SignUp';
import Home from './pages/Home';
import ImageAnalysis from './pages/ImageAnalysis';
import DiagnosisReport from './pages/DiagnosisReport';
import AnalysisHistory from './pages/AnalysisHistory';
import UserProfile from './pages/UserProfile';
import Contact from './pages/Contact';
import Terms from './pages/Terms';
import Privacy from './pages/Privacy';
import Consent from './pages/Consent';
import SkinTreatment from './pages/SkinTreatment';
import ScalpTreatment from './pages/ScalpTreatment';
import Report from './pages/Report';
import MakeupAssistance from './pages/MakeupAssistance';
import FashionAssistance from './pages/FashionAssistance';
import Bookings from './pages/Bookings';
import NotFound from './pages/NotFound';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';

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
            {/* Public auth routes */}
            <Route path="/"                              element={<Login />} />
            <Route path="/signup"                        element={<SignUp />} />
            <Route path="/forgot-password"               element={<ForgotPassword />} />
            <Route path="/reset-password/:uid/:token"    element={<ResetPassword />} />

            {/* Public static pages (P2 — must be reachable without auth) */}
            <Route path="/terms"              element={<Terms />} />
            <Route path="/privacy"            element={<Privacy />} />
            <Route path="/consent"            element={<Consent />} />
            <Route path="/contact"            element={<Contact />} />
            <Route path="/scalp-treatment"    element={<ScalpTreatment />} />
            <Route path="/skin-treatment"     element={<SkinTreatment />} />
            <Route path="/report"             element={<Report />} />

            {/* /history → /analysis-history (P3 deduplication) */}
            <Route path="/history"            element={<Navigate to="/analysis-history" replace />} />

            {/* Protected routes — require a valid JWT */}
            <Route path="/home"               element={<ProtectedRoute><Home /></ProtectedRoute>} />
            <Route path="/analysis"           element={<ProtectedRoute><ImageAnalysis /></ProtectedRoute>} />
            <Route path="/diagnosis"          element={<ProtectedRoute><DiagnosisReport /></ProtectedRoute>} />
            <Route path="/analysis-history"   element={<ProtectedRoute><AnalysisHistory /></ProtectedRoute>} />
            <Route path="/profile"            element={<ProtectedRoute><UserProfile /></ProtectedRoute>} />
            <Route path="/makeup-assistance"  element={<ProtectedRoute><MakeupAssistance /></ProtectedRoute>} />
            <Route path="/fashion-assistance" element={<ProtectedRoute><FashionAssistance /></ProtectedRoute>} />
            <Route path="/bookings"           element={<ProtectedRoute><Bookings /></ProtectedRoute>} />

            {/* Proper 404 page instead of silent redirect to / */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
