import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Sun, Moon, Eye, EyeOff, CheckSquare, Square, ChevronDown, ChevronUp } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import AuthShaderBackground from '../components/AuthShaderBackground';
import './SignUp.css';

// Maps each user-facing label to the boolean flag the backend stores on MedicalHistory.
const HEALTH_OPTIONS = [
  { label: 'Allergies',               field: 'has_allergies'        },
  { label: 'Diabetes',                field: 'is_diabetic'          },
  { label: 'Pregnancy',               field: 'is_pregnant'          },
  { label: 'Heart-related condition', field: 'has_cardio_issues'    },
  { label: 'Hypertension',            field: 'has_hypertension'     },
  { label: 'Asthma',                  field: 'has_asthma'           },
  { label: 'Skin Condition',          field: 'has_skin_conditions'  },
  { label: 'Scalp Condition',         field: 'has_scalp_conditions' },
  { label: 'None',                    field: '__none__'             }, // sentinel — clears the rest
];

export default function SignUp() {
  const [form, setForm] = useState({ firstName: '', lastName: '', email: '', password: '', confirmPassword: '' });
  const [accountType, setAccountType] = useState('free');
  const [healthConditions, setHealthConditions] = useState([]);  // array of label strings
  const [agreed, setAgreed] = useState(false);
  const [showConsent, setShowConsent] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [serverError, setServerError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { register } = useAuth();

  const toggleHealth = (label) => {
    setHealthConditions(prev => {
      if (label === 'None') return prev.includes('None') ? [] : ['None'];
      const next = prev.filter(h => h !== 'None');
      return next.includes(label) ? next.filter(h => h !== label) : [...next, label];
    });
  };

  // Build the medical_history object the backend expects.
  const buildMedicalHistory = () => {
    const out = {};
    HEALTH_OPTIONS.forEach(({ label, field }) => {
      if (field === '__none__') return;
      out[field] = healthConditions.includes(label);
    });
    return out;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');

    if (!form.firstName.trim()) {
      setServerError('First name is required.');
      return;
    }
    if (form.password !== form.confirmPassword) {
      setServerError('Passwords do not match.');
      return;
    }
    if (!agreed) {
      setServerError('Please agree to the terms to continue.');
      return;
    }

    setSubmitting(true);
    const result = await register({
      firstName: form.firstName.trim(),
      lastName:  form.lastName.trim(),
      email:     form.email.trim().toLowerCase(),
      password:  form.password,
      medical_history: buildMedicalHistory(),
    });
    setSubmitting(false);

    if (result.success) {
      navigate('/home');
    } else {
      setServerError(result.error || 'Registration failed. Please try again.');
    }
  };

  return (
    <div className="signup-page">
      <AuthShaderBackground />
      <div className="signup-container">
        <div className="signup-grid">
          <div className="card signup-form-panel p-8">
            <div className="signup-header">
              <div>
                <h1 className="signup-title">
                  Personalised Skin and Scalp Assistant
                </h1>
                <p className="signup-subtitle">One profile, synced across light and dark themes.</p>
              </div>
              <div className="theme-toggle">
                <button onClick={() => toggleTheme('light')} className={`theme-btn ${theme==='light' ? 'active' : ''}`}>
                  <Sun size={12}/> Light
                </button>
                <button onClick={() => toggleTheme('dark')} className={`theme-btn ${theme==='dark' ? 'active' : ''}`}>
                  <Moon size={12}/> Dark
                </button>
              </div>
            </div>

            <h2 className="text-2xl font-bold mb-2">Create your account</h2>
            <p className="signup-subtitle mb-5">Basic profile, health context, and AI analysis focus in one screen.</p>

            <form onSubmit={handleSubmit}>
              <div className="signup-fields-grid">
                <div style={{display:'flex',flexDirection:'column',gap:'1rem'}}>
                  <p className="section-label">Basic Information</p>
                  <div className="form-group">
                    <label>First Name</label>
                    <input type="text" placeholder="Jane" value={form.firstName} onChange={e => setForm({...form, firstName: e.target.value})} className="input-field" required autoComplete="given-name" />
                  </div>
                  <div className="form-group">
                    <label>Last Name</label>
                    <input type="text" placeholder="Doe" value={form.lastName} onChange={e => setForm({...form, lastName: e.target.value})} className="input-field" autoComplete="family-name" />
                  </div>
                  <div className="form-group">
                    <label>Email Address</label>
                    <input type="email" placeholder="jane@example.com" value={form.email} onChange={e => setForm({...form, email: e.target.value})} className="input-field" required autoComplete="email" />
                  </div>
                  <div className="form-group">
                    <label>Password</label>
                    <div className="password-wrapper">
                      <input type={showPass ? 'text' : 'password'} placeholder="••••••••" value={form.password} onChange={e => setForm({...form, password: e.target.value})} className="input-field" style={{paddingRight:'2.5rem'}} required autoComplete="new-password" />
                      <button type="button" onClick={() => setShowPass(!showPass)} className="password-toggle">
                        {showPass ? <EyeOff size={16}/> : <Eye size={16}/>}
                      </button>
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Confirm Password</label>
                    <input type="password" placeholder="••••••••" value={form.confirmPassword} onChange={e => setForm({...form, confirmPassword: e.target.value})} className="input-field" required autoComplete="new-password" />
                  </div>
                  <div>
                    <p className="section-label">Account Type</p>
                    <div className="account-type-btns">
                      {['free', 'premium'].map(t => (
                        <button key={t} type="button" onClick={() => setAccountType(t)} className={`account-type-btn ${accountType === t ? 'selected' : ''}`}>
                          {t === 'free' ? 'Free Account' : 'Premium Account'}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div style={{display:'flex',flexDirection:'column',gap:'1.25rem'}}>
                  <div>
                    <p className="section-label">Health Profile</p>
                    <p className="text-xs" style={{color:'var(--text-tertiary)',marginBottom:'0.75rem'}}>Treatment suggestions are adjusted according to your health condition.</p>
                    <div className="health-options">
                      {HEALTH_OPTIONS.map(({ label }) => (
                        <button key={label} type="button" onClick={() => toggleHealth(label)} className={`health-option-btn ${healthConditions.includes(label) ? 'selected' : ''}`}>
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <button type="button" onClick={() => setAgreed(!agreed)} className={`terms-checkbox ${agreed ? 'checked' : ''}`}>
                    <span className="terms-icon">
                      {agreed ? <CheckSquare size={18}/> : <Square size={18}/>}
                    </span>
                    <span className="terms-text">
                      I agree to the <Link to="/terms" onClick={(e) => e.stopPropagation()}>Terms and Conditions</Link> and consent to upload my face or scalp images for AI-based analysis.
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowConsent((s) => !s)}
                    className="consent-see-more"
                  >
                    {showConsent ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                    {showConsent ? 'Hide details' : 'See more'}
                  </button>

                  {showConsent && (
                    <div className="consent-details">
                      <ul>
                        <li><strong>No third-party sharing.</strong> Your images and personal data are never shared with advertisers, insurers, or external partners.</li>
                        <li><strong>LLM binary masks only.</strong> AI models receive de-identified binary masks derived from your image, not the raw photo, for inference.</li>
                        <li><strong>Exclusive processing.</strong> All analysis runs on our isolated infrastructure; data is processed exclusively for your personalised diagnosis.</li>
                        <li><strong>Right to withdraw.</strong> You may revoke consent and request deletion at any time from your profile settings.</li>
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              {serverError && (
                <div style={{
                  background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
                  borderRadius: '0.75rem', padding: '0.75rem 1rem',
                  color: '#ef4444', fontSize: '0.875rem', marginTop: '1rem',
                }}>
                  {serverError}
                </div>
              )}

              <div className="signup-footer">
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Creating account…' : 'Create Account'}
                </button>
                <p className="signup-footer-text">
                  Already have an account? <Link to="/">Login</Link>
                </p>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}