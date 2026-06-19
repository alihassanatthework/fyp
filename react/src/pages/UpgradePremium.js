import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Crown, Check, ArrowLeft, Sparkles, CreditCard, Lock } from 'lucide-react';
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

const PLANS = {
  monthly: { label: 'Monthly', price: 4.99, sub: 'billed monthly' },
  yearly:  { label: 'Yearly',  price: 39.99, sub: 'billed yearly · save 33%' },
};

// ── Card validation helpers ──────────────────────────────────────────
function luhnValid(num) {
  const digits = num.replace(/\s/g, '');
  if (!/^\d{13,19}$/.test(digits)) return false;
  let sum = 0, alt = false;
  for (let i = digits.length - 1; i >= 0; i--) {
    let d = parseInt(digits[i], 10);
    if (alt) { d *= 2; if (d > 9) d -= 9; }
    sum += d; alt = !alt;
  }
  return sum % 10 === 0;
}
function formatCardNumber(v) {
  return v.replace(/\D/g, '').slice(0, 19).replace(/(.{4})/g, '$1 ').trim();
}
function formatExpiry(v) {
  const d = v.replace(/\D/g, '').slice(0, 4);
  return d.length >= 3 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
}
function expiryValid(v) {
  const m = v.match(/^(\d{2})\/(\d{2})$/);
  if (!m) return false;
  const mm = parseInt(m[1], 10), yy = parseInt(m[2], 10) + 2000;
  if (mm < 1 || mm > 12) return false;
  const now = new Date();
  const exp = new Date(yy, mm); // first of next month
  return exp > now;
}

