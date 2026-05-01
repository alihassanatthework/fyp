import { Scissors } from 'lucide-react';
import StaticPage from '../components/StaticPage';

export default function ScalpTreatment() {
  return (
    <StaticPage
      title="Scalp Treatment"
      subtitle="General guidance for common scalp concerns."
      icon={<Scissors size={20} />}
    >
      <h2>Healthy scalp basics</h2>
      <ul>
        <li>Wash regularly enough to control oil — typically every 2–3 days.</li>
        <li>Use a sulphate-free shampoo if your scalp is sensitive or dry.</li>
        <li>Massage gently while shampooing to support circulation.</li>
      </ul>

      <h2>Common conditions</h2>
      <h2 style={{ fontSize: '0.95rem' }}>Dandruff</h2>
      <p>Anti-fungal shampoos with zinc pyrithione, ketoconazole, or selenium sulphide are first-line.</p>

      <h2 style={{ fontSize: '0.95rem' }}>Dryness &amp; flaking</h2>
      <p>Hydrate with leave-in conditioners and reduce heat-styling frequency.</p>

      <h2 style={{ fontSize: '0.95rem' }}>Hair density loss</h2>
      <p>Look for clinically supported topicals (e.g., minoxidil) and rule out thyroid or iron issues with your doctor.</p>

      <h2>When to see a specialist</h2>
      <ul>
        <li>Sudden hair loss, bald patches, or scarring.</li>
        <li>Severe itching, redness, or signs of infection.</li>
        <li>Persistent flaking unresponsive to anti-dandruff shampoos.</li>
      </ul>

      <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>
        Educational guidance only — not a substitute for medical advice.
      </p>
    </StaticPage>
  );
}
