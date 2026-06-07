/**
 * NearbyProvidersMap
 * ──────────────────
 * Renders an interactive Google Map with real-time provider cards fetched
 * from the Google Maps Places API. Used for:
 *   - Diagnosis report → searchType='dermatologist'
 *   - Makeup/Fashion result → searchType='salon'
 *   - Bookings page → searchType prop drives both modes
 *
 * Requirements:
 *   1. REACT_APP_GOOGLE_MAPS_API_KEY set in react/.env (see README in same folder)
 *   2. Places API + Maps JavaScript API + Geocoding API enabled in Google Cloud
 *
 * Fallbacks:
 *   - If geolocation fails → user can enter a city (geocoded to lat/lng)
 *   - If API key missing → shows clear setup instructions
 *   - If no results → friendly empty state
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import {
  MapPin, Star, Phone, Navigation, Clock,
  Loader2, Search, AlertTriangle, Calendar, Image as ImageIcon,
} from 'lucide-react';
import './NearbyProvidersMap.css';

const GOOGLE_MAPS_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY || '';

// Map of frontend searchType → Google Places search keyword + types
const SEARCH_CONFIG = {
  dermatologist: {
    keyword:    'dermatologist',
    type:       'doctor',          // Places type
    label:      'Dermatologists',
    pinColor:   '#6366f1',
  },
  salon: {
    keyword:    'beauty salon',
    type:       'beauty_salon',
    label:      'Salons',
    pinColor:   '#ec4899',
  },
  all: {
    keyword:    'dermatologist OR beauty salon',
    type:       null,
    label:      'Providers',
    pinColor:   '#10b981',
  },
};

// ── Singleton loader: only ever load the Google Maps script once ───
let googleMapsPromise = null;
function loadGoogleMaps() {
  if (window.google && window.google.maps && window.google.maps.places) {
    return Promise.resolve(window.google.maps);
  }
  if (googleMapsPromise) return googleMapsPromise;
  if (!GOOGLE_MAPS_API_KEY) {
    return Promise.reject(new Error('NO_API_KEY'));
  }
  googleMapsPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places&loading=async`;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (window.google && window.google.maps) resolve(window.google.maps);
      else reject(new Error('LOAD_FAILED'));
    };
    script.onerror = () => reject(new Error('LOAD_FAILED'));
    document.head.appendChild(script);
  });
  return googleMapsPromise;
}

// ── Distance helper (Haversine) ─────────────────────────────────────
function haversineKm(a, b) {
  const R = 6371;
  const dLat = (b.lat - a.lat) * Math.PI / 180;
  const dLng = (b.lng - a.lng) * Math.PI / 180;
  const s = Math.sin(dLat/2)**2 +
            Math.cos(a.lat * Math.PI / 180) *
            Math.cos(b.lat * Math.PI / 180) *
            Math.sin(dLng/2)**2;
  return Math.round(2 * R * Math.asin(Math.sqrt(s)) * 10) / 10;
}

export default function NearbyProvidersMap({
  searchType = 'all',
  defaultCity = '',
  radiusMeters = 8000,
  onBookProvider,             // (place) => void
  title,                      // optional override title
  subtitle,
}) {
  const cfg = SEARCH_CONFIG[searchType] || SEARCH_CONFIG.all;

  const [center,      setCenter]      = useState(null);   // {lat, lng}
  const [places,      setPlaces]      = useState([]);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState('');
  const [cityInput,   setCityInput]   = useState(defaultCity);
  const [usingCity,   setUsingCity]   = useState(!!defaultCity);
  const mapRef       = useRef(null);
  const mapInstance  = useRef(null);
  const markersRef   = useRef([]);

  // Detect missing API key once
  const noApiKey = !GOOGLE_MAPS_API_KEY;

  // ── Get user position ─────────────────────────────────────────────
  const requestGeolocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported.');
      return;
    }
    setLoading(true);
    setError('');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCenter({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setUsingCity(false);
      },
      (err) => {
        let msg = 'Could not get your location.';
        if (err.code === 1) msg = 'Location permission was denied.';
        if (err.code === 2) msg = 'Your OS did not report a location.';
        if (err.code === 3) msg = 'Location request timed out.';
        setError(msg);
        setLoading(false);
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }
    );
  }, []);

  // ── Geocode a city to lat/lng (fallback when geolocation fails) ──
  const geocodeCity = useCallback(async (city) => {
    if (!city || !city.trim()) return;
    setLoading(true);
    setError('');
    try {
      const maps = await loadGoogleMaps();
      const geocoder = new maps.Geocoder();
      const result = await new Promise((resolve, reject) => {
        geocoder.geocode({ address: city }, (results, status) => {
          if (status === 'OK' && results.length) resolve(results[0]);
          else reject(new Error(`Could not find "${city}" on Google Maps.`));
        });
      });
      const loc = result.geometry.location;
      setCenter({ lat: loc.lat(), lng: loc.lng() });
      setUsingCity(true);
    } catch (e) {
      setLoading(false);
      setError(e.message === 'NO_API_KEY' ? 'NO_API_KEY' : (e.message || 'Geocode failed.'));
    }
  }, []);

  // Auto-request geolocation on mount (only if no defaultCity)
  useEffect(() => {
    if (defaultCity) {
      geocodeCity(defaultCity);
    } else {
      requestGeolocation();
    }
  }, []); // eslint-disable-line

  // ── Once we have center: load map + search nearby ─────────────────
  useEffect(() => {
    if (!center) return;
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError('');
        const maps = await loadGoogleMaps();
        if (cancelled) return;

        // Initialize the map if not already
        if (!mapInstance.current && mapRef.current) {
          mapInstance.current = new maps.Map(mapRef.current, {
            center,
            zoom: 13,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
          });
        } else if (mapInstance.current) {
          mapInstance.current.setCenter(center);
        }

        // Drop a user-location pin
        new maps.Marker({
          map:     mapInstance.current,
          position: center,
          title:   'You are here',
          icon: {
            path: maps.SymbolPath.CIRCLE,
            scale: 8,
            fillColor: '#3b82f6',
            fillOpacity: 1,
            strokeColor: '#fff',
            strokeWeight: 2,
          },
        });

        // Places nearby search
        const service = new maps.places.PlacesService(mapInstance.current);
        service.nearbySearch(
          {
            location: center,
            radius:   radiusMeters,
            keyword:  cfg.keyword,
            ...(cfg.type ? { type: cfg.type } : {}),
          },
          (results, status) => {
            if (cancelled) return;
            setLoading(false);
            if (status !== maps.places.PlacesServiceStatus.OK || !results) {
              if (status === maps.places.PlacesServiceStatus.ZERO_RESULTS) {
                setPlaces([]);
              } else {
                setError(`Places search failed: ${status}`);
              }
              return;
            }
            // Clear previous markers
            markersRef.current.forEach((m) => m.setMap(null));
            markersRef.current = [];

            // Sort by distance and take top 20
            const enriched = results
              .filter((r) => r.geometry && r.geometry.location)
              .map((r) => ({
                ...r,
                _loc: { lat: r.geometry.location.lat(), lng: r.geometry.location.lng() },
              }))
              .map((r) => ({ ...r, _distance_km: haversineKm(center, r._loc) }))
              .sort((a, b) => a._distance_km - b._distance_km)
              .slice(0, 20);

            // Render markers
            enriched.forEach((p) => {
              const marker = new maps.Marker({
                map: mapInstance.current,
                position: p._loc,
                title: p.name,
              });
              const info = new maps.InfoWindow({
                content: `<div style="color:#111;font-size:13px;font-weight:600;">${p.name}</div>
                          <div style="color:#444;font-size:12px;">${p.vicinity || ''}</div>`,
              });
              marker.addListener('click', () => info.open(mapInstance.current, marker));
              markersRef.current.push(marker);
            });

            setPlaces(enriched);
          }
        );
      } catch (e) {
        if (cancelled) return;
        setLoading(false);
        if (e.message === 'NO_API_KEY') setError('NO_API_KEY');
        else setError(e.message || 'Map failed to load.');
      }
    })();
    return () => { cancelled = true; };
  }, [center, searchType]); // eslint-disable-line

  // ── Helpers ──────────────────────────────────────────────────────
  const directionsUrl = (p) =>
    `https://www.google.com/maps/dir/?api=1&destination=${p._loc.lat},${p._loc.lng}&destination_place_id=${p.place_id}`;
  const photoUrl = (p) => {
    if (!p.photos || !p.photos.length) return null;
    try { return p.photos[0].getUrl({ maxWidth: 400, maxHeight: 240 }); }
    catch { return null; }
  };
  const openClosed = (p) => {
    if (!p.opening_hours) return null;
    if (typeof p.opening_hours.open_now === 'boolean') return p.opening_hours.open_now;
    if (typeof p.opening_hours.isOpen === 'function') {
      try { return p.opening_hours.isOpen(); } catch { return null; }
    }
    return null;
  };

  // ── No API key fallback ──────────────────────────────────────────
  // Visual warning card removed per UX request — when no key is set,
  // the component renders nothing on the page. All map / booking logic
  // (geolocation, Places search, marker rendering, onBookProvider
  // callback, etc.) remains intact for when REACT_APP_GOOGLE_MAPS_API_KEY
  // IS configured. The Bookings page also exposes its own
  // "Open Google Maps in a new tab" button as an independent fallback.
  if (noApiKey) {
    return null;
  }

  // ── Render ───────────────────────────────────────────────────────
  return (
    <div className="npm-wrap">
      <div className="npm-header">
        <div>
          <h2 className="npm-title">{title || `Nearby ${cfg.label}`}</h2>
          <p className="npm-subtitle">
            {subtitle ||
              (usingCity
                ? `Showing ${cfg.label.toLowerCase()} near ${cityInput || 'the entered city'} (Google Places live data).`
                : `Showing ${cfg.label.toLowerCase()} near your current location (Google Places live data).`)}
          </p>
        </div>
        <div className="npm-controls">
          <button className="npm-btn npm-btn-primary" onClick={requestGeolocation} disabled={loading}>
            <Navigation size={14}/> Use my location
          </button>
        </div>
      </div>

      {/* Manual city fallback */}
      <form
        className="npm-city-row"
        onSubmit={(e) => { e.preventDefault(); geocodeCity(cityInput); }}
      >
        <input
          type="text"
          value={cityInput}
          onChange={(e) => setCityInput(e.target.value)}
          placeholder="Or type a city (e.g. Lahore, Karachi, Islamabad)…"
          className="npm-city-input"
        />
        <button type="submit" className="npm-btn npm-btn-secondary" disabled={!cityInput.trim() || loading}>
          <Search size={14}/> Search this city
        </button>
      </form>

      {/* Map */}
      <div className="npm-map" ref={mapRef} />

      {/* Status */}
      {loading && (
        <div className="npm-status">
          <Loader2 size={18} className="npm-spin" /> Loading nearby {cfg.label.toLowerCase()}…
        </div>
      )}
      {error && error !== 'NO_API_KEY' && (
        <div className="npm-error">
          <AlertTriangle size={16}/> {error}
          {error.includes('location') && (
            <button className="npm-btn npm-btn-secondary" onClick={() => document.querySelector('.npm-city-input')?.focus()}>
              Use city instead
            </button>
          )}
        </div>
      )}

      {/* Results */}
      {!loading && !error && places.length === 0 && center && (
        <div className="npm-empty">
          No {cfg.label.toLowerCase()} found within {radiusMeters / 1000} km. Try a different city or widen the search.
        </div>
      )}

      <div className="npm-grid">
        {places.map((p) => {
          const open = openClosed(p);
          const img  = photoUrl(p);
          return (
            <div key={p.place_id} className="npm-card-item">
              <div className="npm-card-photo">
                {img ? (
                  <img src={img} alt={p.name} />
                ) : (
                  <div className="npm-card-photo-fallback"><ImageIcon size={22}/></div>
                )}
                {open !== null && (
                  <span className={`npm-status-chip ${open ? 'open' : 'closed'}`}>
                    {open ? 'Open now' : 'Closed'}
                  </span>
                )}
              </div>
              <div className="npm-card-body">
                <h3 className="npm-card-name">{p.name}</h3>
                {(p.rating || p.user_ratings_total) && (
                  <p className="npm-card-rating">
                    <Star size={13} fill="#f59e0b" color="#f59e0b" />
                    <strong>{p.rating?.toFixed?.(1) || p.rating || '—'}</strong>
                    {p.user_ratings_total ? <span>({p.user_ratings_total} reviews)</span> : null}
                  </p>
                )}
                <p className="npm-card-line"><MapPin size={12}/> {p.vicinity || '—'}</p>
                <p className="npm-card-line"><Navigation size={12}/> {p._distance_km} km from you</p>
                {p.opening_hours?.weekday_text && (
                  <p className="npm-card-line"><Clock size={12}/> See hours on Google</p>
                )}

                <div className="npm-card-actions">
                  <a
                    className="npm-btn npm-btn-secondary"
                    href={directionsUrl(p)}
                    target="_blank" rel="noreferrer noopener"
                  >
                    <Navigation size={13}/> Directions
                  </a>
                  <button
                    className="npm-btn npm-btn-primary"
                    onClick={() => onBookProvider ? onBookProvider(p) : window.open(directionsUrl(p), '_blank')}
                  >
                    <Calendar size={13}/> Book
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
