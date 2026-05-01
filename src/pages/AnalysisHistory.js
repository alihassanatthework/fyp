import { useNavigate } from 'react-router-dom';
import { useState, useMemo } from 'react';
import { Home, ArrowRight, Download, FileText, ArrowUpDown } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const records = [
  { type: 'Skin Analysis',  condition: 'Detected condition: Acne, mild redness',  date: '12 Mar 2025 · 09:24 AM', ts: new Date('2025-03-12T09:24').getTime(), severity: 'Mild',     sClass: 'badge-mild' },
  { type: 'Scalp Analysis', condition: 'Detected condition: Dandruff and dryness', date: '03 Mar 2025 · 06:15 PM', ts: new Date('2025-03-03T18:15').getTime(), severity: 'Moderate', sClass: 'badge-moderate' },
  { type: 'Skin Analysis',  condition: 'Detected condition: Pigmentation',         date: '18 Feb 2025 · 01:42 PM', ts: new Date('2025-02-18T13:42').getTime(), severity: 'Severe',   sClass: 'badge-severe' },
];

const TYPES = ['All', 'Skin', 'Scalp'];

export default function AnalysisHistory() {
  const navigate = useNavigate();
  const [activeType, setActiveType] = useState('All');
  const [sortDesc, setSortDesc] = useState(true);

  const filtered = useMemo(() => {
    let list = records.slice();
    if (activeType !== 'All') list = list.filter(r => r.type.toLowerCase().startsWith(activeType.toLowerCase()));
    list.sort((a, b) => sortDesc ? b.ts - a.ts : a.ts - b.ts);
    return list;
  }, [activeType, sortDesc]);

  const handleDownload = (rec) => {
    const blob = new Blob(
      [`Analysis Report\n\nType: ${rec.type}\nDate: ${rec.date}\n${rec.condition}\nSeverity: ${rec.severity}\n`],
      { type: 'text/plain' }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${rec.type.replace(/\s+/g, '_')}_${rec.date.split(' ')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title="Analysis History" subtitle="AI-Powered Skin & Scalp Assistant" />

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">

        {/* Page header */}
        <div className="flex items-start justify-between mb-7 flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900 text-white">Analysis History</h1>
            <p className="text-sm text-gray-400 text-gray-500 mt-0.5">Record of your previous skin and scalp analyses.</p>
          </div>
          <button onClick={() => navigate('/home')} className="btn-secondary text-sm py-2">
            <Home size={14}/> Home
          </button>
        </div>

        {/* Filter row — analysis type toggle + sort */}
        <div className="card px-5 py-3 flex items-center justify-between mb-4 flex-wrap gap-3">
          <div className="flex items-center gap-1">
            <span className="text-xs font-medium text-gray-500 text-gray-400 mr-2">Analysis type</span>
            {TYPES.map(t => (
              <button
                key={t}
                onClick={() => setActiveType(t)}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
                  activeType === t
                    ? 'bg-gray-900 bg-white text-white text-gray-900'
                    : 'text-gray-500 text-gray-400 bg-gray-100 bg-gray-800'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          <button
            onClick={() => setSortDesc(s => !s)}
            className="btn-secondary text-xs py-1.5"
            aria-label="Toggle sort order"
          >
            <ArrowUpDown size={13}/> Sort by: {sortDesc ? 'Newest first' : 'Oldest first'}
          </button>
        </div>

        {/* Records list */}
        <div className="space-y-3">
          {filtered.map((rec, i) => (
            <div key={i} className="card px-5 py-4 flex items-center gap-4 shadow-md transition-shadow flex-wrap">
              <div className="w-16 h-16 rounded-xl bg-gray-100 bg-gray-800 flex items-center justify-center shrink-0">
                <p className="text-xs text-gray-400 text-gray-500 leading-tight text-center">
                  {rec.type.includes('Scalp') ? 'Scalp' : 'Face'}<br/>preview
                </p>
              </div>

              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900 text-white text-sm">{rec.type}</p>
                <p className="text-xs text-gray-400 text-gray-500 mt-0.5">{rec.condition}</p>
                <p className="text-xs text-gray-400 text-gray-500 mt-1">{rec.date}</p>
              </div>

              <div className="flex items-center gap-2 shrink-0 flex-wrap">
                <span className={rec.sClass}>{rec.severity}</span>
                <button onClick={() => navigate('/diagnosis')} className="btn-secondary text-xs py-1.5">
                  <FileText size={13}/> Show Report
                </button>
                <button onClick={() => handleDownload(rec)} className="btn-secondary text-xs py-1.5">
                  <Download size={13}/> Download
                </button>
                <button onClick={() => navigate('/diagnosis')} className="text-xs font-semibold text-blue-600 text-blue-400 inline-flex items-center gap-1 px-2">
                  Details <ArrowRight size={13}/>
                </button>
              </div>
            </div>
          ))}

          {filtered.length === 0 && (
            <div className="card px-6 py-8 text-center">
              <h3 className="font-bold text-gray-800 text-gray-100 mb-1">No matching analyses</h3>
              <p className="text-sm text-gray-400 text-gray-500">
                Try a different analysis type filter.
              </p>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
