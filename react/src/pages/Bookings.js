// src/pages/Bookings.js — Provider directory + booking creation page
import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import {
  Calendar, Clock, MapPin, Phone, ChevronLeft,
  Stethoscope, Scissors, CheckCircle2, Loader2, X, Filter,
  Navigation, ExternalLink, Map as MapIcon,
} from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import NearbyProvidersMap from '../components/NearbyProvidersMap';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';
import './Bookings.css';

const PROVIDER_TYPES = [
  { id: 'all',           label: 'All',           icon: Filter      },
  { id: 'dermatologist', label: 'Dermatologist', icon: Stethoscope },
  { id: 'salon',         label: 'Salon',         icon: Scissors    },
];

export default function Bookings() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const conditionFromDiagnosis = location.state?.condition || '';

  // ?type=dermatologist or ?type=salon presets the filter when arriving from
  // a specific feature (Diagnosis → dermatologist, Makeup/Fashion → salon).
  // Accepts state-based or query-string-based source.
  const presetType = (searchParams.get('type') || location.state?.type || 'all').toLowerCase();
  const initialType = ['dermatologist', 'salon'].includes(presetType) ? presetType : 'all';
  const sourceFeature = location.state?.source || (initialType === 'dermatologist' ? 'diagnosis' : initialType === 'salon' ? 'makeup' : null);

  const [providers,   setProviders]   = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState('');
  const [typeFilter,  setTypeFilter]  = useState(initialType);
  const [cityFilter,  setCityFilter]  = useState('');

  const [selectedProvider, setSelectedProvider] = useState(null);
  const [date,        setDate]        = useState('');
  const [time,        setTime]        = useState('');
  const [notes,       setNotes]       = useState(conditionFromDiagnosis
                                          ? `Diagnosed with: ${conditionFromDiagnosis}.`
                                          : '');
  const [submitting,  setSubmitting]  = useState(false);
  const [success,     setSuccess]     = useState(null);

  // ── User geolocation (for "Find Nearby") ────────────────────────
  const [userLoc,     setUserLoc]     = useState(null); // { lat, lng }
  const [locating,    setLocating]    = useState(false);
  const [locError,    setLocError]    = useState('');
  const [locErrorCode,setLocErrorCode]= useState(null);
  const [showHelp,    setShowHelp]    = useState(false);

  const handleFindNearby = () => {
    if (!navigator.geolocation) {
      setLocError('Geolocation not supported in this browser.');
      return;
    }
    setLocating(true);
    setLocError('');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        setUserLoc({ lat: latitude, lng: longitude });
        try {
          const { data } = await apiClient.get(API_ENDPOINTS.PROVIDERS.NEARBY, {
            params: { lat: latitude, lng: longitude, radius: 50 },
          });
          const list = Array.isArray(data) ? data : (data?.results || []);
          if (list.length) setProviders(list);
        } catch {
          // fall back to existing list — already filtered/loaded
        } finally {
          setLocating(false);
        }
      },
      (err) => {
        setLocating(false);
        setLocErrorCode(err.code);
        // Code 1 = PERMISSION_DENIED, 2 = POSITION_UNAVAILABLE, 3 = TIMEOUT
        let msg = err.message || 'Could not get your location.';
        if (err.code === 1)      msg = 'Location permission was denied.';
        else if (err.code === 2) msg = 'Your operating system did not report a location.';
        else if (err.code === 3) msg = 'Location request timed out.';
        setLocError(msg);
      },
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 60000 }
    );
  };

  // "Open in Google Maps" — works without any permissions or API key.
  // Searches Google Maps in a new tab using:
  //   - the type filter (dermatologist / salon)
  //   - the city filter if present, otherwise "near me"
  const gmapsQuery = () => {
    if (typeFilter === 'dermatologist') return 'dermatologist';
    if (typeFilter === 'salon')         return 'beauty salon';
    return 'dermatologist OR beauty salon';
  };
  const gmapsLabel = () => {
    if (typeFilter === 'dermatologist') return 'Dermatologists on Maps';
    if (typeFilter === 'salon')         return 'Salons on Maps';
    return 'All on Maps';
  };
  const openInGoogleMaps = () => {
    const where = cityFilter ? ` near ${cityFilter}` : ' near me';
    const url   = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(gmapsQuery() + where)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // ── Map helpers (Google Maps Embed — no API key required) ──────
  const mapEmbedFor = (p) => {
    if (p.latitude && p.longitude) {
      return `https://maps.google.com/maps?q=${p.latitude},${p.longitude}&z=15&output=embed`;
    }
    const q = encodeURIComponent(`${p.name}, ${p.city || ''}`);
    return `https://maps.google.com/maps?q=${q}&z=14&output=embed`;
  };
  const directionsLink = (p) => {
    if (p.latitude && p.longitude) {
      return `https://www.google.com/maps/dir/?api=1&destination=${p.latitude},${p.longitude}`;
    }
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${p.name}, ${p.city || ''}`)}`;
  };

  // Haversine distance in km — only computed when we know userLoc
  const distanceKm = (p) => {
    if (!userLoc || !p.latitude || !p.longitude) return null;
    const R = 6371;
    const dLat = (p.latitude - userLoc.lat) * Math.PI / 180;
    const dLng = (p.longitude - userLoc.lng) * Math.PI / 180;
    const a = Math.sin(dLat/2)**2 +
              Math.cos(userLoc.lat * Math.PI / 180) *
              Math.cos(p.latitude * Math.PI / 180) *
              Math.sin(dLng/2)**2;
    return Math.round(2 * R * Math.asin(Math.sqrt(a)) * 10) / 10;
  };

  // ── Load providers on mount ──────────────────────────────────────
  useEffect(() => {
    setLoading(true);
    apiClient.get(API_ENDPOINTS.PROVIDERS.LIST)
      .then((res) => {
        // backend may return either a plain array or { results: [...] }
        const data = Array.isArray(res.data) ? res.data : (res.data?.results || []);
        setProviders(data);
        setError('');
      })
      .catch((e) => {
        setError(e.message || 'Failed to load providers.');
        setProviders([]);
      })
      .finally(() => setLoading(false));
  }, []);

  // Helper: backend serializer returns `provider_type`; older mocks used `type`.
  const getType = (p) => p.provider_type || p.type || '';

  // Helper: human-readable working hours from opening/closing times + days.
  const getHoursLabel = (p) => {
    if (p.working_hours) return p.working_hours;
    if (p.opening_time && p.closing_time) {
      const days = p.working_days || 'Mon-Sat';
      return `${days} ${p.opening_time.slice(0,5)} – ${p.closing_time.slice(0,5)}`;
    }
    return null;
  };

  // ── Derived filtered list ────────────────────────────────────────
  const filtered = useMemo(() => {
    return providers.filter((p) => {
      if (typeFilter !== 'all' && getType(p) !== typeFilter) return false;
      if (cityFilter && !String(p.city || '').toLowerCase().includes(cityFilter.toLowerCase())) return false;
      if (p.is_active === false) return false;
      return true;
    });
  }, [providers, typeFilter, cityFilter]);

  // ── Submit booking ───────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedProvider || !date || !time) {
      setError('Please pick a date and time.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      // Bookings can come from two sources:
      //  • Internal provider directory → provider id is a Django pk (number).
      //  • Google Places result        → provider id is a Google place_id
      //    (string starting with "ChIJ…"). The backend then creates a Provider
      //    row from the google_place payload we pass alongside.
      const isGooglePlace = !!selectedProvider._google_place_id
        || (typeof selectedProvider.id === 'string' && Number.isNaN(Number(selectedProvider.id)));

      const body = {
        date,
        time,
        notes,
      };

      if (isGooglePlace) {
        body.google_place = {
          place_id:     selectedProvider._google_place_id || selectedProvider.id,
          name:         selectedProvider.name,
          vicinity:     selectedProvider.address || '',
          lat:          selectedProvider.latitude,
          lng:          selectedProvider.longitude,
          phone:        selectedProvider.phone || '',
        };
        body.provider_type = selectedProvider.provider_type || 'dermatologist';
      } else {
        body.provider = selectedProvider.id;
      }

      const { data } = await apiClient.post(API_ENDPOINTS.BOOKINGS.CREATE, body);
      setSuccess(data);
    } catch (e) {
      setError(e.message || 'Failed to create booking.');
    } finally {
      setSubmitting(false);
    }
  };

  // ── Success screen ───────────────────────────────────────────────
  if (success) {
    return (
      <div className="bookings-page">
        <Navbar title="Booking Confirmed" />
        <main className="bookings-main">
          <div className="card booking-success-card">
            <CheckCircle2 size={56} color="#22c55e" />
            <h1 className="booking-success-title">Booking Confirmed</h1>
            <p className="booking-success-subtitle">
              A confirmation email has been sent to your inbox.
            </p>
            <div className="booking-success-summary">
              <div><strong>Provider:</strong> {selectedProvider?.name}</div>
              <div><strong>Date:</strong> {date}</div>
              <div><strong>Time:</strong> {time}</div>
            </div>
            <div className="booking-success-actions">
              <button className="btn btn-primary" onClick={() => navigate('/home')}>
                Back to Home
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setSuccess(null);
                  setSelectedProvider(null);
                  setDate(''); setTime(''); setNotes('');
                }}
              >
                Book Another
              </button>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  // ── Booking form (provider selected) ─────────────────────────────
  if (selectedProvider) {
    return (
      <div className="bookings-page">
        <Navbar title="Book Appointment" />
        <main className="bookings-main">
          <button
            className="bookings-back-btn"
            onClick={() => { setSelectedProvider(null); setError(''); }}
          >
            <ChevronLeft size={16} /> Back to providers
          </button>

          <div className="card booking-form-card">
            <div className="booking-provider-header">
              <div className={`provider-icon ${getType(selectedProvider)}`}>
                {getType(selectedProvider) === 'salon'
                  ? <Scissors size={20}/>
                  : <Stethoscope size={20}/>}
              </div>
              <div>
                <h2 className="booking-provider-name">{selectedProvider.name}</h2>
                <p className="booking-provider-meta">
                  <MapPin size={12}/> {selectedProvider.address || selectedProvider.city || 'Unknown city'}
                  {selectedProvider.phone && (<> &middot; <Phone size={12}/> {selectedProvider.phone}</>)}
                </p>
              </div>
            </div>

            {/* ── Google Maps embed ────────────────────────────── */}
            <div className="booking-map-wrap">
              <iframe
                title={`Map of ${selectedProvider.name}`}
                src={mapEmbedFor(selectedProvider)}
                width="100%"
                height="240"
                style={{ border: 0, borderRadius: '0.75rem' }}
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
              />
              <a
                href={directionsLink(selectedProvider)}
                target="_blank"
                rel="noreferrer noopener"
                className="booking-directions-btn"
              >
                <Navigation size={14}/> Get Directions <ExternalLink size={12}/>
              </a>
            </div>

            <form onSubmit={handleSubmit} className="booking-form">
              <div className="form-row">
                <div className="form-group">
                  <label><Calendar size={14}/> Date</label>
                  <input
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    min={new Date().toISOString().slice(0, 10)}
                    className="input-field"
                    required
                  />
                </div>
                <div className="form-group">
                  <label><Clock size={14}/> Time</label>
                  <input
                    type="time"
                    value={time}
                    onChange={(e) => setTime(e.target.value)}
                    className="input-field"
                    required
                    /* P3 — future-time enforcement when date is today:
                       minimum time = now + 15 min, formatted HH:MM. */
                    min={(() => {
                      const today = new Date().toISOString().slice(0, 10);
                      if (date !== today) return undefined;
                      const t = new Date(Date.now() + 15 * 60 * 1000);
                      return `${String(t.getHours()).padStart(2,'0')}:${String(t.getMinutes()).padStart(2,'0')}`;
                    })()}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Notes (optional)</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Anything the provider should know about your concern..."
                  className="input-field"
                  rows={3}
                />
              </div>

              {error && <div className="booking-error">{error}</div>}

              <button type="submit" className="btn btn-primary w-full" disabled={submitting}>
                {submitting
                  ? <><Loader2 size={16} className="spin"/> Booking...</>
                  : 'Confirm Booking'}
              </button>
            </form>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  // ── Provider directory ───────────────────────────────────────────
  return (
    <div className="bookings-page">
      <Navbar title="Book Appointment" />
      <main className="bookings-main">
        <div>
          <h1 className="diagnosis-page-title">
            {typeFilter === 'dermatologist' && 'Find a Dermatologist'}
            {typeFilter === 'salon' && 'Find a Salon'}
            {typeFilter === 'all' && 'Find a Specialist'}
          </h1>
          <p className="diagnosis-page-subtitle">
            {typeFilter === 'dermatologist' && 'Verified dermatologists near you for skin and scalp concerns.'}
            {typeFilter === 'salon' && 'Beauty salons near you for makeup and styling services.'}
            {typeFilter === 'all' && 'Choose a verified dermatologist or salon near you.'}
          </p>
        </div>

        {/* Context banner — shown when arriving from a specific feature */}
        {initialType !== 'all' && (
          <div className="booking-context-banner">
            <div className="booking-context-icon">
              {initialType === 'dermatologist' ? <Stethoscope size={16}/> : <Scissors size={16}/>}
            </div>
            <div style={{ flex: 1 }}>
              <div className="booking-context-title">
                Showing only {initialType === 'dermatologist' ? 'dermatologists' : 'salons'}
              </div>
              <div className="booking-context-sub">
                You arrived from <strong>{sourceFeature === 'diagnosis' || initialType === 'dermatologist' ? 'Skin/Scalp Diagnosis' : sourceFeature === 'fashion' ? 'Fashion Assistance' : 'Makeup Assistance'}</strong>.
              </div>
            </div>
            <button
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem' }}
              onClick={() => { setTypeFilter('all'); navigate('/bookings', { replace: true }); }}
            >
              Show all providers
            </button>
          </div>
        )}

        {/* Filters */}
        <div className="card booking-filters">
          <div className="provider-type-tabs">
            {PROVIDER_TYPES
              // When arriving from a specific feature, hide the opposite type
              // so the user can't accidentally switch (they can click "Show all"
              // in the context banner above to expand).
              .filter(({ id }) => {
                if (initialType === 'dermatologist') return id !== 'salon';
                if (initialType === 'salon')         return id !== 'dermatologist';
                return true;
              })
              .map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  className={`provider-type-tab ${typeFilter === id ? 'active' : ''}`}
                  onClick={() => setTypeFilter(id)}
                >
                  <Icon size={14}/> {label}
                </button>
              ))}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="text"
              value={cityFilter}
              onChange={(e) => setCityFilter(e.target.value)}
              placeholder="Filter by city…"
              className="input-field booking-city-input"
            />
            <button
              type="button"
              className="btn btn-secondary booking-nearby-btn"
              onClick={handleFindNearby}
              disabled={locating}
            >
              {locating
                ? <><Loader2 size={14} className="spin"/> Locating…</>
                : <><Navigation size={14}/> Find Nearby</>}
            </button>
            <button
              type="button"
              className="btn btn-secondary booking-maps-btn"
              onClick={openInGoogleMaps}
              title={`Open Google Maps in a new tab searching for: ${gmapsQuery()}${cityFilter ? ' near ' + cityFilter : ' near me'}`}
            >
              <MapIcon size={14}/> {gmapsLabel()}
            </button>
          </div>
        </div>
        {locError && (
          <div className="booking-error" style={{ marginTop: '-0.5rem' }}>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>📍 {locError}</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
              <button
                type="button"
                className="btn btn-primary"
                style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem' }}
                onClick={openInGoogleMaps}
              >
                <MapIcon size={14}/> Open in Google Maps instead
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem' }}
                onClick={() => setShowHelp((s) => !s)}
              >
                {showHelp ? 'Hide steps' : 'How to enable location'}
              </button>
            </div>
            {showHelp && (
              <div className="booking-help-panel">
                {locErrorCode === 2 ? (
                  <>
                    <strong>Your OS isn&rsquo;t reporting a location to Chrome.</strong>
                    <p style={{ margin: '0.4rem 0 0.6rem' }}>
                      You already allowed this site in Chrome — but macOS itself has
                      Location Services OFF for Chrome. Fix it once and Find Nearby
                      works forever.
                    </p>
                    <strong>macOS — enable Location Services for Chrome</strong>
                    <ol style={{ paddingLeft: '1.1rem', margin: '0.4rem 0' }}>
                      <li>Click the <strong>Apple menu</strong> in the top-left corner of your screen.</li>
                      <li>Open <strong>System Settings…</strong></li>
                      <li>In the sidebar, click <strong>Privacy &amp; Security</strong>.</li>
                      <li>Scroll down and click <strong>Location Services</strong>.</li>
                      <li>Toggle <strong>Location Services</strong> to <strong>ON</strong> at the top.</li>
                      <li>Scroll the right-hand list to find <strong>Google Chrome</strong> and switch it <strong>ON</strong>.</li>
                      <li>Press <kbd>Cmd+Q</kbd> to fully quit Chrome, then reopen it and return here.</li>
                      <li>Click <strong>Find Nearby</strong> again — it should work now.</li>
                    </ol>
                  </>
                ) : (
                  <>
                    <strong>Allow this site to use your location:</strong>
                    <ol style={{ paddingLeft: '1.1rem', margin: '0.5rem 0' }}>
                      <li>Click the <strong>🔒 lock / 🛈 icon</strong> on the left of the address bar.</li>
                      <li>Find <strong>Location</strong> → change from <em>Block</em> to <em>Allow</em>.</li>
                      <li>Refresh this page (<kbd>Cmd+R</kbd>).</li>
                    </ol>
                  </>
                )}
                <em style={{ color: 'var(--text-tertiary)', fontSize: '0.78rem', display: 'block', marginTop: '0.5rem' }}>
                  Skip the setup — &ldquo;{gmapsLabel()}&rdquo; opens real Google Maps with the right search and works without any permission.
                </em>
              </div>
            )}
          </div>
        )}
        {userLoc && (
          <div className="booking-loc-pill">
            <MapPin size={12}/> Showing distances from your current location
          </div>
        )}

        {!locError && !userLoc && initialType === 'all' && (
          <div className="booking-hint-pill">
            <span>💡</span>
            <span>
              Tip — click <strong>Dermatologist</strong> or <strong>Salon</strong> first,
              then click <strong>{gmapsLabel()}</strong> to open Google Maps with only that type.
            </span>
          </div>
        )}

        {/* ── Live Google Places nearby search ─────────────────── */}
        <NearbyProvidersMap
          searchType={typeFilter}
          defaultCity={cityFilter}
          onBookProvider={(place) => {
            // Convert a Google Place into the shape our booking form expects
            setSelectedProvider({
              id: place.place_id,
              name: place.name,
              address: place.vicinity || '',
              city: '',
              phone: place.formatted_phone_number || '',
              latitude: place._loc?.lat,
              longitude: place._loc?.lng,
              provider_type: typeFilter === 'salon' ? 'salon' : 'dermatologist',
              _google_place_id: place.place_id,
            });
          }}
        />
        {/* Loading / error / empty state legacy fall-back UI. */}
        {loading && providers.length === 0 && (
          <div className="booking-loading">
            <Loader2 size={28} className="spin" />
            <p>Loading providers…</p>
          </div>
        )}
        {/* P3 — Replace infinite spinner with empty-state when list is empty. */}
        {!loading && providers.length === 0 && !error && (
          <div className="booking-loading">
            <MapIcon size={28}/>
            <p style={{ marginTop: '0.5rem' }}>
              No providers loaded — use the live map above to search nearby,
              or click <strong>"{gmapsLabel()}"</strong> to open Google Maps.
            </p>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
