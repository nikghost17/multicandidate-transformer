import { useEffect, useState } from "react";
import { RefreshCw, Trash2, ChevronLeft, ChevronRight, Users } from "lucide-react";
import { useCandidates } from "../contexts/CandidateContext";
import { useToast } from "../contexts/ToastContext";
import CandidateCard from "../components/CandidateCard";

function SkeletonCard() {
  return (
    <div className="skeleton" style={{ height: 240, borderRadius: "var(--r-lg)" }} />
  );
}

export default function Dashboard() {
  const { candidates, total, loading, page, PAGE_SIZE, fetchCandidates, clearAll } =
    useCandidates();
  const { addToast } = useToast();
  const [clearing, setClearing] = useState(false);

  useEffect(() => { fetchCandidates(1); }, [fetchCandidates]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const handleClear = async () => {
    if (!window.confirm("Delete ALL candidates? This cannot be undone.")) return;
    setClearing(true);
    try {
      const r = await clearAll();
      addToast(`Cleared ${r.deleted} candidates`, "info");
    } catch {
      addToast("Clear failed", "error");
    } finally {
      setClearing(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <h1>Candidate Profiles</h1>
          <p>{total} total candidates · Page {page} of {totalPages}</p>
        </div>
        <div className="page-actions">
          <button
            id="refresh-btn"
            className="btn btn-secondary"
            onClick={() => fetchCandidates(page)}
            disabled={loading}
          >
            <RefreshCw size={15} className={loading ? "spin" : ""} />
            Refresh
          </button>
          {total > 0 && (
            <button
              id="clear-all-btn"
              className="btn btn-danger"
              onClick={handleClear}
              disabled={clearing}
            >
              <Trash2 size={15} />
              {clearing ? "Clearing…" : "Clear All"}
            </button>
          )}
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="skeleton-grid">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : candidates.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">👥</div>
          <h3>No candidates yet</h3>
          <p>Upload a CSV or resume on the Upload page to get started.</p>
        </div>
      ) : (
        <>
          <div className="candidates-grid" id="candidates-grid">
            {candidates.map((c) => (
              <CandidateCard key={c.candidate_id} candidate={c} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                gap: 12,
                marginTop: 28,
              }}
            >
              <button
                id="prev-page-btn"
                className="btn btn-secondary"
                disabled={page <= 1}
                onClick={() => fetchCandidates(page - 1)}
              >
                <ChevronLeft size={15} /> Prev
              </button>
              <span className="text-muted fs-13">
                {page} / {totalPages}
              </span>
              <button
                id="next-page-btn"
                className="btn btn-secondary"
                disabled={page >= totalPages}
                onClick={() => fetchCandidates(page + 1)}
              >
                Next <ChevronRight size={15} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
