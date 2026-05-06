import { useNavigate, useLocation } from 'react-router-dom';
import { Download, Bookmark, Bell, ArrowRight, CheckCircle2, ShieldCheck } from 'lucide-react';
import Navbar from '../components/Navbar';
import './DiagnosisReport.css';

const steps = [
  { title: 'Consult a certified dermatologist', desc: 'Schedule an in-person or telehealth visit within 7 days.' },
  { title: 'Topical treatment options', desc: 'Discuss retinoids or benzoyl peroxide-based treatments if appropriate.' },
  { title: 'Daily skincare routine', desc: 'Use a gentle, non-comedogenic cleanser and avoid harsh scrubbing.' },
  { title: 'Follow-up scan', desc: 'Re-scan in 4–6 weeks to track your skin health progress.' },
];

export default function DiagnosisReport() {
  const navigate = useNavigate();
  const location = useLocation();

  const payload = location.state?.data;

  // Backend returns either `context` directly or `{success,data}` wrapper.
  let report = payload?.data ? payload.data : payload;

  // Fallback: if user refreshes the diagnosis page, use last analysis cached in localStorage.
  if (!report) {
    try {
      const cached = localStorage.getItem('lastAnalysis');
      if (cached) {
        const parsed = JSON.parse(cached);
        report = parsed?.data ? parsed.data : parsed;
      }
    } catch (e) {}
  }

  const conditions = report?.conditions || [];
  const recommendations = report?.recommendations || [];

  const primary = conditions[0] || {
    name: 'Normal',
    severity_level: 'Unknown',
    severity_score: 0,
  };

  const scorePct = Math.max(0, Math.min(100, Number(primary.severity_score) || 0));

  if (!report) {
    return (
      <div className="diagnosis-page">
        <Navbar title="Diagnosis Report" />
        <main className="diagnosis-main">
          <div className="card p-6">
            <h1 className="diagnosis-page-title">No report data found</h1>
            <p className="diagnosis-page-subtitle" style={{ marginTop: 8 }}>
              Please run an analysis first.
            </p>
            <button className="btn btn-primary w-full py-3" onClick={() => navigate('/analysis')}>
              Start Analysis
            </button>
          </div>
        </main>
      </div>
    );
  }

  const analysisId = report.analysis_id || '—';
  const analysisType = report.analysis_type || 'skin';
  const analysisTypeLower = String(analysisType || 'skin').toLowerCase();
  const originalImage = report.original_image || '';
  const visualizedImage = report.visualized_image || '';
  const efficientnetVisualization = report.efficientnet_visualization || '';
  const yoloChart = report.yolo_chart || '';
  const yoloVisualization = report.yolo_visualization || '';

  return (
    <div className="diagnosis-page">
      <Navbar title="Diagnosis Report" />
      <main className="diagnosis-main">
        <div>
          <h1 className="diagnosis-page-title">Diagnosis Report & Actions</h1>
          <p className="diagnosis-page-subtitle">Complete analysis results with actionable next steps.</p>
        </div>
        <div className="card diagnosis-meta-grid">
          <div className="meta-item">
            <p className="meta-label">REPORT NAME</p>
            <p className="meta-value">
              {analysisType === 'scalp' ? 'Scalp Analysis' : 'Facial Skin Analysis'} #{analysisId}
            </p>
          </div>
          <div className="meta-item">
            <p className="meta-label">DATE & TIME</p>
            <p className="meta-value">—</p>
          </div>
          <div className="meta-item">
            <p className="meta-label">REPORT ID</p>
            <p className="meta-value">{analysisId}</p>
          </div>
        </div>
        <div className="diagnosis-grid">
          <div className="card p-6">
            <div className="condition-header">
              <ShieldCheck size={18} className="condition-header-icon"/>
              <h2 className="condition-header-title">Detected Condition</h2>
            </div>
            <div className="flex items-start gap-4 mb-4">
              <div className="condition-icon-badge">
                <span className="condition-icon-text">!</span>
              </div>
              <div className="condition-info">
                <h2 className="condition-name">{primary.name}</h2>
                <p className="condition-confidence">Confidence: {scorePct}%</p>
              </div>
            </div>
            {conditions.length > 1 && (
              <div style={{ marginTop: 12 }}>
                <p className="condition-description" style={{ marginBottom: 8 }}>
                  Also detected:
                </p>
                <div className="space-y-2">
                  {conditions.slice(1, 4).map((c, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                      <span className="text-sm" style={{ color: 'var(--text-primary)' }}>
                        {c.name}
                      </span>
                      <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
                        {c.severity_score}/100
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="severity-box">
              <div className="severity-header">
                <span className="severity-label">
                  Severity Level: <span className="severity-level">{primary.severity_level}</span>
                </span>
                <span className="severity-score">{scorePct}/100</span>
              </div>
              <div className="severity-bar">
                <div className="severity-bar-fill" style={{ width: `${scorePct}%` }} />
              </div>
              <div className="severity-range">
                <span>Mild</span><span>Severe</span>
              </div>
            </div>
          </div>
          <div className="card book-card p-6">
            <div>
              <h2 className="book-title">Ready to treat this?</h2>
              <p className="book-desc">Book a consultation with a specialist.</p>
              <button className="btn btn-primary w-full py-3">Book Appointment <ArrowRight size={15}/></button>
            </div>
            <div className="book-footer">
              <ShieldCheck size={14}/>Securely verified report
            </div>
          </div>
        </div>
        <div className="diagnosis-grid">
          <div className="card p-6">
            <div className="recommendation-header">
              <span className="recommendation-emoji">🩺</span>
              <h2 className="condition-header-title">Dermatologist Recommendation</h2>
            </div>
            {recommendations.length > 0 ? (
              <ul className="recommendation-text" style={{ marginTop: 10 }}>
                {recommendations.slice(0, 5).map((r, idx) => (
                  <li key={idx} style={{ marginBottom: 8 }}>
                    {r}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="recommendation-text">
                Based on the analysis of the affected areas, consulting a certified dermatologist is recommended to assess underlying causes.
              </p>
            )}
            <div className="disclaimer-box">
              <p className="disclaimer-text">
                <span className="disclaimer-label">Medical Disclaimer:</span> This report is AI-generated for informational purposes only and does not constitute a medical diagnosis. Always seek the advice of a physician or other qualified health provider.
              </p>
            </div>
          </div>
          <div className="card p-6">
            <div className="recommendation-header">
              <span className="recommendation-emoji">📋</span>
              <h2 className="condition-header-title">Suggested Next Steps</h2>
            </div>
            <ul className="steps-list">
              {steps.map((s, i) => (
                <li key={i} className="step-item">
                  <CheckCircle2 size={16} className="step-icon"/>
                  <div>
                    <p className="step-title">{s.title}</p>
                    <p className="step-desc">{s.desc}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {(visualizedImage || originalImage) && (
          <div className="card p-6" style={{ marginTop: 16 }}>
            <h2 className="condition-header-title" style={{ marginBottom: 12 }}>Analysis Images</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
              {originalImage ? (
                <div>
                  <p className="text-sm" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>Original</p>
                  <img src={originalImage} alt="Original upload" style={{ width: '100%', borderRadius: 12 }} />
                </div>
              ) : null}
              {visualizedImage ? (
                <div>
                  <p className="text-sm" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>Overlay</p>
                  <img src={visualizedImage} alt="Overlay visualization" style={{ width: '100%', borderRadius: 12 }} />
                </div>
              ) : null}
            </div>
          </div>
        )}

        {((analysisTypeLower === 'skin' && efficientnetVisualization) ||
          (analysisTypeLower === 'scalp' && (yoloChart || yoloVisualization))) && (
          <div className="card p-6" style={{ marginTop: 16 }}>
            <h2 className="condition-header-title" style={{ marginBottom: 12 }}>AI Charts</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
              {analysisTypeLower === 'skin' && efficientnetVisualization ? (
                <div>
                  <p className="text-sm" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>EfficientNet Scores</p>
                  <img src={efficientnetVisualization} alt="EfficientNet scores chart" style={{ width: '100%', borderRadius: 12 }} />
                </div>
              ) : null}
              {analysisTypeLower === 'scalp' && yoloChart ? (
                <div>
                  <p className="text-sm" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>YOLO Detections Chart</p>
                  <img src={yoloChart} alt="YOLO detections chart" style={{ width: '100%', borderRadius: 12 }} />
                </div>
              ) : null}
              {analysisTypeLower === 'scalp' && yoloVisualization && !yoloChart ? (
                <div style={{ gridColumn: '1 / -1' }}>
                  <p className="text-sm" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>YOLO Visualization</p>
                  <img src={yoloVisualization} alt="YOLO visualization" style={{ width: '100%', borderRadius: 12 }} />
                </div>
              ) : null}
            </div>
          </div>
        )}
        <div className="card footer-bar">
          <div className="footer-info">
            <span className="footer-emoji">🗄️</span>
            <div>
              <p className="footer-info-title">Data auto-saved</p>
              <p className="footer-info-desc">This report is securely stored and can be accessed in your history.</p>
            </div>
          </div>
          <div className="footer-actions">
            <button className="btn btn-secondary"><Download size={14}/> Download PDF</button>
            <button className="btn btn-secondary"><Bookmark size={14}/> Save Scan</button>
            <button className="btn btn-secondary"><Bell size={14}/> Set Reminder</button>
          </div>
        </div>
        <p className="footer-note">Regular monitoring helps track your skin health progress over time.</p>
      </main>
    </div>
  );
}