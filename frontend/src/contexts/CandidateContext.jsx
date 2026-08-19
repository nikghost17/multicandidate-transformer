import { createContext, useContext, useState, useCallback } from "react";

const CandidateContext = createContext(null);

const BASE = "/api";

export function CandidateProvider({ children }) {
  const [candidates, setCandidates]   = useState([]);
  const [total,      setTotal]        = useState(0);
  const [loading,    setLoading]      = useState(false);
  const [page,       setPage]         = useState(1);
  const PAGE_SIZE = 20;

  const fetchCandidates = useCallback(async (p = 1) => {
    setLoading(true);
    try {
      const res  = await fetch(`${BASE}/candidates?page=${p}&page_size=${PAGE_SIZE}`);
      const data = await res.json();
      setCandidates(data.candidates ?? []);
      setTotal(data.total ?? 0);
      setPage(p);
    } catch (err) {
      console.error("fetchCandidates error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteCandidate = useCallback(async (id) => {
    const res = await fetch(`${BASE}/candidates/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");
    setCandidates((prev) => prev.filter((c) => c.candidate_id !== id));
    setTotal((t) => Math.max(0, t - 1));
  }, []);

  const enrichCandidate = useCallback(async (id) => {
    const res  = await fetch(`${BASE}/candidates/${id}/enrich`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Enrich failed");
    setCandidates((prev) =>
      prev.map((c) => (c.candidate_id === id ? data.candidate : c))
    );
    return data.candidate;
  }, []);

  const fetchConfidence = useCallback(async (id) => {
    const res  = await fetch(`${BASE}/candidates/${id}/confidence`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Fetch confidence failed");
    return data;
  }, []);

  const clearAll = useCallback(async () => {
    const res  = await fetch(`${BASE}/candidates`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Clear failed");
    setCandidates([]);
    setTotal(0);
    return data;
  }, []);

  return (
    <CandidateContext.Provider
      value={{
        candidates,
        total,
        loading,
        page,
        PAGE_SIZE,
        fetchCandidates,
        deleteCandidate,
        enrichCandidate,
        fetchConfidence,
        clearAll,
      }}
    >
      {children}
    </CandidateContext.Provider>
  );
}

export const useCandidates = () => useContext(CandidateContext);
