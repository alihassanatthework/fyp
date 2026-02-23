import { useNavigate } from 'react-router-dom';
import { Home, Edit3 } from 'lucide-react';
import Navbar from '../components/Navbar';

export default function UserProfile() {
  const navigate = useNavigate();

  const conditions = ['Diabetes', 'Heart-related condition', 'None'];
  const allergies = ['Fragrance', 'Parabens'];

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title="User Profile" subtitle="AI-Powered Skin, Scalp, Makeup & Fashion Assistant" />

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">
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
            <button className="btn-primary text-sm py-2">
              <Edit3 size={14}/> Edit Profile
            </button>
          </div>
        </div>

        {/* Two-panel grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

          {/* User Profile */}
          <div className="card p-6">
            <h2 className="font-bold text-gray-900 text-white mb-1">User Profile</h2>
            <p className="text-xs text-gray-400 text-gray-500 mb-6">Account details used for login and personalization.</p>

            <div className="space-y-4">
              {[
                { label: 'Username' },
                { label: 'Email' },
                { label: 'Member since' },
                { label: 'Account type', value: 'Free' },
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
            <p className="text-xs text-gray-400 text-gray-500 mb-6">Medical details used to keep treatments safe and personalized.</p>

            <div className="space-y-5">
              {/* Medical conditions */}
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

              {/* Allergies */}
              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-2">Allergies</label>
                <div className="flex flex-wrap gap-2">
                  {allergies.map((a, i) => (
                    <span key={a} className={`text-xs font-semibold px-3 py-1 rounded-full ${
                      i === 0
                        ? 'bg-amber-400 text-white'
                        : 'border border-gray-200 border-gray-700 text-gray-600 text-gray-300 bg-white bg-gray-800'
                    }`}>
                      {a}
                    </span>
                  ))}
                </div>
              </div>

              {/* Pregnancy status */}
              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-1.5">Pregnancy status</label>
                <div className="input-field bg-gray-50 bg-gray-800 text-gray-400 text-gray-500 cursor-default">—</div>
              </div>

              {/* Last updated */}
              <div>
                <label className="block text-sm font-medium text-gray-600 text-gray-400 mb-1.5">Last updated</label>
                <div className="input-field bg-gray-50 bg-gray-800 text-gray-400 text-gray-500 cursor-default">—</div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="py-4 px-6 border-t border-gray-100 border-gray-800 flex items-center justify-between text-xs text-gray-400">
        <span>AI Beauty Assistant · User Profile</span>
        <div className="flex gap-4">
          <button className="text-gray-600 transition">About Project</button>
          <button className="text-gray-600 transition">Contact / Support</button>
        </div>
      </footer>
    </div>
  );
}
