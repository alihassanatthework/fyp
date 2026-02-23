import { Sun, Moon, User } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useNavigate } from 'react-router-dom';
import './Navbar.css';

export default function Navbar({ title, subtitle }) {
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-left">
          <span className="navbar-logo">ME.</span>
          {title && (
            <>
              <span className="navbar-divider">·</span>
              <div>
                <span className="navbar-title">{title}</span>
                {subtitle && <div className="navbar-subtitle">{subtitle}</div>}
              </div>
            </>
          )}
        </div>

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
        </div>
      </div>
    </header>
  );
}
