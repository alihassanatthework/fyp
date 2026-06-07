/**
 * NotFound — replaces the wildcard redirect to /. Shows a clear
 * message and a back-to-home button. (P2.)
 */
import { useNavigate } from 'react-router-dom';
import { Home, AlertTriangle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import './NotFound.css';

export default function NotFound() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  return (
    <div className="nf-page">
      <div className="nf-card">
        <div className="nf-icon" aria-hidden="true">
          <AlertTriangle size={28}/>
        </div>
        <h1 className="nf-title">404 — Page Not Found</h1>
        <p className="nf-sub">
          The page you were looking for doesn't exist or has been moved.
        </p>
        <div className="nf-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => navigate(isAuthenticated ? '/home' : '/')}
          >
            <Home size={14}/> {isAuthenticated ? 'Back to dashboard' : 'Back to login'}
          </button>
        </div>
      </div>
    </div>
  );
}
