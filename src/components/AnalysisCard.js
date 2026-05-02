import { Droplets, Wind } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './AnalysisCard.css';

const VARIANTS = {
  skin: {
    icon: <Droplets size={26} />,
    title: 'Skin Analysis',
    desc: 'Upload a face image. AI detects skin conditions, texture, and pigmentation.',
    bullets: ['Acne, redness', 'Pigmentation', 'Texture insights'],
    cta: 'Start Skin Analysis',
    to: '/analysis?type=skin',
    accent: 'skin',
  },
  scalp: {
    icon: <Wind size={26} />,
    title: 'Scalp Analysis',
    desc: 'Upload a scalp image. AI detects dandruff, dryness, and density issues.',
    bullets: ['Dandruff, flakes', 'Dryness', 'Hair density'],
    cta: 'Start Scalp Analysis',
    to: '/analysis?type=scalp',
    accent: 'scalp',
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
      <div className="analysis-card-icon">{v.icon}</div>
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
