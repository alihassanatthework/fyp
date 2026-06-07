import { Droplets, Wind } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './AnalysisCard.css';

const VARIANTS = {
  skin: {
    icon: <Droplets size={28} />,
    title: 'Skin Analysis',
    desc: 'Upload a face image. AI detects skin conditions, texture, and pigmentation.',
    bullets: ['Acne, redness & inflammation', 'Pigmentation & dark spots', 'Skin texture insights'],
    cta: 'Start Skin Analysis',
    to: '/analysis?type=skin',
    accent: 'skin',
    grad: 'linear-gradient(135deg, #f472b6, #fb7185)',
    dotColors: ['#f472b6', '#fb7185', '#fda4af'],
  },
  scalp: {
    icon: <Wind size={28} />,
    title: 'Scalp Analysis',
    desc: 'Upload a scalp image. AI detects dandruff, dryness, and density issues.',
    bullets: ['Dandruff & flake detection', 'Scalp dryness & oiliness', 'Hair density analysis'],
    cta: 'Start Scalp Analysis',
    to: '/analysis?type=scalp',
    accent: 'scalp',
    grad: 'linear-gradient(135deg, #38bdf8, #818cf8)',
    dotColors: ['#38bdf8', '#818cf8', '#6366f1'],
  },
};

export default function AnalysisCard({ type = 'skin', onClick }) {
  const navigate = useNavigate();
  const v = VARIANTS[type] || VARIANTS.skin;

  const handleClick = () => {
    if (onClick) onClick();
    else navigate(v.to);
  };

  return (
    <div className={`analysis-card analysis-card--${v.accent}`}>
      <div className="analysis-card-illustration">
        <div className="aci-ring aci-ring-1"/>
        <div className="aci-ring aci-ring-2"/>
        <div className="aci-icon-wrap" style={{ background: v.grad }}>{v.icon}</div>
        <div className="aci-dot aci-dot-1" style={{ background: v.dotColors[0] }}/>
        <div className="aci-dot aci-dot-2" style={{ background: v.dotColors[1] }}/>
        <div className="aci-dot aci-dot-3" style={{ background: v.dotColors[2] }}/>
      </div>
      <h3 className="analysis-card-title">{v.title}</h3>
      <p className="analysis-card-desc">{v.desc}</p>
      <ul className="analysis-card-bullets">
        {v.bullets.map((b) => (
          <li key={b}>{b}</li>
        ))}
      </ul>
      <button onClick={handleClick} className="analysis-card-btn">
        {v.cta}
      </button>
    </div>
  );
}
