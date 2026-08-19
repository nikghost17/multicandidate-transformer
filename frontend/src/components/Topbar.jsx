import { useLocation } from "react-router-dom";
import { useCandidates } from "../contexts/CandidateContext";

const PAGE_META = {
  "/":       { title: "Dashboard",       desc: "All candidate profiles at a glance" },
  "/upload": { title: "Upload Data",     desc: "Ingest CSV files or PDF/DOCX resumes" },
  "/search": { title: "Semantic Search", desc: "Natural language search across all candidates" },
};

export default function Topbar() {
  const { pathname } = useLocation();
  const meta = PAGE_META[pathname] ?? { title: "Candidate Intelligence", desc: "" };
  const { total } = useCandidates();

  return (
    <header className="topbar">
      <div className="topbar-left">
        <h2>{meta.title}</h2>
        {meta.desc && <p>{meta.desc}</p>}
      </div>
      <div className="topbar-right">
        <div className="status-badge">
          <span className="status-dot" />
          Django API · {total} candidates
        </div>
      </div>
    </header>
  );
}
