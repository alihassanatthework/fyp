import { useNavigate } from 'react-router-dom';
import { Home, Plus, ArrowRight, RefreshCw } from 'lucide-react';
import Navbar from '../components/Navbar';

const records = [
  { type: 'Skin Analysis', condition: 'Detected condition: Acne, mild redness', date: '12 Mar 2025 · 09:24 AM', severity: 'Mild', sClass: 'badge-mild' },
  { type: 'Scalp Analysis', condition: 'Detected condition: Dandruff and dryness', date: '03 Mar 2025 · 06:15 PM', severity: 'Moderate', sClass: 'badge-moderate' },
  { type: 'Skin Analysis', condition: 'Detected condition: Pigmentation', date: '18 Feb 2025 · 01:42 PM', severity: 'Severe', sClass: 'badge-severe' },
];

export default function AnalysisHistory() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title="Analysis History" subtitle="AI-Powered Skin, Scalp, Makeup & Fashion Assistant" />

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">

        {/* Page header */}
        <div className="flex items-start justify-between mb-7">
          <div>
            <h1 className="text-xl font-bold text-gray-900 text-white">Analysis History</h1>
            <p className="text-sm text-gray-400 text-gray-500 mt-0.5">Record of your previous skin and scalp analyses.</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => navigate('/home')} className="btn-secondary text-sm py-2">
              <Home size={14}/> Back to Home
            </button>
            <button onClick={() => navigate('/analysis')} className="btn-primary text-sm py-2">
              <Plus size={14}/> Start New Analysis
            </button>
          </div>
        </div>

        {/* Filter row */}
        <div className="card px-5 py-3 flex items-center justify-between mb-4">
          <div className="flex items-center gap-1">
            <span className="text-xs font-medium text-gray-500 text-gray-400 mr-2">Analysis type</span>
            {['All', 'Skin', 'Scalp'].map(t => (
              <button key={t} className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
                t === 'All'
                  ? 'bg-gray-900 bg-white text-white text-gray-900'
                  : 'text-gray-500 text-gray-400 bg-gray-100 bg-gray-800'
              }`}>{t}</button>
            ))}
          </div>
          <div className="flex items-center gap-1">
            <span className="text-xs font-medium text-gray-500 text-gray-400 mr-2">Sort by</span>
            {['Newest first', 'Oldest first'].map(s => (
              <button key={s} className={`px-4 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                s === 'Newest first'
                  ? 'border-gray-300 border-gray-600 text-gray-700 text-gray-200 bg-white bg-gray-800'
                  : 'border-transparent text-gray-400 bg-gray-100 bg-gray-800'
              }`}>{s}</button>
            ))}
          </div>
        </div>

        {/* Records list */}
        <div className="space-y-3">
          {records.map((rec, i) => (
            <div key={i} className="card px-5 py-4 flex items-center gap-4 shadow-md transition-shadow">
              {/* Image preview placeholder */}
              <div className="w-16 h-16 rounded-xl bg-gray-100 bg-gray-800 flex items-center justify-center shrink-0">
                <div className="text-center">
                  <p className="text-xs text-gray-400 text-gray-500 leading-tight">
                    {rec.type.includes('Scalp') ? 'Scalp' : 'Face'}<br/>image<br/>preview
                  </p>
                </div>
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900 text-white text-sm">{rec.type}</p>
                <p className="text-xs text-gray-400 text-gray-500 mt-0.5">{rec.condition}</p>
              </div>

              {/* Right: date + badge + link */}
              <div className="flex items-center gap-4 shrink-0">
                <span className="text-xs text-gray-400 text-gray-500 whitespace-nowrap">{rec.date}</span>
                <span className={rec.sClass}>{rec.severity}</span>
                <button onClick={() => navigate('/diagnosis')}
                  className="flex items-center gap-1 text-xs font-semibold text-blue-600 text-blue-700 whitespace-nowrap transition">
                  View full report <ArrowRight size={13}/>
                </button>
              </div>
            </div>
          ))}

          {/* Empty state card */}
          <div className="card px-6 py-8 text-center">
            <h3 className="font-bold text-gray-800 text-gray-100 mb-1">No analysis history available yet</h3>
            <p className="text-sm text-gray-400 text-gray-500 mb-5">
              Once you complete your first skin or scalp analysis, it will appear here for easy tracking and comparison over time.
            </p>
            <button onClick={() => navigate('/analysis')} className="btn-primary inline-flex mx-auto">
              <RefreshCw size={15}/> Start New Analysis
            </button>
          </div>
        </div>
      </main>

      <footer className="py-4 px-6 border-t border-gray-100 border-gray-800 flex items-center justify-between text-xs text-gray-400">
        <span>AI Beauty Assistant · Analysis History</span>
        <div className="flex gap-4">
          <button className="text-gray-600 transition">About Project</button>
          <button className="text-gray-600 transition">Contact / Support</button>
        </div>
      </footer>
    </div>
  );
}
