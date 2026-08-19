import { MapPin, Mail, Phone, Briefcase, Star } from "lucide-react";
import { useDrawer } from "../contexts/DrawerContext";

function getInitials(name) {
  if (!name) return "?";
  return name
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0]?.toUpperCase() ?? "")
    .join("");
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value ?? 0) * 100);
  const color =
    pct >= 80 ? "var(--clr-success)"
    : pct >= 50 ? "var(--clr-warning)"
    : "var(--clr-danger)";
  return (
    <div className="confidence-bar-wrap">
      <div className="confidence-bar-label">
        <span>Confidence</span>
        <span style={{ color }}>{pct}%</span>
      </div>
      <div className="confidence-bar-track">
        <div
          className="confidence-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

export default function CandidateCard({ candidate }) {
  const { openDrawer } = useDrawer();
  const {
    full_name,
    headline,
    emails = [],
    phones = [],
    location,
    skills = [],
    overall_confidence,
    llm_enriched,
    years_experience,
  } = candidate;

  const loc = location
    ? [location.city, location.region, location.country].filter(Boolean).join(", ")
    : null;

  const visibleSkills = skills.slice(0, 4);
  const extraSkills   = skills.length - 4;

  return (
    <div
      id={`candidate-card-${candidate.candidate_id}`}
      className="card candidate-card card-clickable"
      onClick={() => openDrawer(candidate)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && openDrawer(candidate)}
      aria-label={`View profile for ${full_name}`}
    >
      {/* Header */}
      <div className="candidate-card-header">
        <div className="avatar">{getInitials(full_name)}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="candidate-name">{full_name || "Unknown"}</div>
          <div className="candidate-headline">{headline || "No headline"}</div>
          {llm_enriched && (
            <span className="llm-badge">
              <Star size={10} /> AI Enriched
            </span>
          )}
        </div>
      </div>

      {/* Meta chips */}
      <div className="candidate-meta">
        {emails[0] && (
          <span className="meta-chip">
            <Mail /> {emails[0]}
          </span>
        )}
        {phones[0] && (
          <span className="meta-chip">
            <Phone /> {phones[0]}
          </span>
        )}
        {loc && (
          <span className="meta-chip">
            <MapPin /> {loc}
          </span>
        )}
        {years_experience != null && (
          <span className="meta-chip">
            <Briefcase /> {years_experience}y exp
          </span>
        )}
      </div>

      {/* Skills */}
      {visibleSkills.length > 0 && (
        <div className="skills-row">
          {visibleSkills.map((s) => (
            <span key={s.name} className="skill-tag">{s.name}</span>
          ))}
          {extraSkills > 0 && (
            <span className="skill-tag-more">+{extraSkills}</span>
          )}
        </div>
      )}

      {/* Confidence bar */}
      <ConfidenceBar value={overall_confidence} />
    </div>
  );
}
