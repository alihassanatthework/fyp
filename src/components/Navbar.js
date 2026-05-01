import { Sun, Moon, User, LogOut } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useNavigate, NavLink } from 'react-router-dom';
import './Navbar.css';
import { useAuth } from '../contexts/AuthContext';

export default function Navbar({ title, subtitle }) {
  const { theme, toggleTheme } = useTheme();
  const { logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-left">
          <span
            className="navbar-logo"
            role="button"
            tabIndex={0}
            onClick={() => navigate('/home')}
            onKeyDown={(e) => { if (e.key === 'Enter') navigate('/home'); }}
          >
            ME
          </span>
          {title && (
            <div className="navbar-title-wrap">
              <span className="navbar-title">{title}</span>
              {subtitle && <div className="navbar-subtitle">{subtitle}</div>}
            </div>
          )}
        </div>

        {isAuthenticated && (
          <nav className="navbar-links">
            <NavLink to="/home" className={({isActive}) => `navbar-link ${isActive ? 'active' : ''}`}>Home</NavLink>
            <NavLink to="/analysis-history" className={({isActive}) => `navbar-link ${isActive ? 'active' : ''}`}>History</NavLink>
            <NavLink to="/diagnosis" className={({isActive}) => `navbar-link ${isActive ? 'active' : ''}`}>Diagnosis</NavLink>
            <NavLink to="/contact" className={({isActive}) => `navbar-link ${isActive ? 'active' : ''}`}>Contact</NavLink>
          </nav>
        )}

        <div className="navbar-right">
          <div className="theme-toggle">
            <button
              onClick={() => toggleTheme('light')}
              className={`theme-btn ${theme === 'light' ? 'active' : ''}`}
            >
              <Sun size={13} /> Light
            </button>
            <button
              onClick={() => toggleTheme('dark')}
              className={`theme-btn ${theme === 'dark' ? 'active' : ''}`}
            >
              <Moon size={13} /> Dark
            </button>
          </div>

          <button onClick={() => navigate('/profile')} className="profile-btn">
            <User size={16} /> Profile
          </button>

          {isAuthenticated && (
            <button onClick={handleLogout} className="logout-btn">
              <LogOut size={16} /> Logout
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