export default function UpgradePremium() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [plan, setPlan] = useState('monthly');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [receipt, setReceipt] = useState(null);
  const [error, setError] = useState('');
  const [card, setCard] = useState({ name: '', number: '', expiry: '', cvv: '' });
  const [showDemo, setShowDemo] = useState(false);

  const set = (k, v) => setCard((c) => ({ ...c, [k]: v }));

  const onGatewayClick = async () => {
    const went = await handleGatewayPay();
    if (!went) setShowDemo(true);   // no Safepay keys yet → reveal demo form
  };

  // When Safepay redirects back to /upgrade?status=success&tracker=...&sig=...,
  // confirm the payment server-side and show the receipt.
  useEffect(() => {
    const statusParam = searchParams.get('status');
    const tracker = searchParams.get('tracker') || searchParams.get('beacon');
    if (statusParam === 'cancelled') {
      setError('Payment was cancelled.');
      return;
    }
    if (statusParam === 'success' && tracker) {
      (async () => {
        setBusy(true);
        try {
          const res = await apiClient.post(API_ENDPOINTS.PAYMENTS.VERIFY, { tracker });
          if (res?.data?.verified) {
            setReceipt({ plan_label: 'Premium', amount: '—', currency: 'PKR',
              card_last4: '', transaction_id: tracker });
            setDone(true);
            setTimeout(() => navigate('/profile'), 2600);
          } else {
            setError('We could not verify your payment. Contact support if you were charged.');
          }
        } catch {
          setError('Payment verification failed.');
        } finally {
          setBusy(false);
        }
      })();
    }
  }, [searchParams, navigate]);

  // Try the real Safepay gateway first. If the backend reports it's not
  // configured (no keys yet), fall back to the built-in demo card form.
  const handleGatewayPay = async () => {
    setError('');
    setBusy(true);
    try {
      const res = await apiClient.post(API_ENDPOINTS.PAYMENTS.INIT, { plan });
      if (res?.data?.configured && res.data.checkout_url) {
        window.location.href = res.data.checkout_url;   // → Safepay hosted checkout
        return true;
      }
      return false;   // not configured → caller shows demo form
    } catch {
      return false;
    } finally {
      setBusy(false);
    }
  };

  const validate = () => {
    if (!card.name.trim()) return 'Enter the name on the card.';
    if (!luhnValid(card.number)) return 'Enter a valid card number.';
    if (!expiryValid(card.expiry)) return 'Enter a valid future expiry (MM/YY).';
    if (!/^\d{3,4}$/.test(card.cvv)) return 'Enter a valid CVV.';
    return '';
  };

  const handlePay = async (e) => {
    e.preventDefault();
    const v = validate();
    if (v) { setError(v); return; }
    setError('');
    setBusy(true);
    try {
      // Simulate gateway processing latency.
      await new Promise((r) => setTimeout(r, 1200));
      const last4 = card.number.replace(/\s/g, '').slice(-4);
      const res = await apiClient.post(API_ENDPOINTS.PROFILE.UPGRADE, {
        plan,
        card_last4: last4,
      });
      if (res?.data?.success) {
        setReceipt(res.data);
        setDone(true);
        setTimeout(() => navigate('/profile'), 2600);
      } else {
        setError('Payment failed. Please try again.');
      }
    } catch (err) {
      setError(err?.response?.data?.error || 'Payment failed. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const amount = PLANS[plan].price;

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

          {done && receipt ? (
            <div className="upgrade-receipt">
              <div className="upgrade-success">
                <Crown size={18}/> Payment successful — you're Premium!
              </div>
              <ul className="upgrade-receipt-rows">
                <li><span>Plan</span><span>{receipt.plan_label}</span></li>
                <li><span>Amount</span><span>${Number(receipt.amount).toFixed(2)} {receipt.currency}</span></li>
                <li><span>Card</span><span>•••• {receipt.card_last4 || '----'}</span></li>
                <li><span>Transaction</span><span>{receipt.transaction_id}</span></li>
              </ul>
              <p className="upgrade-redirect">Redirecting to your profile…</p>
            </div>
          ) : (
            <>
              {/* Plan selector */}
              <div className="upgrade-plans">
                {Object.entries(PLANS).map(([key, p]) => (
                  <button
                    key={key}
                    type="button"
                    className={`upgrade-plan ${plan === key ? 'active' : ''}`}
                    onClick={() => setPlan(key)}
                  >
                    <span className="upgrade-plan-label">{p.label}</span>
                    <span className="upgrade-plan-price">${p.price.toFixed(2)}</span>
                    <span className="upgrade-plan-sub">{p.sub}</span>
                  </button>
                ))}
              </div>

              <ul className="upgrade-perks">
                {PREMIUM_PERKS.map((p, i) => (
                  <li key={i}><Check size={15}/> {p}</li>
                ))}
              </ul>

              {/* Primary: real Safepay gateway (cards + Easypaisa + JazzCash) */}
              {!showDemo && (
                <>
                  <button className="upgrade-cta" type="button" onClick={onGatewayClick} disabled={busy}>
                    {busy
                      ? 'Starting secure checkout…'
                      : <><Sparkles size={16}/> Pay ${amount.toFixed(2)} — Card · Easypaisa · JazzCash</>}
                  </button>
                  {error && <div className="upgrade-error" style={{ marginTop: 10 }}>{error}</div>}
                  <p className="upgrade-demo-note">
                    Secure checkout via Safepay. Pay with Visa, Mastercard, PayPak, Easypaisa, or JazzCash.
                  </p>
                </>
              )}

              {/* Fallback demo card form (shown when the gateway isn't configured) */}
              {showDemo && (
              <form className="upgrade-pay-form" onSubmit={handlePay}>
                <div className="upgrade-pay-header">
                  <CreditCard size={16}/> <span>Card details</span>
                  <span className="upgrade-secure"><Lock size={12}/> Secure</span>
                </div>

                <label className="upgrade-field">
                  <span>Name on card</span>
                  <input
                    type="text" value={card.name} placeholder="Ali Hassan"
                    onChange={(e) => set('name', e.target.value)}
                  />
                </label>

                <label className="upgrade-field">
                  <span>Card number</span>
                  <input
                    type="text" inputMode="numeric" value={card.number}
                    placeholder="4242 4242 4242 4242"
                    onChange={(e) => set('number', formatCardNumber(e.target.value))}
                  />
                </label>

                <div className="upgrade-field-row">
                  <label className="upgrade-field">
                    <span>Expiry</span>
                    <input
                      type="text" inputMode="numeric" value={card.expiry}
                      placeholder="MM/YY"
                      onChange={(e) => set('expiry', formatExpiry(e.target.value))}
                    />
                  </label>
                  <label className="upgrade-field">
                    <span>CVV</span>
                    <input
                      type="text" inputMode="numeric" value={card.cvv}
                      placeholder="123" maxLength={4}
                      onChange={(e) => set('cvv', e.target.value.replace(/\D/g, ''))}
                    />
                  </label>
                </div>

                {error && <div className="upgrade-error">{error}</div>}

                <button className="upgrade-cta" type="submit" disabled={busy}>
                  {busy
                    ? 'Processing payment…'
                    : <><Sparkles size={16}/> Pay ${amount.toFixed(2)} &amp; Upgrade</>}
                </button>
                <p className="upgrade-demo-note">
                  Demo checkout — use any test card (e.g. 4242 4242 4242 4242). Your full
                  card number is never sent to or stored on our servers.
                </p>
              </form>
              )}
            </>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
