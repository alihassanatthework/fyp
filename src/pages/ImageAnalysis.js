import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { UploadCloud, Camera, Droplets, Wind, CheckCircle2, ShieldCheck, CheckSquare, ArrowLeft } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { useAnalysis } from '../hooks/useAnalysis';
import { useCamera } from '../hooks/useCamera';

const TYPE_META = {
  skin: {
    icon: <Droplets size={28} />,
    label: 'Skin Analysis',
    desc: 'Analyse facial skin conditions, texture, and concerns.',
    bullets: ['Acne, redness', 'Pigmentation', 'Texture insights'],
  },
  scalp: {
    icon: <Wind size={28} />,
    label: 'Scalp Analysis',
    desc: 'Analyse scalp health, hair density, and conditions.',
    bullets: ['Dandruff, flakes', 'Dryness', 'Hair density'],
  },
};

export default function ImageAnalysis() {
  const location = useLocation();
  const urlType = (() => {
    const t = new URLSearchParams(location.search).get('type');
    return t === 'skin' || t === 'scalp' ? t : null;
  })();
  const typeLocked = urlType !== null;

  // No type selected initially when not locked — user must pick a card first.
  const [analysisType, setAnalysisType] = useState(urlType || null);
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState(false);
  const [serverError, setServerError] = useState('');
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
      return;
    }
    setError(false);
    setFile(f);
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
      const payload = response?.data;
      if (payload) {
        try { localStorage.setItem('lastAnalysis', JSON.stringify(payload)); } catch (e) {}
        navigate('/diagnosis');
      } else {
        const msg = response?.error || 'Upload failed. Please try a different image.';
        setServerError(msg);
      }
    } finally {
      uploadInFlightRef.current = false;
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
    setError(false);
    setServerError('');
  };

  const showSelector = !analysisType;
  const meta = analysisType ? TYPE_META[analysisType] : null;

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title="Image Analysis" />

      <main className="flex-1 page-container py-8">
        <div className="text-center mb-10">
          <h1 className="font-display text-3xl font-bold text-gray-900 text-white">Image Analysis</h1>
          <p className="text-gray-400 text-gray-500 mt-2 text-sm">
            {showSelector
              ? 'Which analysis do you want? Pick a type below to begin.'
              : `Upload your image for personalised ${analysisType} analysis.`}
          </p>
        </div>

        {/* ── Step 1: vertical type cards ───────────────────────────────── */}
        {showSelector && (
          <div className="flex flex-col gap-4 max-w-2xl mx-auto">
            {['skin', 'scalp'].map((id) => {
              const t = TYPE_META[id];
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => setAnalysisType(id)}
                  className="card p-6 text-left transition-shadow hover:shadow-lg"
                  style={{ cursor: 'pointer', border: '1px solid var(--border-color)' }}
                >
                  <div className="flex items-center gap-4 mb-3">
                    <div
                      className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0"
                      style={{ background: 'var(--blue-50)', color: 'var(--nav-accent)' }}
                    >
                      {t.icon}
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-800 text-gray-100 text-base mb-0.5">{t.label}</h3>
                      <p className="text-sm text-gray-500 text-gray-400">{t.desc}</p>
                    </div>
                  </div>
                  <ul
                    className="text-xs text-gray-500 text-gray-400 flex flex-wrap gap-2"
                    style={{ paddingLeft: '4.5rem', listStyle: 'none' }}
                  >
                    {t.bullets.map((b) => (
                      <li
                        key={b}
                        style={{
                          background: 'var(--bg-tertiary)',
                          padding: '0.25rem 0.625rem',
                          borderRadius: '999px',
                        }}
                      >
                        {b}
                      </li>
                    ))}
                  </ul>
                </button>
              );
            })}
          </div>
        )}

        {/* ── Step 2: upload + camera (only after a type is chosen) ─────── */}
        {!showSelector && (
          <div className="max-w-2xl mx-auto space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ background: 'var(--blue-50)', color: 'var(--nav-accent)' }}
                >
                  {meta.icon}
                </div>
                <div>
                  <p className="font-semibold text-gray-800 text-gray-100 text-sm">{meta.label}</p>
                  <p className="text-xs text-gray-400 text-gray-500">{meta.desc}</p>
                </div>
              </div>
              {!typeLocked && (
                <button onClick={handleBack} className="btn-secondary text-xs py-1.5">
                  <ArrowLeft size={13}/> Change
                </button>
              )}
            </div>

            <div className="flex items-center gap-2 text-xs text-gray-500 text-gray-400 bg-white bg-gray-900 border border-gray-100 border-gray-800 rounded-xl px-4 py-3">
              <Camera size={14} className="text-gray-400 shrink-0"/>
              {analysisType === 'scalp'
                ? 'Upload a clear scalp image in good lighting.'
                : 'Upload a clear face image in good lighting. No makeup.'}
            </div>

            <label
              htmlFor="fyp-file-input"
              onDragOver={(e) => { if (dropDisabled) return; e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => { if (dropDisabled) return; setDragOver(false); }}
              onDrop={onDrop}
              style={{ pointerEvents: dropDisabled ? 'none' : 'auto' }}
              className={`relative block ${loading ? 'cursor-not-allowed' : 'cursor-pointer'} rounded-2xl border-2 border-dashed flex flex-col items-center justify-center py-16 transition-all ${
                dragOver
                  ? 'border-blue-400 bg-blue-50 bg-blue-900/10'
                  : file
                    ? 'border-green-400 bg-green-50 bg-green-900/10'
                    : 'border-gray-200 border-gray-700 bg-white bg-gray-900 border-blue-300 bg-blue-50/30'
              }`}>
              <input
                id="fyp-file-input"
                ref={fileRef}
                type="file"
                className="hidden"
                accept=".jpg,.jpeg,.png,.heic"
                onClick={e => { e.stopPropagation(); e.target.value = ''; }}
                onChange={e => validateAndSet(e.target.files[0])} />

              {file ? (
                <>
                  <CheckCircle2 size={44} className="text-green-500 mb-3"/>
                  <p className="font-semibold text-gray-700 text-gray-200 text-sm">{file.name}</p>
                  <p className="text-xs text-gray-400 mt-1">Ready to analyse</p>
                </>
              ) : (
                <>
                  <UploadCloud size={44} className="text-red-400 mb-3"/>
                  <p className="font-semibold text-gray-700 text-gray-200">Upload Your Image</p>
                  <p className="text-sm text-gray-400 text-gray-500 mt-1">Drag and drop your image here, or click to browse</p>
                  <p className="text-xs text-gray-400 text-gray-500 mt-2">Supported formats: JPG, PNG, HEIC. Max size: 10MB.</p>
                </>
              )}
            </label>

            <div className="grid grid-cols-2 gap-3">
              <button type="button" onClick={handlePickFile} className="btn-secondary py-3" disabled={loading}>
                <UploadCloud size={16}/> Choose File
              </button>
              <button onClick={handleTakePhoto} className="btn-secondary py-3">
                <Camera size={16}/> Take Photo
              </button>
            </div>

            {error && (
              <div className="rounded-xl bg-red-50 bg-red-900/20 border border-red-200 border-red-800 px-4 py-3 text-sm text-red-600 text-red-400 text-center">
                Invalid file type or size. Please try again.
              </div>
            )}

            {serverError && (
              <div className="rounded-xl bg-red-50 bg-red-900/20 border border-red-200 border-red-800 px-4 py-3 text-sm text-red-600 text-red-400 text-center">
                {serverError}
              </div>
            )}

            {file && (
              <button
                onClick={handleAnalyze}
                disabled={loading}
                className="btn-primary w-full py-3 text-base disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Analysing...' : 'Analyse Now'}
              </button>
            )}
          </div>
        )}

        {/* Feature cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-10">
          {[
            { icon: <CheckCircle2 size={22} className="text-gray-500"/>, title: 'Face and Scalp Support', desc: 'Both analysis types supported for comprehensive care.' },
            { icon: <ShieldCheck size={22} className="text-gray-500"/>, title: 'Input Validation', desc: 'Automatic file type and size checks ensure valid uploads.' },
            { icon: <CheckSquare size={22} className="text-gray-500"/>, title: 'Camera and Upload', desc: 'Multiple input methods available for convenience.' },
          ].map((item, i) => (
            <div key={i} className="card p-5">
              <div className="mb-3">{item.icon}</div>
              <h3 className="font-semibold text-sm text-gray-800 text-gray-100 mb-1">{item.title}</h3>
              <p className="text-xs text-gray-400 text-gray-500 leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </main>

      <Footer />
    </div>
  );
}
