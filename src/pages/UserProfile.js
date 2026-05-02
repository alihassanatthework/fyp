import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, Edit3, ShieldCheck, AlertCircle, Heart, Pill, CalendarClock } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import EditProfileModal from '../components/EditProfileModal';
// import apiClient from '../api/client'; // ── API disabled for local dev ──
import './UserProfile.css';

function getConditionsFromMedicalHistory(med) {
  if (!med) return [];
  const map = [
    { field: 'has_allergies',       label: 'Allergies' },
    { field: 'is_diabetic',         label: 'Diabetes' },
    { field: 'is_pregnant',         label: 'Pregnancy' },
    { field: 'has_cardio_issues',   label: 'Heart Condition' },
    { field: 'has_hypertension',    label: 'Hypertension' },
    { field: 'has_asthma',          label: 'Asthma' },
    { field: 'has_skin_conditions', label: 'Skin Condition' },
    { field: 'has_scalp_conditions',label: 'Scalp Condition' },
  ];
  return map.filter(m => med[m.field]).map(m => m.label);
}

export default function UserProfile() {
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchProfile = async () => {
    try {
      setLoading(true);
      setError('');

      // ── MOCK profile (no backend) ────────────────────────────────────────
      const stored = localStorage.getItem('user');
      const u = stored ? JSON.parse(stored) : { full_name: 'Test User', email: 'test@example.com' };
      setProfileData({
        user: {
          full_name: u.full_name || 'Test User',
          email: u.email || 'test@example.com',
          member_since: new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long' }),
        },
        profile: { updated_at: new Date().toISOString() },
        medical_history: {
          has_allergies: false,
          is_diabetic: false,
          is_pregnant: false,
          has_cardio_issues: false,
          has_hypertension: false,
          has_asthma: false,
          has_skin_conditions: false,
          has_scalp_conditions: false,
          known_allergens: '',
          current_medications: '',
        },
      });

      // ── REAL API call (commented out) ──────────────────────────────────────
      // const res = await apiClient.get('/profile/');
      // setProfileData(res.data);
    } catch (err) {
      setError('Could not load profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProfile(); }, []);

  const handleSave = async (formPayload) => {
    // ── MOCK save (no backend) ─────────────────────────────────────────────
    setProfileData((prev) => ({ ...prev, ...formPayload }));

    // ── REAL API call (commented out) ──────────────────────────────────────
    // await apiClient.patch('/profile/', formPayload);
    // await fetchProfile();
  };

  if (loading) return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex items-center justify-center">
      <p className="text-gray-400">Loading profile…</p>
    </div>
  );

  const u = profileData?.user || {};
  const profile = profileData?.profile || {};
  const med = profileData?.medical_history || {};

  const conditions = getConditionsFromMedicalHistory(med);
  const hasAllergies = med.has_allergies;
  const knownAllergens = med.known_allergens || '';

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title="User Profile" />

      <main className="page-container flex-1 w-full py-8">

        {error && (
          <div className="mb-5 rounded-xl bg-amber-50 bg-amber-900/20 border border-amber-200 border-amber-700 px-4 py-3 text-sm text-amber-700 text-amber-400 text-center">
            {error}
          </div>
        )}

        {/* Header */}
        <div className="profile-page-header">
          <div>
            <h1 className="text-xl font-bold text-gray-900 text-white">User Profile</h1>
            <p className="text-sm text-gray-400 text-gray-500 mt-0.5">
              View and manage your basic details and health information for safe, personalized recommendations.
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => navigate('/home')} className="btn-secondary text-sm py-2">
              <Home size={14}/> Home
            </button>
            <button onClick={() => setShowModal(true)} className="btn-primary text-sm py-2">
              <Edit3 size={14}/> Edit Profile
            </button>
          </div>
        </div>

        <div className="profile-grid">

          {/* Account panel */}
          <div className="card profile-card">
            <h2 className="profile-card-title">Account Details</h2>
            <p className="profile-card-sub">Used for login and personalization.</p>
            <div className="profile-fields">
              {[
                { label: 'Full Name',    value: u.full_name },
                { label: 'Email',        value: u.email },
                { label: 'Member since', value: u.member_since },
              ].map((f, i) => (
                <div key={i} className="profile-field">
                  <label className="profile-field-label">{f.label}</label>
                  <div className="profile-field-value">
                    {f.value || <span className="profile-field-empty">—</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Health panel */}
          <div className="card profile-card">
            <div className="health-header">
              <div className="health-icon-box">
                <ShieldCheck size={18}/>
              </div>
              <div>
                <h2 className="profile-card-title" style={{ marginBottom: 2 }}>Health Profile</h2>
                <p className="profile-card-sub" style={{ marginBottom: 0 }}>Medical context used to keep treatments safe.</p>
              </div>
            </div>

            <div className="health-grid">
              <div className="health-row">
                <div className="health-row-icon"><Heart size={14}/></div>
                <div className="health-row-body">
                  <p className="health-row-label">Medical conditions</p>
                  <div className="health-pills">
                    {conditions.length > 0
                      ? conditions.map(c => <span key={c} className="health-pill">{c}</span>)
                      : <span className="health-empty">None reported</span>}
                  </div>
                </div>
              </div>

              <div className="health-row">
                <div className="health-row-icon"><AlertCircle size={14}/></div>
                <div className="health-row-body">
                  <p className="health-row-label">Allergies</p>
                  {hasAllergies ? (
                    <div className="health-pills">
                      <span className="health-pill health-pill-warn">Allergies</span>
                      {knownAllergens && <span className="health-pill">{knownAllergens}</span>}
                    </div>
                  ) : (
                    <span className="health-empty">None reported</span>
                  )}
                </div>
              </div>

              <div className="health-row">
                <div className="health-row-icon"><Pill size={14}/></div>
                <div className="health-row-body">
                  <p className="health-row-label">Current medications</p>
                  <p className="health-value">{med.current_medications || '—'}</p>
                </div>
              </div>

              <div className="health-row">
                <div className="health-row-icon"><CalendarClock size={14}/></div>
                <div className="health-row-body">
                  <p className="health-row-label">Last updated</p>
                  <p className="health-value">
                    {profile.updated_at
                      ? new Date(profile.updated_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
                      : '—'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <EditProfileModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSave={handleSave}
        profileData={profileData}
      />

      <Footer />
    </div>
  );
}
