import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, Edit3 } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import EditProfileModal from '../components/EditProfileModal';
import { useProfile } from '../hooks/useProfile';

export default function UserProfile() {
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);
  const [localProfile, setLocalProfile] = useState(null);

  const { profile, loading, error, getProfile, updateProfile } = useProfile();

  // Load from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('userProfile');
    if (saved) {
      setLocalProfile(JSON.parse(saved));
    }
    getProfile(); // still try the API
  }, []);

  // Priority: API profile > localStorage profile
  const activeProfile = profile || localProfile;

  const handleSave = async (formData) => {
    // Always save to localStorage immediately
    const updated = { ...(activeProfile || {}), ...formData, lastUpdated: new Date().toLocaleDateString() };
    localStorage.setItem('userProfile', JSON.stringify(updated));
    setLocalProfile(updated);

    // Also try to save to backend
    await updateProfile(formData);
  };

  const conditions = activeProfile?.conditions?.length ? activeProfile.conditions : ['—'];
  const allergies = activeProfile?.allergies?.length ? activeProfile.allergies : [];

  if (loading && !localProfile) return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex items-center justify-center">
      <p className="text-gray-400">Loading profile...</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title="User Profile" subtitle="AI-Powered Skin, Scalp, Makeup & Fashion Assistant" />

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">

        {/* Offline banner — only show if no local data either */}
        {error && !localProfile && (
          <div className="mb-5 rounded-xl bg-amber-50 bg-amber-900/20 border border-amber-200 border-amber-700 px-4 py-3 text-sm text-amber-700 text-amber-400 text-center">
            ⚠️ Backend unavailable and no local profile found. Please sign up or check your connection.
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

          {/* User Profile */}
          <div className="card p-6">
            <h2 className="font-bold text-gray-900 text-white mb-1">User Profile</h2>
            <p className="text-xs text-gray-400 text-gray-500 mb-6">
              Account details used for login and personalization.
            </p>
            <div className="space-y-4">
              {[
                { label: 'Username', value: activeProfile?.name },
                { label: 'Email', value: activeProfile?.email },
                { label: 'Member since', value: activeProfile?.memberSince },
                { label: 'Account type', value: activeProfile?.accountType || 'Free' },
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

          {/* Health Profile */}
          <div className="card p-6">
            <h2 className="font-bold text-gray-900 text-white mb-1">Health Profile</h2>
            <p className="text-xs text-gray-400 text-gray-500 mb-6">
              Medical details used to keep treatments safe and personalized.
            </p>
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-2">Medical conditions</label>
                <div className="flex flex-wrap gap-2">
                  {conditions.map(c => (
                    <span key={c} className="border border-gray-200 border-gray-700 text-gray-600 text-gray-300 text-xs font-medium px-3 py-1 rounded-full bg-white bg-gray-800">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-2">Allergies</label>
                <div className="flex flex-wrap gap-2">
                  {allergies.length > 0 ? allergies.map((a, i) => (
                    <span key={a} className={`text-xs font-semibold px-3 py-1 rounded-full ${
                      i === 0 ? 'bg-amber-400 text-white' : 'border border-gray-200 border-gray-700 text-gray-600 text-gray-300 bg-white bg-gray-800'
                    }`}>{a}</span>
                  )) : <span className="text-gray-400 text-gray-500 text-xs">—</span>}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-1.5">Pregnancy status</label>
                <div className="input-field bg-gray-50 bg-gray-800 text-gray-400 text-gray-500 cursor-default">
                  {activeProfile?.pregnancyStatus || '—'}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-1.5">Last updated</label>
                <div className="input-field bg-gray-50 bg-gray-800 text-gray-400 text-gray-500 cursor-default">
                  {activeProfile?.lastUpdated || '—'}
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
        profile={activeProfile}
      />

      <Footer />
    </div>
  );
}