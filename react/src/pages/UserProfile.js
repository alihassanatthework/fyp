import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, Edit3 } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import EditProfileModal from '../components/EditProfileModal';
import apiClient from '../api/client';

// Convert medical_history boolean fields → readable condition names
function getConditionsFromMedicalHistory(med) {
  if (!med) return [];
  const map = [
    { field: 'has_allergies',      label: 'Allergies' },
    { field: 'is_diabetic',        label: 'Diabetes' },
    { field: 'is_pregnant',        label: 'Pregnancy' },
    { field: 'has_cardio_issues',  label: 'Heart Condition' },
    { field: 'has_hypertension',   label: 'Hypertension' },
    { field: 'has_asthma',         label: 'Asthma' },
    { field: 'has_skin_conditions',label: 'Skin Condition' },
    { field: 'has_scalp_conditions',label: 'Scalp Condition' },
  ];
  return map.filter(m => med[m.field]).map(m => m.label);
}

export default function UserProfile() {
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);

  // Full API response: { user, profile, medical_history }
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchProfile = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await apiClient.get('/profile/');
      setProfileData(res.data);
    } catch (err) {
      setError('Could not load profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProfile(); }, []);

  // After saving from modal, refresh profile from API
  const handleSave = async (formPayload) => {
    await apiClient.patch('/profile/', formPayload);
    await fetchProfile();
  };

  if (loading) return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex items-center justify-center">
      <p className="text-gray-400">Loading profile…</p>
    </div>
  );

  const user = profileData?.user || {};
  const profile = profileData?.profile || {};
  const med = profileData?.medical_history || {};

  const conditions = getConditionsFromMedicalHistory(med);
  const hasAllergies = med.has_allergies;
  const knownAllergens = med.known_allergens || '';

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title="User Profile" subtitle="AI-Powered Skin & Scalp Assistant" />

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">

        {error && (
          <div className="mb-5 rounded-xl bg-amber-50 bg-amber-900/20 border border-amber-200 border-amber-700 px-4 py-3 text-sm text-amber-700 text-amber-400 text-center">
            ⚠️ {error}
          </div>
        )}

        {/* Header */}
        <div className="flex items-start justify-between mb-7">
          <div>
            <h1 className="text-xl font-bold text-gray-900 text-white">User Profile</h1>
            <p className="text-sm text-gray-400 text-gray-500 mt-0.5">
              View and manage your basic details and health information for safe, personalized recommendations.
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => navigate('/home')} className="btn-secondary text-sm py-2">
              <Home size={14}/> Back to Home
            </button>
            <button onClick={() => setShowModal(true)} className="btn-primary text-sm py-2">
              <Edit3 size={14}/> Edit Profile
            </button>
          </div>
        </div>

        {/* Two-panel grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

          {/* Account panel */}
          <div className="card p-6">
            <h2 className="font-bold text-gray-900 text-white mb-1">User Profile</h2>
            <p className="text-xs text-gray-400 text-gray-500 mb-6">
              Account details used for login and personalization.
            </p>
            <div className="space-y-4">
              {[
                { label: 'Full Name',    value: user.full_name },
                { label: 'Email',        value: user.email },
                { label: 'Member since', value: user.member_since },
                { label: 'Skin type',    value: profile.skin_type
                    ? profile.skin_type.charAt(0).toUpperCase() + profile.skin_type.slice(1)
                    : null },
                { label: 'Hair type',    value: profile.hair_type
                    ? profile.hair_type.charAt(0).toUpperCase() + profile.hair_type.slice(1)
                    : null },
              ].map((f, i) => (
                <div key={i}>
                  <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-1.5">{f.label}</label>
                  <div className="input-field bg-gray-50 bg-gray-800 text-gray-600 text-gray-300 cursor-default">
                    {f.value || <span className="text-gray-400 text-gray-500">—</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Health panel */}
          <div className="card p-6">
            <h2 className="font-bold text-gray-900 text-white mb-1">Health Profile</h2>
            <p className="text-xs text-gray-400 text-gray-500 mb-6">
              Medical details used to keep treatments safe and personalized.
            </p>
            <div className="space-y-5">

              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-2">Medical conditions</label>
                <div className="flex flex-wrap gap-2">
                  {conditions.length > 0 ? conditions.map(c => (
                    <span key={c} className="border border-gray-200 border-gray-700 text-gray-600 text-gray-300 text-xs font-medium px-3 py-1 rounded-full bg-white bg-gray-800">
                      {c}
                    </span>
                  )) : <span className="text-gray-400 text-gray-500 text-xs">None reported</span>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-2">Allergies</label>
                {hasAllergies ? (
                  <div className="flex flex-wrap gap-2">
                    <span className="text-xs font-semibold px-3 py-1 rounded-full bg-amber-400 text-white">
                      Allergies
                    </span>
                    {knownAllergens && (
                      <span className="text-xs px-3 py-1 rounded-full border border-gray-200 border-gray-700 text-gray-600 text-gray-300 bg-white bg-gray-800">
                        {knownAllergens}
                      </span>
                    )}
                  </div>
                ) : (
                  <span className="text-gray-400 text-gray-500 text-xs">None reported</span>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-1.5">Pregnancy status</label>
                <div className="input-field bg-gray-50 bg-gray-800 text-gray-400 text-gray-500 cursor-default">
                  {med.is_pregnant ? 'Currently pregnant' : 'Not pregnant'}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-1.5">Current medications</label>
                <div className="input-field bg-gray-50 bg-gray-800 text-gray-400 text-gray-500 cursor-default">
                  {med.current_medications || '—'}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-1.5">Last updated</label>
                <div className="input-field bg-gray-50 bg-gray-800 text-gray-400 text-gray-500 cursor-default">
                  {profile.updated_at
                    ? new Date(profile.updated_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
                    : '—'}
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
