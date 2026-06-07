import { useState, useEffect } from 'react';
import { Heart, Download, Calendar } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { useAnalysis } from '../hooks/useAnalysis';
import { analysisService } from '../services/analysisService';
import './History.css';

export default function History() {
  const navigate = useNavigate();
  const [liked, setLiked] = useState({});
  const [scanType, setScanType] = useState('All Types');
  const [severity, setSeverity] = useState('All Severities');
  const [scans, setScans] = useState([]);
  const [openingId, setOpeningId] = useState(null);

  const { getHistory, loading } = useAnalysis();

  useEffect(() => {
    const loadHistory = async () => {
      const result = await getHistory({ type: scanType, severity });
      if (result.success) {
        // history endpoint may be paginated → { count, results } or a bare array
        const list = Array.isArray(result.data)
          ? result.data
          : (result.data?.results || []);
        setScans(list);
      }
    };
    loadHistory();
  }, [scanType, severity]);

  // View Details — fetch the full pipeline payload then navigate to /diagnosis.
  const handleViewDetails = async (scan) => {
    if (!scan.id) return;
    try {
      setOpeningId(scan.id);
      const full = await analysisService.getAnalysisById(scan.id);
      navigate('/diagnosis', { state: { data: full } });
    } catch {
      navigate('/diagnosis', { state: { data: scan } });
    } finally {
      setOpeningId(null);
    }
  };

  // Download a tiny .txt summary so the button does something useful.
  const handleDownload = (scan) => {
    const blob = new Blob(
      [`Scan Report\n\nType: ${scan.type}\nDate: ${scan.date}\nCondition: ${scan.name}\nSeverity: ${scan.severity}\n`],
      { type: 'text/plain' },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(scan.name || 'scan').replace(/\s+/g, '_')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const toggleLike = (i) => setLiked(prev => ({ ...prev, [i]: !prev[i] }));

  return (
    <div className="history-page">
      <Navbar title="Health Scan History" />
      <main className="history-main">
        <div className="history-header">
          <div className="history-icon-box">
            <Heart size={18} style={{fill: 'white'}}/>
          </div>
          <h1 className="history-title">Health Scan History</h1>
        </div>
        <div className="history-grid">
          <div className="history-filters">
            <div><p className="section-label">Filters</p></div>
            <div className="filter-group">
              <label>Date Range</label>
              <div style={{position: 'relative'}}>
                <Calendar size={14} className="filter-icon"/>
                <input type="date" className="input-field" style={{paddingLeft: '2rem'}}/>
              </div>
            </div>
            <div className="filter-group">
              <label>Scan Type</label>
              <select value={scanType} onChange={e => setScanType(e.target.value)} className="input-field">
                <option>All Types</option>
                <option>Skin Scan</option>
                <option>Scalp Scan</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Severity</label>
              <select value={severity} onChange={e => setSeverity(e.target.value)} className="input-field">
                <option>All Severities</option>
                <option>Mild</option>
                <option>Moderate</option>
                <option>Severe</option>
              </select>
            </div>
            <button className="btn btn-primary w-full">Apply Filters</button>
          </div>

          <div>
            <div className="mb-5">
              <h2 className="text-xl font-bold">Scan History</h2>
              <p className="text-sm" style={{color: 'var(--text-tertiary)', marginTop: '0.25rem'}}>
                Your past health scans at a glance, filtered by your preferences.
              </p>
            </div>

            {loading && (
              <div className="text-center" style={{padding: '4rem 0', color: 'var(--text-tertiary)'}}>
                <p className="text-sm">Loading scans...</p>
              </div>
            )}

            {!loading && (
              <div className="scan-cards-grid">
                {scans.map((scan, i) => (
                  <div key={i} className="card scan-card">
                    <div className="scan-card-header">
                      <p className="scan-date">{scan.date}</p>
                      <button onClick={() => toggleLike(i)} className={`like-btn ${liked[i] ? 'liked' : ''}`}>
                        <Heart size={16} style={liked[i] ? {fill: 'currentColor'} : {}}/>
                      </button>
                    </div>
                    <p className="scan-type"><Heart size={11}/> {scan.type}</p>
                    <h3 className="scan-name">{scan.name}</h3>
                    <span className={`badge ${scan.severityClass}`}>{scan.severity}</span>
                    <div className="scan-card-actions">
                      <button
                        className="btn btn-secondary"
                        onClick={() => handleViewDetails(scan)}
                        disabled={openingId === scan.id}
                      >
                        {openingId === scan.id ? 'Loading…' : 'View Details'}
                      </button>
                      <button
                        className="btn btn-secondary"
                        onClick={() => handleDownload(scan)}
                      >
                        <Download size={12}/> Report
                      </button>
                    </div>
                  </div>
                ))}

                {scans.length === 0 && (
                  <div className="text-center" style={{padding: '4rem 0', color: 'var(--text-tertiary)'}}>
                    <p className="text-sm">No scans match your filters.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}