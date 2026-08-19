import { useState, useEffect } from "react";
import { X, Sparkles, Trash2, Star } from "lucide-react";
import { useDrawer } from "../contexts/DrawerContext";
import { useCandidates } from "../contexts/CandidateContext";
import { useToast } from "../contexts/ToastContext";

const TABS = ["Profile", "Confidence", "Provenance"];

function getInitials(name) {
  if (!name) return "?";
  return name.split(" ").slice(0, 2).map((n) => n[0]?.toUpperCase() ?? "").join("");
}

/* ── Profile Tab ─────────────────────────────────────────────────── */
function ProfileTab({ candidate }) {
  const {
    full_name, headline, emails = [], phones = [], location,
    skills = [], experience = [], education = [], llm_summary,
    years_experience, llm_enriched,
  } = candidate;

  const loc = location
    ? [location.city, location.region, location.country].filter(Boolean).join(", ")
    : "—";

  return (
    <div>
      {/* Summary */}
      {llm_summary && (
        <div className="drawer-section">
          <div className="drawer-section-title">AI Summary</div>
          <div className="summary-box">{llm_summary}</div>
        </div>
      )}

      {/* Contact */}
      <div className="drawer-section">
        <div className="drawer-section-title">Contact & Info</div>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-label">Email(s)</span>
            <span className="info-value">{emails.join(", ") || "—"}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Phone(s)</span>
            <span className="info-value">{phones.join(", ") || "—"}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Location</span>
            <span className="info-value">{loc}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Experience</span>
            <span className="info-value">{years_experience != null ? `${years_experience} years` : "—"}</span>
          </div>
        </div>
      </div>

      {/* Skills */}
      {skills.length > 0 && (
        <div className="drawer-section">
          <div className="drawer-section-title">Skills ({skills.length})</div>
          <div className="skills-row">
            {skills.map((s) => (
              <span key={s.name} className="skill-tag">{s.name}</span>
            ))}
          </div>
        </div>
      )}

      {/* Experience */}
      {experience.length > 0 && (
        <div className="drawer-section">
          <div className="drawer-section-title">Experience</div>
          {experience.map((exp, i) => (
            <div key={i} className="exp-item">
              <div className="exp-title">{exp.title}</div>
              <div className="exp-company">{exp.company}</div>
              {(exp.start || exp.end) && (
                <div className="exp-dates">{exp.start} – {exp.end || "Present"}</div>
              )}
              {exp.summary && <div className="exp-summary">{exp.summary}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Education */}
      {education.length > 0 && (
        <div className="drawer-section">
          <div className="drawer-section-title">Education</div>
          {education.map((edu, i) => (
            <div key={i} className="edu-item">
              <div className="exp-title">{edu.institution}</div>
              {edu.degree && <div className="exp-company">{edu.degree}</div>}
              {edu.field_of_study && <div className="exp-dates">{edu.field_of_study}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Confidence Tab ──────────────────────────────────────────────── */
function ConfidenceTab({ candidateId }) {
  const { fetchConfidence } = useCandidates();
  const [data, setData]     = useState(null);

  useEffect(() => {
    fetchConfidence(candidateId).then(setData).catch(console.error);
  }, [candidateId, fetchConfidence]);

  if (!data) return <div className="text-muted fs-13" style={{ textAlign:"center", padding:"40px 0" }}>Loading…</div>;

  const fields = data.fields ?? data ?? {};

  return (
    <div>
      {Object.entries(fields).map(([field, info]) => {
        const score = typeof info === "object" ? info.confidence ?? info.score ?? 0 : info;
        const source = typeof info === "object" ? info.source ?? info.method ?? "" : "";
        const pct = Math.round(score * 100);
        const color = pct >= 80 ? "var(--clr-success)" : pct >= 50 ? "var(--clr-warning)" : "var(--clr-danger)";
        return (
          <div key={field} className="confidence-item">
            <div className="confidence-item-header">
              <span className="confidence-field-name">{field.replace(/_/g, " ")}</span>
              <span className="confidence-score" style={{ color }}>{pct}%</span>
            </div>
            {source && <div className="confidence-source">Source: {source}</div>}
            <div className="confidence-bar-track" style={{ marginTop: 6 }}>
              <div
                className="confidence-bar-fill"
                style={{ width: `${pct}%`, background: color }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Provenance Tab ──────────────────────────────────────────────── */
function ProvenanceTab({ candidate }) {
  const provenance = candidate.provenance ?? [];

  if (!provenance.length)
    return <div className="text-muted fs-13" style={{ textAlign:"center", padding:"40px 0" }}>No provenance data.</div>;

  return (
    <div>
      {provenance.map((p, i) => (
        <div key={i} className="prov-item">
          <div className="prov-field">{p.field_name}</div>
          <div className="prov-meta">
            {p.source && <span className="prov-tag">source: {p.source}</span>}
            {p.method && <span className="prov-tag">method: {p.method}</span>}
            {p.confidence != null && (
              <span className="prov-tag">conf: {Math.round(p.confidence * 100)}%</span>
            )}
          </div>
          {p.value != null && (
            <div className="info-value" style={{ marginTop:6, fontSize:12 }}>
              {typeof p.value === "object" ? JSON.stringify(p.value) : String(p.value)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ── Drawer Shell ────────────────────────────────────────────────── */
export default function CandidateDrawer() {
  const { openCandidate, closeDrawer } = useDrawer();
  const { enrichCandidate, deleteCandidate } = useCandidates();
  const { addToast } = useToast();
  const [activeTab, setActiveTab]     = useState("Profile");
  const [enriching, setEnriching]     = useState(false);
  const [candidate, setCandidate]     = useState(null);

  useEffect(() => {
    if (openCandidate) {
      setCandidate(openCandidate);
      setActiveTab("Profile");
    }
  }, [openCandidate]);

  if (!openCandidate || !candidate) return null;

  const handleEnrich = async () => {
    setEnriching(true);
    try {
      const updated = await enrichCandidate(candidate.candidate_id);
      setCandidate(updated);
      addToast("Enriched with Gemini AI ✨", "success");
    } catch (e) {
      addToast(e.message || "Enrichment failed", "error");
    } finally {
      setEnriching(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete ${candidate.full_name}?`)) return;
    try {
      await deleteCandidate(candidate.candidate_id);
      addToast(`${candidate.full_name} deleted`, "info");
      closeDrawer();
    } catch (e) {
      addToast("Delete failed", "error");
    }
  };

  return (
    <>
      <div className="drawer-overlay" onClick={closeDrawer} />
      <div className="drawer" id="candidate-drawer" role="dialog" aria-modal="true">

        {/* Header */}
        <div className="drawer-header">
          <div className="drawer-avatar-block">
            <div className="avatar" style={{ width:46, height:46, fontSize:17 }}>
              {getInitials(candidate.full_name)}
            </div>
            <div>
              <div className="drawer-name">{candidate.full_name || "Unknown"}</div>
              <div className="drawer-sub">
                {candidate.llm_enriched && <><Star size={11} style={{ display:"inline", marginRight:4 }} />AI Enriched · </>}
                ID: <span className="mono" style={{ fontSize:11 }}>{candidate.candidate_id?.slice(0, 8)}…</span>
              </div>
            </div>
          </div>
          <button className="icon-btn" id="drawer-close-btn" onClick={closeDrawer} aria-label="Close">
            <X size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div className="drawer-tabs">
          {TABS.map((t) => (
            <button
              key={t}
              id={`drawer-tab-${t.toLowerCase()}`}
              className={`drawer-tab${activeTab === t ? " active" : ""}`}
              onClick={() => setActiveTab(t)}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="drawer-body">
          {activeTab === "Profile"    && <ProfileTab    candidate={candidate} />}
          {activeTab === "Confidence" && <ConfidenceTab candidateId={candidate.candidate_id} />}
          {activeTab === "Provenance" && <ProvenanceTab candidate={candidate} />}
        </div>

        {/* Footer */}
        <div className="drawer-footer">
          <button
            id="enrich-btn"
            className="btn btn-accent"
            onClick={handleEnrich}
            disabled={enriching || candidate.llm_enriched}
            style={{ flex: 1 }}
          >
            <Sparkles size={15} />
            {enriching ? "Enriching…" : candidate.llm_enriched ? "Already Enriched" : "Enrich with Gemini"}
          </button>
          <button
            id="delete-candidate-btn"
            className="btn btn-danger"
            onClick={handleDelete}
            aria-label="Delete candidate"
          >
            <Trash2 size={15} />
          </button>
        </div>
      </div>
    </>
  );
}
