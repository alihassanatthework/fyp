import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Crown, Check, ArrowLeft, Sparkles } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';
import './UpgradePremium.css';

const PREMIUM_PERKS = [
  'Unlimited skin & scalp scans every day',
  'No daily scan limit',
  'Priority AI processing',
  'Full diagnosis history & reports',
  'Personalised makeup & fashion guidance',
];

export default function UpgradePremium() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const handleUpgrade = async () => {
    setBusy(true);
    setError('');
    try {
      const res = await apiClient.post(API_ENDPOINTS.PROFILE.UPGRADE);
      if (res?.data?.success) {
        setDone(true);
        setTimeout(() => navigate('/profile'), 1400);
      } else {
        setError('Upgrade failed. Please try again.');
      }
    } catch (e) {
      setError('Upgrade failed. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen page-bg">
      <Navbar title="Upgrade" />
      <main className="upgrade-main">
        <button className="upgrade-back" onClick={() => navigate(-1)}>
          <ArrowLeft size={15}/> Back
        </button>

        <div className="upgrade-card">
          <div className="upgrade-crown"><Crown size={28}/></div>
          <h1 className="upgrade-title">Upgrade to Premium</h1>
          <p className="upgrade-sub">Unlock unlimited scans and the full experience.</p>

          <div className="upgrade-price">
            <span className="upgrade-price-amount">Free</span>
            <span className="upgrade-price-note">for this FYP demo — no payment required</span>
          </div>

          <ul className="upgrade-perks">
            {PREMIUM_PERKS.map((p, i) => (
              <li key={i}><Check size={15}/> {p}</li>
            ))}
          </ul>

          {error && <div className="upgrade-error">{error}</div>}

          {done ? (
            <div className="upgrade-success">
              <Crown size={16}/> You're Premium now! Redirecting…
            </div>
          ) : (
            <button className="upgrade-cta" onClick={handleUpgrade} disabled={busy}>
              {busy
                ? 'Upgrading…'
                : <><Sparkles size={16}/> Upgrade Now</>}
            </button>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
