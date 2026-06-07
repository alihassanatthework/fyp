import { useState, useRef, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Sun, Moon, User, Eye, EyeOff } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import AuthShaderBackground from '../components/AuthShaderBackground';
import './Login.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  // ── 3D parallax tilt on the login card ──
  // Cursor position drives a perspective rotateX/Y transform with a
  // tiny lag (lerp) so the card "weighs" something when it moves.
  // Layers inside the card (.depth-back / .depth-mid / .depth-front)
  // sit at different translateZ offsets so the parallax is real depth,
  // not just a single-plane tilt.
  const cardRef = useRef(null);
  const targetRef = useRef({ rx: 0, ry: 0 });
  const currentRef = useRef({ rx: 0, ry: 0 });

  useEffect(() => {
    const card = cardRef.current;
    if (!card) return;

    const onMove = (e) => {
      const rect = card.getBoundingClientRect();
      const dx = (e.clientX - (rect.left + rect.width  / 2)) / (rect.width  / 2);
      const dy = (e.clientY - (rect.top  + rect.height / 2)) / (rect.height / 2);
      // Max ±9° tilt — strong enough to feel, gentle enough not to flicker.
      targetRef.current.ry = Math.max(-1, Math.min(1, dx)) *  9;
      targetRef.current.rx = Math.max(-1, Math.min(1, dy)) * -9;
    };
    const onLeave = () => { targetRef.current.rx = 0; targetRef.current.ry = 0; };

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerleave', onLeave);

    let raf;
    const tick = () => {
      currentRef.current.rx += (targetRef.current.rx - currentRef.current.rx) * 0.08;
      currentRef.current.ry += (targetRef.current.ry - currentRef.current.ry) * 0.08;
      card.style.transform =
        `perspective(1200px) ` +
        `rotateX(${currentRef.current.rx.toFixed(2)}deg) ` +
        `rotateY(${currentRef.current.ry.toFixed(2)}deg)`;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerleave', onLeave);
      cancelAnimationFrame(raf);
    };
  }, []);

  const [slowWarn, setSlowWarn] = useState(false);
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setSlowWarn(false);
    setSubmitting(true);

    // Show progress hint after 5s — auth should be fast; if it's not the
    // server is likely cold-starting. Auto-abort at 30s via Promise.race.
    const slowTimer = setTimeout(() => setSlowWarn(true), 5000);
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Login timed out — please try again.')), 30000)
    );

    try {
      const result = await Promise.race([login(email, password), timeoutPromise]);
      if (result?.success) {
        navigate('/home');
      } else {
        setError(result?.error || 'Login failed. Please try again.');
      }
    } catch (err) {
      setError(err.message || 'Login timed out.');
    } finally {
      clearTimeout(slowTimer);
      setSlowWarn(false);
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      {/* Iridescent marble + voronoi cell WebGL background */}
      <AuthShaderBackground />

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
            <button className="profile-btn" onClick={() => navigate('/signup')}>
              <User size={14}/> Sign Up
            </button>
          </div>
        </div>
      </header>

      <main className="login-main">
        <div ref={cardRef} className="card login-card login-card-3d">
          <div className="depth-back"  aria-hidden="true"/>
          <h1 className="login-title depth-front">Login to AI Assistant</h1>

          <form onSubmit={handleLogin} className="login-form depth-mid">
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="Enter your email"
                className="input-field"
                required
                autoComplete="email"
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
                  autoComplete="current-password"
                />
                <button type="button" onClick={() => setShowPass(!showPass)} className="password-toggle">
                  {showPass ? <EyeOff size={16}/> : <Eye size={16}/>}
                </button>
              </div>
            </div>

            {error && (
              <div style={{
                background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
                borderRadius: '0.75rem', padding: '0.75rem 1rem',
                color: '#ef4444', fontSize: '0.875rem', textAlign: 'center',
              }}>
                {error}
              </div>
            )}

            <button type="submit" className="btn btn-primary w-full" disabled={submitting}>
              {submitting ? 'Logging in…' : 'Login'}
            </button>
            {slowWarn && (
              <p style={{ textAlign: 'center', fontSize: '0.78rem',
                          color: 'var(--text-tertiary)', marginTop: '0.4rem' }}>
                Server is taking longer than usual — auto-cancel in 25s.
              </p>
            )}

            <div className="forgot-password">
              <button type="button" onClick={() => navigate('/forgot-password')}>
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




