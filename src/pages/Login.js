import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Sun, Moon, User, Eye, EyeOff } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import './Login.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const handleLogin = async (e) => {
    e.preventDefault();
    const result = await login(email, password);
    if (result.success) {
      navigate('/home');
    }
  };

  return (
    <div className="login-page">
      <header className="login-header">
        <div className="login-header-content">
          <div className="flex items-center gap-2">
            <span className="navbar-logo">ME.</span>
            <span className="navbar-divider">·</span>
            <span className="navbar-title">Login</span>
          </div>
          <div className="navbar-right">
            <div className="theme-toggle">
              <button onClick={() => toggleTheme('light')} className={`theme-btn ${theme==='light' ? 'active' : ''}`}>
                <Sun size={12}/> Light
              </button>
              <button onClick={() => toggleTheme('dark')} className={`theme-btn ${theme==='dark' ? 'active' : ''}`}>
                <Moon size={12}/> Dark
              </button>
            </div>
            <button className="profile-btn">
              <User size={14}/> Profile
            </button>
          </div>
        </div>
      </header>

      <main className="login-main">
        <div className="card login-card">
          <h1 className="login-title">Login to AI Assistant</h1>

          <form onSubmit={handleLogin} className="login-form">
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="Enter your email"
                className="input-field"
                required
              />
            </div>

            <div className="form-group">
              <label>Password</label>
              <div className="password-wrapper">
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="input-field"
                  style={{ paddingRight: '2.5rem' }}
                  required
                />
                <button type="button" onClick={() => setShowPass(!showPass)} className="password-toggle">
                  {showPass ? <EyeOff size={16}/> : <Eye size={16}/>}
                </button>
              </div>
            </div>

            <button type="submit" className="btn btn-primary w-full">
              Login
            </button>

            <div className="forgot-password">
              <button type="button">
                Forgot Password?
              </button>
            </div>

            <p className="login-footer-text">
              Don't have an account?{' '}
              <Link to="/signup">Sign Up</Link>
            </p>
          </form>
        </div>
      </main>

      <footer className="login-footer">
        <button>Help</button>
        <button>Support</button>
      </footer>
    </div>
  );
}




