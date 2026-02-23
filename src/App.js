import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Login from './pages/Login';
import SignUp from './pages/SignUp';
import Home from './pages/Home';
import ImageAnalysis from './pages/ImageAnalysis';
import DiagnosisReport from './pages/DiagnosisReport';
import History from './pages/History';
import AnalysisHistory from './pages/AnalysisHistory';
import UserProfile from './pages/UserProfile';

function App() {
  return (
    <ThemeProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/home" element={<Home />} />
          <Route path="/analysis" element={<ImageAnalysis />} />
          <Route path="/diagnosis" element={<DiagnosisReport />} />
          <Route path="/history" element={<History />} />
          <Route path="/analysis-history" element={<AnalysisHistory />} />
          <Route path="/profile" element={<UserProfile />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;
