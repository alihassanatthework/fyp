/**
 * SkinCopilot
 * ───────────
 * Conversational hero card that greets the user with a template-driven AI
 * voice and surfaces context-aware quick actions. No LLM call — message
 * + chips are picked from the user's stats so the AI feels alive without
 * a network round-trip.
 *
 * Adapts to:
 *   • no scans yet            → "let's start your first scan"
 *   • severe condition flag   → red alert, prompt to book derma
 *   • last scan ≥ 30 days     → time-to-rescan nudge
 *   • generally healthy       → upbeat trend message
 *   • time of day             → "Good morning / afternoon / evening"
 */
import { Sparkles, ArrowRight, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './SkinCopilot.css';

function greetingPrefix() {
  const h = new Date().getHours();
  if (h < 5)  return 'Late night';
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  if (h < 22) return 'Good evening';
  return 'Hi night owl';
}

function buildMessage(stats, firstName) {
  const prefix = greetingPrefix();
  const name   = firstName || 'there';
  const total  = stats?.total_scans ?? 0;
  const severe = stats?.severity_counts?.Severe ?? 0;
  const trend  = stats?.health_trend ?? 0;
  const score  = stats?.health_score ?? null;
  const lastDate = stats?.last_scan_date;
  const daysSince = stats?.recent_scans?.[0]?.date
    ? Math.floor((Date.now() - new Date(stats.recent_scans[0].date)) / 86400000)
    : null;
  const top = stats?.recurring_conditions?.[0]?.name;

  if (total === 0) {
    return {
      tone: 'invite',
      text: `${prefix}, ${name} — let's start with your first scan.`,
      chips: [
        { label: 'Start skin scan',  to: '/analysis?type=skin'  },
        { label: 'Start scalp scan', to: '/analysis?type=scalp' },
      ],
    };
  }
  if (severe >= 3) {
    return {
      tone: 'alert',
      text: `${prefix}, ${name}. You have ${severe} severe finding${severe>1?'s':''} — consider booking a dermatologist this week.`,
      chips: [
        { label: 'Find a dermatologist', to: '/bookings?type=dermatologist' },
        { label: 'View severe scans',    to: '/analysis-history' },
      ],
    };
  }
  if (daysSince !== null && daysSince >= 14) {
    return {
      tone: 'nudge',
      text: `${prefix}, ${name} — it's been ${daysSince} days since your last scan. Quick re-check?`,
      chips: [
        { label: 'Run a quick scan', to: '/analysis' },
        { label: 'Open AI Mirror',   action: 'mirror' },
      ],
    };
  }
  if (trend >= 5 && score !== null) {
    return {
      tone: 'happy',
      text: `${prefix}, ${name}. Your skin health is up ${trend} points this month — keep going. ✨`,
      chips: [
        { label: 'See timeline',        action: 'time' },
        { label: 'Want a routine tip?', action: 'tip'  },
      ],
    };
  }
  if (trend <= -5) {
    return {
      tone: 'concern',
      text: `${prefix}, ${name}. Your score dropped ${Math.abs(trend)} points recently. Want a deeper look?`,
      chips: [
        { label: 'Open constellation', action: 'time' },
        { label: 'Book a check-up',    to: '/bookings?type=dermatologist' },
      ],
    };
  }
  if (top) {
    return {
      tone: 'info',
      text: `${prefix}, ${name}. Your most-tracked concern is ${top}. Want to drill in?`,
      chips: [
        { label: `View ${top} history`, to: '/analysis-history' },
        { label: 'Start a new scan',    to: '/analysis' },
      ],
    };
  }
  return {
    tone: 'info',
    text: `${prefix}, ${name}. Last scan ${lastDate || 'recently'} — looking steady.`,
    chips: [
      { label: 'New scan',   to: '/analysis' },
      { label: 'AI Mirror',  action: 'mirror' },
    ],
  };
}

export default function SkinCopilot({ stats, firstName, onAction }) {
  const navigate = useNavigate();
  const msg = buildMessage(stats, firstName);

  const handleChip = (chip) => {
    if (chip.to) navigate(chip.to);
    else if (chip.action && onAction) onAction(chip.action);
  };

  return (
    <div className={`skin-copilot tone-${msg.tone}`}>
      <div className="skin-copilot-avatar" aria-hidden="true">
        {msg.tone === 'alert' ? <AlertTriangle size={20}/> : <Sparkles size={20}/>}
      </div>
      <div className="skin-copilot-body">
        <p className="skin-copilot-label">AI Skin Copilot</p>
        <p className="skin-copilot-text">{msg.text}</p>
        <div className="skin-copilot-chips">
          {msg.chips.map((chip, i) => (
            <button
              key={i}
              className="skin-copilot-chip"
              onClick={() => handleChip(chip)}
            >
              {chip.label} <ArrowRight size={12}/>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
