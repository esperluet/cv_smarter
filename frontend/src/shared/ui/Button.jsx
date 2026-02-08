export default function Button({ children, type = "button", variant = "primary", ...props }) {
  return (
    <button type={type} className={`btn btn-${variant}`} {...props}>
      {children}
    </button>
  );
}
