import { useState } from "react";
import { Search as SearchIcon } from "lucide-react";
import { useDrawer } from "../contexts/DrawerContext";

const BASE = "/api";

const CHIPS = [
  "Python developer with machine learning",
  "Senior DevOps with Kubernetes",
  "React frontend engineer",
  "Data scientist with NLP experience",
  "Full stack developer Java Spring",
  "Cloud architect AWS",
];

const SECTIONS = [
  { value: "",              label: "All Sections" },
  { value: "skills",       label: "Skills" },
  { value: "experience",   label: "Experience" },
  { value: "education",    label: "Education" },
  { value: "summary",      label: "Summary" },
  { value: "projects",     label: "Projects" },
];

function getInitials(name) {
  if (!name) return "?";
  return name.split(" ").slice(0, 2).map((n) => n[0]?.toUpperCase() ?? "").join("");
}

export default function Search() {
  const { openDrawer } = useDrawer();
  const [query,     setQuery]     = useState("");
  const [section,   setSection]   = useState("");
  const [results,   setResults]   = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [searched,  setSearched]  = useState(false);

  const doSearch = async (q = query, sec = section) => {
    if (!q.trim() || q.length < 2) return;
    setLoading(true);
    setSearched(true);
    try {
      const params = new URLSearchParams({ q: q.trim(), top_k: 10 });
      if (sec) params.set("section", sec);
      const res  = await fetch(`${BASE}/candidates/search?${params}`);
      const data = await res.json();
      setResults(data.results ?? []);
    } catch (e) {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleChip = (chip) => {
    setQuery(chip);
    doSearch(chip, section);
  };

  return (
    <div>
      {/* Hero */}
      <div className="search-hero">
        <h1>Semantic Search</h1>
        <p>Find candidates using natural language — powered by all-MiniLM-L6-v2 + MongoDB</p>
      </div>

      {/* Search bar */}
      <div className="search-bar-wrap">
        <span className="search-icon"><SearchIcon size={18} /></span>
        <input
          id="search-input"
          className="search-input"
          type="text"
          placeholder="e.g. Python developer with AWS and ML experience…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch()}
          aria-label="Search candidates"
        />
        <button
          id="search-submit-btn"
          className="search-btn-inline"
          onClick={() => doSearch()}
          disabled={loading || query.length < 2}
        >
          {loading ? "…" : "Search"}
        </button>
      </div>

      {/* Section filter */}
      <div style={{ display:"flex", justifyContent:"center", gap:8, marginBottom:20, flexWrap:"wrap" }}>
        {SECTIONS.map((s) => (
          <button
            key={s.value}
            id={`section-filter-${s.value || "all"}`}
            className="search-chip"
            style={section === s.value ? { borderColor:"var(--clr-primary)", color:"var(--clr-primary)", background:"var(--clr-primary-dim)" } : {}}
            onClick={() => { setSection(s.value); if (query) doSearch(query, s.value); }}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Quick chips */}
      <div className="search-chips">
        {CHIPS.map((chip) => (
          <button
            key={chip}
            id={`chip-${chip.slice(0,20).replace(/\s+/g,"-")}`}
            className="search-chip"
            onClick={() => handleChip(chip)}
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Results */}
      <div className="search-results" id="search-results">
        {loading && (
          <div className="empty-state">
            <div className="empty-icon" style={{ fontSize:36 }}>🔍</div>
            <p>Searching…</p>
          </div>
        )}

        {!loading && searched && results?.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🔎</div>
            <h3>No results found</h3>
            <p>Try a different query or upload more candidate data.</p>
          </div>
        )}

        {!loading && results?.map((r, i) => {
          const c = r.candidate;
          const pct = Math.round((r.relevance_score ?? 0) * 100);
          const loc = c.location
            ? [c.location.city, c.location.region, c.location.country].filter(Boolean).join(", ")
            : null;

          return (
            <div
              key={c.candidate_id}
              id={`result-card-${i}`}
              className="card result-card"
              onClick={() => openDrawer(c)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && openDrawer(c)}
              aria-label={`View profile for ${c.full_name}`}
            >
              <div className="result-score">{pct}%</div>
              <div className="result-body">
                <div className="result-name">{c.full_name || "Unknown"}</div>
                <div className="result-headline">
                  {c.headline || loc || "—"}
                  {r.section_title && (
                    <span className="meta-chip" style={{ marginLeft:8, display:"inline-flex" }}>
                      {r.section_title}
                    </span>
                  )}
                </div>
                {r.matched_chunk && (
                  <div className="result-snippet">{r.matched_chunk}</div>
                )}
                {c.skills?.length > 0 && (
                  <div className="skills-row" style={{ marginTop:8 }}>
                    {c.skills.slice(0, 5).map((s) => (
                      <span key={s.name} className="skill-tag">{s.name}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
