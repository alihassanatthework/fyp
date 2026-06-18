import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, Edit3, ShieldCheck, AlertCircle, Heart, Pill, CalendarClock, Lock, Crown, Sparkles } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import EditProfileModal from '../components/EditProfileModal';
import { profileService } from '../services/profileService';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';
import './UserProfile.css';

/**
 * ChangePasswordCard — P3 — wires the existing /auth/change-password/
 * backend endpoint to the UI (previously had no caller).
 */
function ChangePasswordCard() {
  const [oldPw, setOldPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confPw, setConfPw] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState({ kind: '', text: '' });

  const submit = async (e) => {
    e.preventDefault();
    setMsg({ kind: '', text: '' });
    if (newPw !== confPw) { setMsg({ kind: 'err', text: 'New passwords do not match.' }); return; }
    if (newPw.length < 8) { setMsg({ kind: 'err', text: 'Password must be at least 8 characters.' }); return; }
    setBusy(true);
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.CHANGE_PASSWORD, {
        old_password: oldPw,
        new_password: newPw,
        confirm_password: confPw,
      });
      setMsg({ kind: 'ok', text: 'Password updated.' });
      setOldPw(''); setNewPw(''); setConfPw('');
    } catch (err) {
      setMsg({ kind: 'err', text: err.message || 'Could not change password.' });
    } finally { setBusy(false); }
  };

  return (
    <section className="page-container w-full" style={{ padding: '0 1.75rem 2rem' }}>
      <div className="card profile-card" style={{ maxWidth: 540 }}>
        <h2 className="profile-card-title">
          <Lock size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }}/>
          Change password
        </h2>
        <p className="profile-card-sub">Use a strong password you don't reuse elsewhere.</p>
        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <input className="input-field" type="password" placeholder="Current password"
                 autoComplete="current-password" value={oldPw} onChange={(e)=>setOldPw(e.target.value)} required/>
          <input className="input-field" type="password" placeholder="New password (min 8)"
                 autoComplete="new-password" value={newPw} onChange={(e)=>setNewPw(e.target.value)} required minLength={8}/>
          <input className="input-field" type="password" placeholder="Confirm new password"
                 autoComplete="new-password" value={confPw} onChange={(e)=>setConfPw(e.target.value)} required/>
          {msg.text && (
            <div role="status" aria-live="polite" style={{
              fontSize: '0.82rem', padding: '0.6rem 0.8rem', borderRadius: '0.6rem',
              background: msg.kind === 'ok' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
              color:      msg.kind === 'ok' ? '#10b981' : '#ef4444',
            }}>{msg.text}</div>
          )}
          <button type="submit" className="btn btn-primary" disabled={busy} style={{ alignSelf: 'flex-start' }}>
            {busy ? 'Saving…' : 'Update password'}
          </button>
        </form>
      </div>
    </section>
  );
}

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
      const data = await profileService.getProfile();

      // Backend returns { user: { first_name, last_name, email, date_joined },
      //                   profile: {...}, medical_history: {...} }
      // Build full_name for the existing UI bindings.
      const fn = data?.user?.first_name || '';
      const ln = data?.user?.last_name  || '';
      const full = `${fn} ${ln}`.trim();
      // Format Member since as "Month DD, YYYY" — fall back to the
      // backend's pre-formatted member_since string if date_joined
      // isn't present (very old user records).
      const joined = data?.user?.date_joined
        ? new Date(data.user.date_joined).toLocaleDateString('en-US', {
            year: 'numeric', month: 'long', day: '2-digit',
          })
        : (data?.user?.member_since || '');

      setProfileData({
        user: {
          ...data?.user,
          full_name: full || data?.user?.email || '',
          member_since: joined,
        },
        profile: data?.profile || {},
        medical_history: data?.medical_history || {},
      });
    } catch (err) {
      setError('Could not load profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProfile(); }, []);

  const handleSave = async (formPayload) => {
    // EditProfileModal already sends the correct shape:
    //   { user: { first_name, last_name }, medical_history: {...} }
    // Strip the synthetic full_name (backend doesn't accept it).
    if (formPayload?.user?.full_name !== undefined) {
      const { full_name, ...rest } = formPayload.user;
      formPayload = { ...formPayload, user: rest };
    }
    await profileService.updateProfile(formPayload);
    await fetchProfile();
  };

  if (loading) return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex items-center justify-center">
      <p className="text-gray-400">Loading profile…</p>
    </div>
  );

  const u = profileData?.user || {};
  const profile = profileData?.profile || {};
  const med = profileData?.medical_history || {};
  const isPremium = profile?.account_type === 'premium';

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
                    {f.value || <span className="profile-field-empty">Not provided</span>}
                    {f.label === 'Full Name' && isPremium && (
                      <Crown size={15} className="profile-crown" aria-label="Premium" />
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Account tier + upgrade (free users only) */}
            {!isPremium && (
              <div className="profile-upgrade">
                <div>
                  <p className="profile-upgrade-title">Free Account</p>
                  <p className="profile-upgrade-sub">5 scans/day · upgrade for unlimited</p>
                </div>
                <button className="profile-upgrade-btn" onClick={() => navigate('/upgrade')}>
                  <Sparkles size={14}/> Upgrade to Premium
                </button>
              </div>
            )}
            {isPremium && (
              <div className="profile-premium-row">
                <Crown size={15}/> Premium · unlimited scans
              </div>
            )}
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
                  <p className="health-value">{med.current_medications || 'None'}</p>
                </div>
              </div>

              <div className="health-row">
                <div className="health-row-icon"><CalendarClock size={14}/></div>
                <div className="health-row-body">
                  <p className="health-row-label">Last updated</p>
                  <p className="health-value">
                    {profile.updated_at
                      ? new Date(profile.updated_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
                      : 'Not provided'}
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
      <ChangePasswordCard />


      <Footer />
    </div>
  );
}
