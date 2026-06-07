import { Smile } from 'lucide-react';
import StaticPage from '../components/StaticPage';

export default function SkinTreatment() {
  return (
    <StaticPage
      title="Skin Treatment"
      subtitle="General guidance for common skin concerns."
      icon={<Smile size={20} />}
    >
      <h2>Daily routine</h2>
      <ul>
        <li>Cleanse with a gentle, non-comedogenic cleanser, morning and night.</li>
        <li>Moisturise daily — even oily skin benefits from hydration.</li>
        <li>Apply a broad-spectrum SPF 30+ every morning.</li>
      </ul>

      <h2>Common conditions</h2>
      <h2 style={{ fontSize: '0.95rem' }}>Acne</h2>
      <p>Look for ingredients like salicylic acid or benzoyl peroxide. Avoid harsh scrubbing — it inflames skin.</p>

      <h2 style={{ fontSize: '0.95rem' }}>Pigmentation</h2>
      <p>Vitamin C serums and consistent SPF are foundational. Persistent dark spots warrant a dermatologist visit.</p>

      <h2 style={{ fontSize: '0.95rem' }}>Dryness</h2>
      <p>Layer hydrating serums (hyaluronic acid) under a richer moisturiser. Limit hot water exposure.</p>

      <h2>When to see a dermatologist</h2>
      <ul>
        <li>Persistent or worsening symptoms despite routine adjustments.</li>
        <li>Severe inflammation, scarring, or sudden changes in moles.</li>
        <li>Allergic reactions or chronic conditions like eczema or rosacea.</li>
      </ul>

      <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>
        Educational guidance only — not a substitute for medical advice.
      </p>
    </StaticPage>
  );
}
