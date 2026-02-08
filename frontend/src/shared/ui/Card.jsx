export default function Card({ title, description, children, className = "" }) {
  return (
    <section className={`card ${className}`.trim()}>
      {title ? <h2 className="card-title">{title}</h2> : null}
      {description ? <p className="card-description">{description}</p> : null}
      {children}
    </section>
  );
}
