import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import './EditProfileModal.css';

const HEALTH_CONDITIONS = [
  { field: 'has_allergies',        label: 'Allergies' },
  { field: 'is_diabetic',          label: 'Diabetes' },
  { field: 'is_pregnant',          label: 'Pregnancy' },
  { field: 'has_cardio_issues',    label: 'Heart Condition' },
  { field: 'has_hypertension',     label: 'Hypertension' },
  { field: 'has_asthma',           label: 'Asthma' },
  { field: 'has_skin_conditions',  label: 'Skin Condition' },
  { field: 'has_scalp_conditions', label: 'Scalp Condition' },
];

export default function EditProfileModal({ isOpen, onClose, onSave, profileData }) {
  const user    = profileData?.user    || {};
  const med     = profileData?.medical_history || {};

  const [firstName,   setFirstName]   = useState('');
  const [lastName,    setLastName]    = useState('');
  const [medFields,   setMedFields]   = useState({});
  const [allergens,   setAllergens]   = useState('');
  const [medications, setMedications] = useState('');
  const [saving,      setSaving]      = useState(false);
  const [error,       setError]       = useState('');

  // Populate form whenever modal opens with latest profileData
  useEffect(() => {
    if (!isOpen) return;
    // Pre-fill from existing user data — supports either explicit
    // first_name/last_name fields, or a single `full_name` we split.
    let fn = user.first_name || '';
    let ln = user.last_name  || '';
    if (!fn && user.full_name) {
      const parts = user.full_name.trim().split(/\s+/);
      fn = parts[0] || '';
      ln = parts.slice(1).join(' ');
    }
    setFirstName(fn);
    setLastName(ln);
    setAllergens(med.known_allergens      || '');
    setMedications(med.current_medications || '');
    const initial = {};
    HEALTH_CONDITIONS.forEach(({ field }) => { initial[field] = med[field] || false; });
    setMedFields(initial);
    setError('');
  }, [isOpen, profileData]); // re-populate form when modal opens with fresh data

  const toggleCondition = (field) =>
    setMedFields(prev => ({ ...prev, [field]: !prev[field] }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await onSave({
        user:    {
          first_name: firstName,
          last_name: lastName,
          full_name: `${firstName} ${lastName}`.trim(),
        },
        medical_history: {
          ...medFields,
          known_allergens:     allergens,
          current_medications: medications,
        },
      });
      onClose();
    } catch {
      setError('Failed to save. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}
        style={{ maxWidth: 540, maxHeight: '90vh', overflowY: 'auto' }}>

        <div className="modal-header">
          <h2 className="modal-title">Edit Profile</h2>
          <button className="modal-close" onClick={onClose}><X size={20}/></button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">

          {/* Basic info */}
          <p className="modal-section-label">Basic Information</p>
          <div className="form-group">
            <label>First Name</label>
            <input type="text" value={firstName}
              onChange={e => setFirstName(e.target.value)} className="input-field" required/>
          </div>
          <div className="form-group">
            <label>Last Name</label>
            <input type="text" value={lastName}
              onChange={e => setLastName(e.target.value)} className="input-field"/>
          </div>
          <div className="form-group">
            <label>
              Email{' '}
              <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>(cannot be changed)</span>
            </label>
            <input type="email" value={user.email || ''} className="input-field"
              disabled style={{ opacity: 0.55, cursor: 'not-allowed' }}/>
          </div>

          {/* Health conditions */}
          <p className="modal-section-label" style={{ marginTop: '1.25rem' }}>Health Conditions</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
            {HEALTH_CONDITIONS.map(({ field, label }) => (
              <button key={field} type="button" onClick={() => toggleCondition(field)}
                style={{
                  padding: '0.35rem 0.85rem', borderRadius: '999px',
                  fontSize: '0.8rem', fontWeight: 500, cursor: 'pointer',
                  border: medFields[field] ? '2px solid var(--nav-accent)' : '2px solid var(--border-color)',
                  background: medFields[field] ? 'var(--blue-50)' : 'transparent',
                  color: medFields[field] ? 'var(--nav-accent)' : 'var(--text-secondary)',
                  transition: 'all 0.15s',
                }}>
                {label}
              </button>
            ))}
          </div>

          <div className="form-group">
            <label>
              Known allergens{' '}
              <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>(optional)</span>
            </label>
            <input type="text" value={allergens}
              onChange={e => setAllergens(e.target.value)}
              className="input-field" placeholder="e.g. peanuts, penicillin"/>
          </div>
          <div className="form-group">
            <label>
              Current medications{' '}
              <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>(optional)</span>
            </label>
            <input type="text" value={medications}
              onChange={e => setMedications(e.target.value)}
              className="input-field" placeholder="e.g. metformin, lisinopril"/>
          </div>

          {error && (
            <div style={{ color: '#ef4444', fontSize: '0.85rem', textAlign: 'center', marginBottom: '0.5rem' }}>
              {error}
            </div>
          )}

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}
