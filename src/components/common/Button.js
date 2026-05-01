// src/components/common/Button.js
// Reusable Button Component

import './Button.css';

export default function Button({
  children,
  variant = 'primary', // primary, secondary, outline, danger
  size = 'medium', // small, medium, large
  fullWidth = false,
  loading = false,
  disabled = false,
  onClick,
  type = 'button',
  className = '',
  ...props
}) {
  const classes = [
    'btn',
    `btn-${variant}`,
    `btn-${size}`,
    fullWidth && 'btn-full-width',
    loading && 'btn-loading',
    disabled && 'btn-disabled',
    className
  ].filter(Boolean).join(' ');

  return (
    <button
      type={type}
      className={classes}
      onClick={onClick}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="btn-loader">Loading...</span>
      ) : (
        children
      )}
    </button>
  );
}
