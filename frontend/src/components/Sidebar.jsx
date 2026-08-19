import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  Search,
  Users,
  Cpu,
  Database,
} from "lucide-react";
import { useCandidates } from "../contexts/CandidateContext";
import { useEffect } from "react";

const NAV = [
  { to: "/",       label: "Dashboard",      icon: LayoutDashboard },
  { to: "/upload", label: "Upload",         icon: Upload          },
  { to: "/search", label: "Semantic Search",icon: Search          },
];

export default function Sidebar() {
  const { total, fetchCandidates } = useCandidates();

  useEffect(() => { fetchCandidates(); }, [fetchCandidates]);

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">🧠</div>
        <div className="sidebar-logo-text">
          <h1>Candidate Intel</h1>
          <p>Django · React · MongoDB</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        <div className="sidebar-section-label">Navigation</div>
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Stats */}
      <div className="sidebar-stats">
        <div className="sidebar-section-label" style={{ marginTop: 0 }}>Live Stats</div>
        <div className="stat-row">
          <span><Users size={12} style={{ display:"inline", marginRight:4 }} />Candidates</span>
          <span>{total}</span>
        </div>
        <div className="stat-row">
          <span><Cpu size={12} style={{ display:"inline", marginRight:4 }} />Backend</span>
          <span style={{ color: "var(--clr-success)", fontSize: 11 }}>Django</span>
        </div>
        <div className="stat-row">
          <span><Database size={12} style={{ display:"inline", marginRight:4 }} />Database</span>
          <span style={{ fontSize: 11 }}>MongoDB</span>
        </div>
      </div>
    </aside>
  );
}
