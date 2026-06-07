/**
 * CommandPalette
 * ──────────────
 * Linear/Raycast style universal search. Press ⌘K / Ctrl+K from anywhere
 * → fuzzy search across all dashboard commands and pages.
 *
 * No external dep — fuzzy match is a simple subsequence scoring function.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, ScanLine, Sparkles, Shirt, ClipboardList, Calendar, User,
  Sun, Moon, LogOut, History as HistoryIcon, Camera, Bell, ArrowRight,
} from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import './CommandPalette.css';

// Fuzzy subsequence score. Returns -1 if no match.
function score(query, label) {
  if (!query) return 0;
  const q = query.toLowerCase();
  const t = label.toLowerCase();
  let qi = 0, ti = 0, s = 0;
  while (qi < q.length && ti < t.length) {
    if (q[qi] === t[ti]) { s += 2; qi++; }
    else                 { s -= 0.05; }
    ti++;
  }
  if (qi < q.length) return -1;
  if (t.startsWith(q)) s += 4;
  if (t.includes(q))   s += 2;
  return s;
}

export default function CommandPalette({ open, onClose, onAction }) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { logout } = useAuth();
  const inputRef = useRef(null);
  const [q, setQ] = useState('');
  const [highlight, setHighlight] = useState(0);

  const commands = useMemo(() => [
    { id: 'scan-skin',   label: 'Start skin scan',        icon: <ScanLine size={14}/>,    run: () => navigate('/analysis?type=skin')  },
    { id: 'scan-scalp',  label: 'Start scalp scan',       icon: <ScanLine size={14}/>,    run: () => navigate('/analysis?type=scalp') },
    { id: 'mirror',      label: 'Open AI Mirror Mode',    icon: <Camera size={14}/>,      run: () => onAction?.('mirror')             },
    { id: 'wrapped',     label: 'Open Skin Wrapped',      icon: <Sparkles size={14}/>,    run: () => onAction?.('wrapped')            },
    { id: 'makeup',      label: 'Makeup assistance',      icon: <Sparkles size={14}/>,    run: () => navigate('/makeup-assistance')   },
    { id: 'fashion',     label: 'Fashion assistance',     icon: <Shirt size={14}/>,       run: () => navigate('/fashion-assistance')  },
    { id: 'history',     label: 'Analysis history',       icon: <HistoryIcon size={14}/>, run: () => navigate('/analysis-history')    },
    { id: 'reports',     label: 'Diagnosis reports',      icon: <ClipboardList size={14}/>,run: () => navigate('/analysis-history')   },
    { id: 'book-derma',  label: 'Find a dermatologist',   icon: <Calendar size={14}/>,    run: () => navigate('/bookings?type=dermatologist') },
    { id: 'book-salon',  label: 'Find a salon',           icon: <Calendar size={14}/>,    run: () => navigate('/bookings?type=salon') },
    { id: 'profile',     label: 'Open profile',           icon: <User size={14}/>,        run: () => navigate('/profile')             },
    { id: 'theme',       label: `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`,
                         icon: theme === 'dark' ? <Sun size={14}/> : <Moon size={14}/>,
                         run: () => toggleTheme(theme === 'dark' ? 'light' : 'dark') },
    { id: 'remind',      label: 'Set a reminder',         icon: <Bell size={14}/>,        run: () => onAction?.('reminder')           },
    { id: 'logout',      label: 'Log out',                icon: <LogOut size={14}/>,      run: () => { logout(); navigate('/'); }      },
  ], [navigate, theme, toggleTheme, logout, onAction]);

  const filtered = useMemo(() => {
    if (!q) return commands;
    return commands
      .map((c) => ({ ...c, _s: score(q, c.label) }))
      .filter((c) => c._s >= 0)
      .sort((a, b) => b._s - a._s);
  }, [q, commands]);

  useEffect(() => {
    if (!open) { setQ(''); setHighlight(0); return; }
    const t = setTimeout(() => inputRef.current?.focus(), 30);
    return () => clearTimeout(t);
  }, [open]);

  useEffect(() => { setHighlight(0); }, [q]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowDown' || (e.key === 'Tab' && !e.shiftKey)) {
        e.preventDefault();
        setHighlight((h) => Math.min(filtered.length - 1, h + 1));
      }
      if (e.key === 'ArrowUp' || (e.key === 'Tab' && e.shiftKey)) {
        e.preventDefault();
        setHighlight((h) => Math.max(0, h - 1));
      }
      if (e.key === 'Home') {
        e.preventDefault();
        setHighlight(0);
      }
      if (e.key === 'End') {
        e.preventDefault();
        setHighlight(Math.max(0, filtered.length - 1));
      }
      if (e.key === 'Enter') {
        const c = filtered[highlight];
        if (c) { onClose(); c.run(); }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, filtered, highlight, onClose]);

  if (!open) return null;

  return (
    <div className="cp-overlay" onClick={onClose}>
      <div className="cp-shell" onClick={(e) => e.stopPropagation()}>
        <div className="cp-input-row">
          <Search size={16}/>
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Type a command or search…"
            className="cp-input"
          />
          <kbd className="cp-esc">esc</kbd>
        </div>

        <div className="cp-list" role="listbox">
          {filtered.length === 0 && (
            <div className="cp-empty">No matches.</div>
          )}
          {filtered.map((c, i) => (
            <button
              key={c.id}
              className={`cp-item ${i === highlight ? 'highlight' : ''}`}
              onClick={() => { onClose(); c.run(); }}
              onMouseEnter={() => setHighlight(i)}
            >
              <span className="cp-item-icon">{c.icon}</span>
              <span className="cp-item-label">{c.label}</span>
              <ArrowRight size={12} className="cp-item-arrow"/>
            </button>
          ))}
        </div>

        <div className="cp-footer">
          <span><kbd>↑</kbd><kbd>↓</kbd> to navigate</span>
          <span><kbd>↵</kbd> to select</span>
          <span><kbd>esc</kbd> to close</span>
        </div>
      </div>
    </div>
  );
}
