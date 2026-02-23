import { useState } from 'react';
import { Heart, Download, Calendar } from 'lucide-react';
import Navbar from '../components/Navbar';
import './History.css';

const scans = [
  { date: 'Oct 26, 2023, 10:30 AM', type: 'Skin Scan', name: 'Acne Vulgaris', severity: 'Moderate', severityClass: 'badge-moderate' },
  { date: 'Oct 20, 2023, 02:15 PM', type: 'Scalp Scan', name: 'Dandruff (Seborrheic Dermatitis)', severity: 'Mild', severityClass: 'badge-mild' },
  { date: 'Sep 15, 2023, 09:00 AM', type: 'Skin Scan', name: 'Eczema (Atopic Dermatitis)', severity: 'Severe', severityClass: 'badge-severe' },
  { date: 'Aug 01, 2023, 11:45 AM', type: 'Skin Scan', name: 'Psoriasis Lesion', severity: 'Moderate', severityClass: 'badge-moderate' },
  { date: 'Jul 28, 2023, 03:00 PM', type: 'Scalp Scan', name: 'Folliculitis', severity: 'Mild', severityClass: 'badge-mild' },
  { date: 'Jun 10, 2023, 08:30 AM', type: 'Skin Scan', name: 'Rosacea', severity: 'Severe', severityClass: 'badge-severe' },
];

export default function History() {
  const [liked, setLiked] = useState({});
  const [scanType, setScanType] = useState('All Types');
  const [severity, setSeverity] = useState('All Severities');
  const toggleLike = (i) => setLiked(prev => ({ ...prev, [i]: !prev[i] }));
  const filtered = scans.filter(s => {
    const typeMatch = scanType === 'All Types' || s.type === scanType;
    const sevMatch = severity === 'All Severities' || s.severity === severity;
    return typeMatch && sevMatch;
  });

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
              <p className="text-sm" style={{color: 'var(--text-tertiary)', marginTop: '0.25rem'}}>Your past health scans at a glance, filtered by your preferences.</p>
            </div>
            <div className="scan-cards-grid">
              {filtered.map((scan, i) => (
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
                    <button className="btn btn-secondary">View Details</button>
                    <button className="btn btn-secondary"><Download size={12}/> Report</button>
                  </div>
                </div>
              ))}
            </div>
            {filtered.length === 0 && (
              <div className="text-center" style={{padding: '4rem 0', color: 'var(--text-tertiary)'}}>
                <p className="text-sm">No scans match your filters.</p>
              </div>
            )}
          </div>
        </div>
      </main>
      <footer className="history-footer">
        <p>Made with ❤️ AI Beauty Assistant</p>
      </footer>
    </div>
  );
}