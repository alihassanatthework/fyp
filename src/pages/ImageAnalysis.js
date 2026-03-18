import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, Camera, Smile, Scissors, CheckCircle2, ShieldCheck, CheckSquare } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { useAnalysis } from '../hooks/useAnalysis';
import { useCamera } from '../hooks/useCamera';


export default function ImageAnalysis() {
  const [analysisType, setAnalysisType] = useState('skin');
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState(false);
  const fileRef = useRef();
  const navigate = useNavigate();

  const { uploadImage, loading } = useAnalysis();
  const { openNativeCamera } = useCamera();

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
    e.preventDefault();
    setDragOver(false);
    validateAndSet(e.dataTransfer.files[0]);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    const response = await uploadImage(file, analysisType);
    if (response.success) {
      navigate('/diagnosis', { state: { data: response.data } });
    } else {
      console.error('Upload failed:', response.error);
    }
  };

  const handleTakePhoto = () => {
    openNativeCamera((capturedFile) => {
      console.log('Photo captured:', capturedFile);
      validateAndSet(capturedFile);
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title="Image Analysis" />

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">
        <div className="text-center mb-10">
          <h1 className="font-display text-3xl font-bold text-gray-900 text-white">Image Analysis</h1>
          <p className="text-gray-400 text-gray-500 mt-2 text-sm">Upload your image for personalized skin or scalp analysis</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Left: select type */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-700 text-gray-300 mb-1">
              <span className="w-5 h-5 rounded-full bg-gray-200 bg-gray-700 flex items-center justify-center text-xs font-bold text-gray-600 text-gray-300">⏱</span>
              Select Analysis Type
            </div>

            {[
              { id: 'skin', icon: <Smile size={20} className="text-blue-500"/>, label: 'Skin Analysis', desc: 'Analyze facial skin conditions, texture, and concerns' },
              { id: 'scalp', icon: <Scissors size={20} className="text-indigo-500"/>, label: 'Scalp Analysis', desc: 'Analyze scalp health, hair density, and conditions' },
            ].map(opt => (
              <button key={opt.id} onClick={() => setAnalysisType(opt.id)}
                className={`w-full text-left p-4 rounded-2xl border-2 transition-all ${
                  analysisType === opt.id
                    ? 'border-blue-500 bg-blue-50 bg-blue-900/20'
                    : 'border-gray-200 border-gray-700 bg-white bg-gray-900 border-gray-300'
                }`}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    {opt.icon}
                    <span className="font-semibold text-gray-800 text-gray-100 text-sm">{opt.label}</span>
                  </div>
                  <span className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                    analysisType === opt.id ? 'border-blue-500 bg-blue-500' : 'border-gray-300 border-gray-600'
                  }`}>
                    {analysisType === opt.id && <span className="w-1.5 h-1.5 rounded-full bg-white block"/>}
                  </span>
                </div>
                <p className="text-xs text-gray-400 text-gray-500 leading-relaxed pl-7">{opt.desc}</p>
              </button>
            ))}
          </div>

          {/* Right: upload */}
          <div className="md:col-span-2 space-y-4">
            <div className="flex items-center gap-2 text-xs text-gray-500 text-gray-400 bg-white bg-gray-900 border border-gray-100 border-gray-800 rounded-xl px-4 py-3">
              <Camera size={14} className="text-gray-400 shrink-0"/>
              Upload a clear face image in good lighting. No makeup.
            </div>

            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => fileRef.current.click()}
              className={`relative cursor-pointer rounded-2xl border-2 border-dashed flex flex-col items-center justify-center py-16 transition-all ${
                dragOver
                  ? 'border-blue-400 bg-blue-50 bg-blue-900/10'
                  : file
                    ? 'border-green-400 bg-green-50 bg-green-900/10'
                    : 'border-gray-200 border-gray-700 bg-white bg-gray-900 border-blue-300 bg-blue-50/30'
              }`}>
              <input ref={fileRef} type="file" className="hidden" accept=".jpg,.jpeg,.png,.heic"
                onChange={e => validateAndSet(e.target.files[0])} />

              {file ? (
                <>
                  <CheckCircle2 size={44} className="text-green-500 mb-3"/>
                  <p className="font-semibold text-gray-700 text-gray-200 text-sm">{file.name}</p>
                  <p className="text-xs text-gray-400 mt-1">Ready to analyze</p>
                </>
              ) : (
                <>
                  <UploadCloud size={44} className="text-red-400 mb-3"/>
                  <p className="font-semibold text-gray-700 text-gray-200">Upload Your Image</p>
                  <p className="text-sm text-gray-400 text-gray-500 mt-1">Drag and drop your image here, or click to browse</p>
                  <p className="text-xs text-gray-400 text-gray-500 mt-2">Supported formats: JPG, PNG, HEIC • Max size: 10MB</p>
                </>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => fileRef.current.click()} className="btn-secondary py-3">
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

            {file && (
              <button
                onClick={handleAnalyze}
                disabled={loading}
                className="btn-primary w-full py-3 text-base disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Analyzing...' : 'Analyze Now →'}
              </button>
            )}
          </div>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-10">
          {[
            { icon: <CheckCircle2 size={22} className="text-gray-500"/>, title: 'Face & Scalp Support', desc: 'Both analysis types supported for comprehensive care.' },
            { icon: <ShieldCheck size={22} className="text-gray-500"/>, title: 'Input Validation', desc: 'Automatic file type and size checks ensure valid uploads.' },
            { icon: <CheckSquare size={22} className="text-gray-500"/>, title: 'Camera & Upload', desc: 'Multiple input methods available for convenience.' },
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