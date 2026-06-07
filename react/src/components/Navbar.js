import { useState, useEffect } from 'react';
import { Sun, Moon, User, LogOut, Menu, X, Home as HomeIcon, History as HistoryIcon, Mail } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useNavigate, NavLink, useLocation } from 'react-router-dom';
import './Navbar.css';
import { useAuth } from '../contexts/AuthContext';

// `title` / `subtitle` props are accepted for backward compatibility with
// existing callers but are intentionally unused — the navbar is identical
// on every page so each page renders its own H1 inside <main>.
// eslint-disable-next-line no-unused-vars
export default function Navbar({ title, subtitle }) {
  const { theme, toggleTheme } = useTheme();
  const { logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Close the drawer whenever the route changes (e.g. user tapped a link).
  useEffect(() => { setDrawerOpen(false); }, [location.pathname]);

  // Lock body scroll while the drawer is open so iOS Safari doesn't bounce.
  useEffect(() => {
    if (drawerOpen) document.body.style.overflow = 'hidden';
    else            document.body.style.overflow = '';
    return () => { document.body.style.overflow = ''; };
  }, [drawerOpen]);

  const handleLogout = () => {
    setDrawerOpen(false);
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
        </div>

        {isAuthenticated && (
          <nav className="navbar-links">
            <NavLink to="/home"             className={({isActive}) => `navbar-link ${isActive ? 'active' : ''}`}>Home</NavLink>
            <NavLink to="/analysis-history" className={({isActive}) => `navbar-link ${isActive ? 'active' : ''}`}>Reports</NavLink>
            <NavLink to="/contact"          className={({isActive}) => `navbar-link ${isActive ? 'active' : ''}`}>Contact</NavLink>
          </nav>
        )}

        <div className="navbar-right">
          <div className="theme-toggle">
            <button
              onClick={() => toggleTheme('light')}
              className={`theme-btn ${theme === 'light' ? 'active' : ''}`}
              aria-label="Light mode"
            >
              <Sun size={13} aria-hidden="true" /> Light
            </button>
            <button
              onClick={() => toggleTheme('dark')}
              className={`theme-btn ${theme === 'dark' ? 'active' : ''}`}
              aria-label="Dark mode"
            >
              <Moon size={13} aria-hidden="true" /> Dark
            </button>
          </div>

          <button onClick={() => navigate('/profile')} className="profile-btn">
            <User size={16} aria-hidden="true" /> Profile
          </button>

          {isAuthenticated && (
            <button onClick={handleLogout} className="logout-btn">
              <LogOut size={16} aria-hidden="true" /> Logout
            </button>
          )}

          {/* Mobile-only hamburger — hidden ≥769px via CSS. */}
          <button
            type="button"
            className="navbar-hamburger"
            aria-label={drawerOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={drawerOpen}
            onClick={() => setDrawerOpen((s) => !s)}
          >
            {drawerOpen ? <X size={22} aria-hidden="true"/> : <Menu size={22} aria-hidden="true"/>}
          </button>
        </div>
      </div>

      {/* ── Mobile drawer + backdrop (CSS hides on desktop) ── */}
      <div
        className={`navbar-drawer-backdrop ${drawerOpen ? 'open' : ''}`}
        onClick={() => setDrawerOpen(false)}
        aria-hidden="true"
      />
      <aside
        className={`navbar-drawer ${drawerOpen ? 'open' : ''}`}
        aria-hidden={!drawerOpen}
      >
        <nav className="navbar-drawer-nav">
          {isAuthenticated && (
            <>
              <NavLink to="/home"             className={({isActive}) => `navbar-drawer-link ${isActive ? 'active' : ''}`}>
                <HomeIcon size={18}/> Home
              </NavLink>
              <NavLink to="/analysis-history" className={({isActive}) => `navbar-drawer-link ${isActive ? 'active' : ''}`}>
                <HistoryIcon size={18}/> Reports
              </NavLink>
              <NavLink to="/contact"          className={({isActive}) => `navbar-drawer-link ${isActive ? 'active' : ''}`}>
                <Mail size={18}/> Contact
              </NavLink>
              <NavLink to="/profile"          className={({isActive}) => `navbar-drawer-link ${isActive ? 'active' : ''}`}>
                <User size={18}/> Profile
              </NavLink>
              <button onClick={handleLogout} className="navbar-drawer-link navbar-drawer-logout">
                <LogOut size={18}/> Logout
              </button>
            </>
          )}
          {!isAuthenticated && (
            <>
              <NavLink to="/"       className="navbar-drawer-link">Login</NavLink>
              <NavLink to="/signup" className="navbar-drawer-link">Sign Up</NavLink>
            </>
          )}
        </nav>
      </aside>
    </header>
  );
}
