export default function TextField({ label, error, ...props }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <input className={`field-input ${error ? "field-input-error" : ""}`.trim()} {...props} />
      {error ? <span className="field-error">{error}</span> : null}
    </label>
  );
}
