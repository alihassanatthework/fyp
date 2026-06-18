import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  UploadCloud, Camera, Droplets, Wind,
  CheckCircle2, ShieldCheck, CheckSquare,
  ArrowLeft, ChevronRight, Sparkles, ScanLine,
} from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { useAnalysis } from '../hooks/useAnalysis';
import { useCamera } from '../hooks/useCamera';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';
import './ImageAnalysis.css';

const TYPE_META = {
  skin: {
    icon: <Droplets size={24} />,
    label: 'Skin Analysis',
    desc: 'Analyse facial skin conditions, texture, and concerns.',
    bullets: ['Acne & redness', 'Pigmentation', 'Texture insights'],
  },
  scalp: {
    icon: <Wind size={24} />,
    label: 'Scalp Analysis',
    desc: 'Analyse scalp health, hair density, and conditions.',
    bullets: ['Dandruff & flakes', 'Dryness', 'Hair density'],
  },
};

export default function ImageAnalysis() {
  const location = useLocation();
  const urlType = (() => {
    const t = new URLSearchParams(location.search).get('type');
    return t === 'skin' || t === 'scalp' ? t : null;
  })();
  const typeLocked = urlType !== null;

  const [analysisType, setAnalysisType] = useState(urlType || null);
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [error, setError] = useState(false);
  const [serverError, setServerError] = useState('');
  // Daily scan quota (Free tier). null until loaded; {is_premium, used, limit, remaining}.
  const [quota, setQuota] = useState(null);

  const fetchQuota = async () => {
    try {
      const res = await apiClient.get(API_ENDPOINTS.ANALYSIS.STATS);
      if (res?.data?.scan_quota) setQuota(res.data.scan_quota);
    } catch (e) { /* non-blocking */ }
  };
  useEffect(() => { fetchQuota(); }, []);
  const fileRef = useRef();
  const uploadInFlightRef = useRef(false);
  const navigate = useNavigate();

  const { uploadImage, loading } = useAnalysis();
  const { openNativeCamera } = useCamera();
  const dropDisabled = loading || uploadInFlightRef.current;

  useEffect(() => {
    uploadInFlightRef.current = false;
    const onPageShow = (e) => {
      if (e.persisted) {
        uploadInFlightRef.current = false;
        setServerError('');
        setFile(null);
        setPreviewUrl(null);
        setError(false);
      }
    };
    window.addEventListener('pageshow', onPageShow);
    return () => window.removeEventListener('pageshow', onPageShow);
  }, []);

  const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/heic'];
  const MAX_SIZE = 10 * 1024 * 1024;

  const validateAndSet = (f) => {
    if (!f) return;
    if (!ALLOWED_TYPES.includes(f.type) || f.size > MAX_SIZE) {
      setError(true);
      setFile(null);
      setPreviewUrl(null);
      return;
    }
    setError(false);
    setFile(f);
    const url = URL.createObjectURL(f);
    setPreviewUrl(url);
  };

  const onDrop = (e) => {
    if (dropDisabled) return;
    e.preventDefault();
    setDragOver(false);
    validateAndSet(e.dataTransfer.files[0]);
  };

  const handlePickFile = () => {
    if (dropDisabled) return;
    if (fileRef.current) fileRef.current.click();
  };

  const handleAnalyze = async () => {
    if (!file) return;
    if (uploadInFlightRef.current) return;
    uploadInFlightRef.current = true;
    setServerError('');

    const response = await uploadImage(file, analysisType);
    try {
      if (response?.success && response?.data) {
        const payload = response.data;
        try { localStorage.setItem('lastAnalysis', JSON.stringify(payload)); } catch (e) {}
        // Pass via route state too so the diagnosis page can render immediately
        // even before localStorage is read.
        navigate('/diagnosis', { state: { data: payload } });
      } else {
        const msg = response?.error || 'Upload failed. Please try a different image.';
        setServerError(msg);
      }
    } finally {
      uploadInFlightRef.current = false;
      fetchQuota();   // refresh remaining-scans count after each attempt
    }
  };

  const handleTakePhoto = () => {
    openNativeCamera((capturedFile) => {
      validateAndSet(capturedFile);
    });
  };

  const handleBack = () => {
    setAnalysisType(null);
    setFile(null);
    setPreviewUrl(null);
    setError(false);
    setServerError('');
  };

  const showSelector = !analysisType;
  const meta = analysisType ? TYPE_META[analysisType] : null;

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title="Image Analysis" />

      <main className="flex-1 page-container py-8">

        {/* Hero */}
        <div className="ia-hero">
          <div className="ia-hero-badge">
            <ScanLine size={13}/> AI-Powered Analysis
          </div>
          <h1>Image Analysis</h1>
          <p>
            {showSelector
              ? 'Select an analysis type to get started.'
              : `Upload your image for personalised ${analysisType} analysis.`}
          </p>
        </div>

        {/* ── Step 1: type selector ── */}
        {showSelector && (
          <div className="ia-type-grid">
            {['skin', 'scalp'].map((id) => {
              const t = TYPE_META[id];
              return (
                <button key={id} type="button" className="ia-type-card" onClick={() => setAnalysisType(id)}>
                  <ChevronRight size={16} className="ia-type-arrow"/>
                  <div className="ia-type-icon">{t.icon}</div>
                  <div className="ia-type-label">{t.label}</div>
                  <div className="ia-type-desc">{t.desc}</div>
                  <ul className="ia-type-bullets">
                    {t.bullets.map((b) => <li key={b}>{b}</li>)}
                  </ul>
                </button>
              );
            })}
          </div>
        )}

        {/* ── Step 2: upload card ── */}
        {!showSelector && (
          <div className="ia-upload-wrapper">
            <div className="ia-upload-card">

              {/* Card header */}
              <div className="ia-card-header">
                <div className="ia-card-header-left">
                  <div className="ia-card-header-icon">{meta.icon}</div>
                  <div>
                    <div className="ia-card-header-title">{meta.label}</div>
                    <div className="ia-card-header-sub">{meta.desc}</div>
                  </div>
                </div>
                {!typeLocked && (
                  <button className="ia-card-change-btn" onClick={handleBack}>
                    <ArrowLeft size={13}/> Change
                  </button>
                )}
              </div>

              {/* Card body */}
              <div className="ia-card-body">

                {/* Tip */}
                <div className="ia-tip-bar">
                  <Camera size={14}/>
                  {analysisType === 'scalp'
                    ? 'Upload a clear scalp image in good lighting.'
                    : 'Upload a clear face image in good lighting. No makeup.'}
                </div>

                {/* Drop zone */}
                <label
                  htmlFor="ia-file-input"
                  onDragOver={(e) => { if (dropDisabled) return; e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => { if (dropDisabled) return; setDragOver(false); }}
                  onDrop={onDrop}
                  style={{ pointerEvents: dropDisabled ? 'none' : 'auto' }}
                  className={`ia-dropzone ${dragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
                >
                  <input
                    id="ia-file-input"
                    ref={fileRef}
                    type="file"
                    className="hidden"
                    style={{ display: 'none' }}
                    accept=".jpg,.jpeg,.png,.heic"
                    onClick={e => { e.stopPropagation(); e.target.value = ''; }}
                    onChange={e => validateAndSet(e.target.files[0])}
                  />

                  {file && previewUrl ? (
                    <div className="ia-preview-wrap">
                      <img src={previewUrl} alt="Preview"/>
                      <div className="ia-preview-overlay">
                        <span className="ia-preview-filename">{file.name}</span>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="ia-dropzone-icon">
                        <UploadCloud size={28}/>
                      </div>
                      <div className="ia-dropzone-title">Drop your image here</div>
                      <div className="ia-dropzone-sub">or use the buttons below to choose or capture</div>
                      <div className="ia-dropzone-hint">JPG · PNG · HEIC &nbsp;·&nbsp; Max 10 MB</div>
                    </>
                  )}
                </label>

                {/* Ready status — clean text UNDER the card */}
                {file && previewUrl && (
                  <div className="ia-ready-status">
                    <CheckCircle2 size={16}/>
                    <span>Image ready — click <strong>Analyse Now</strong></span>
                  </div>
                )}

                {/* Choose / Take buttons */}
                <div className="ia-action-row">
                  <button type="button" className="ia-action-btn" onClick={handlePickFile} disabled={loading}>
                    <UploadCloud size={16}/> Choose File
                  </button>
                  <button type="button" className="ia-action-btn" onClick={handleTakePhoto} disabled={loading}>
                    <Camera size={16}/> Take Photo
                  </button>
                </div>

                {/* Errors */}
                {error && (
                  <div className="ia-error-bar">
                    Invalid file type or size. Please upload a JPG, PNG, or HEIC under 10 MB.
                  </div>
                )}
                {serverError && (
                  <div className="ia-error-bar">{serverError}</div>
                )}

                {/* Daily scan quota (Free tier) */}
                {quota && !quota.is_premium && quota.remaining > 0 && (
                  <div className="ia-scan-quota">
                    <ScanLine size={14}/> {quota.remaining}/{quota.limit} scans left today
                  </div>
                )}
                {quota && !quota.is_premium && quota.remaining <= 0 && (
                  <div className="ia-scan-limit">
                    <p className="ia-scan-limit-title">
                      Daily scan limit reached ({quota.limit}/{quota.limit})
                    </p>
                    <p className="ia-scan-limit-sub">
                      Your free scans reset at midnight. Upgrade to Premium for unlimited scans.
                    </p>
                    <button className="ia-upgrade-btn" onClick={() => navigate('/upgrade')}>
                      <Sparkles size={14}/> Upgrade to Premium
                    </button>
                  </div>
                )}
                {/* Premium users: no counter shown (unlimited). */}

                {/* Analyse button */}
                {file && (
                  <button
                    className="ia-analyse-btn"
                    onClick={handleAnalyze}
                    disabled={loading || (quota && !quota.is_premium && quota.remaining <= 0)}
                  >
                    {loading
                      ? <><span className="ia-spinner"/>Analysing…</>
                      : <><Sparkles size={16}/> Analyse Now</>}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Feature cards */}
        <div className="ia-feature-grid">
          {[
            { icon: <CheckCircle2 size={20}/>, title: 'Face & Scalp Support', desc: 'Both analysis types supported for comprehensive care.' },
            { icon: <ShieldCheck size={20}/>, title: 'Input Validation', desc: 'Automatic file type and size checks ensure valid uploads.' },
            { icon: <CheckSquare size={20}/>, title: 'Camera & Upload', desc: 'Multiple input methods available for convenience.' },
          ].map((item, i) => (
            <div key={i} className="ia-feature-card">
              <div className="ia-feature-icon">{item.icon}</div>
              <div className="ia-feature-title">{item.title}</div>
              <div className="ia-feature-desc">{item.desc}</div>
            </div>
          ))}
        </div>
      </main>

      <Footer />
    </div>
  );
}
