import { useState, useRef } from "react";
import { Upload as UploadIcon, FileText, Table } from "lucide-react";
import { useCandidates } from "../contexts/CandidateContext";
import { useToast } from "../contexts/ToastContext";

const BASE = "/api";

function DropZone({ accept, label, icon: Icon, types, onUpload, uploading }) {
  const [dragOver, setDragOver] = useState(false);
  const [result,   setResult]   = useState(null);
  const inputRef = useRef(null);

  const handleFile = async (file) => {
    if (!file) return;
    setResult(null);
    try {
      const res = await onUpload(file);
      setResult({ type: "success", message: res.message ?? "Uploaded successfully!" });
    } catch (e) {
      setResult({ type: "error", message: e.message ?? "Upload failed." });
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div>
      <div
        className={`upload-zone${dragOver ? " drag-over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        id={`upload-zone-${label.toLowerCase().replace(/\s+/g,"-")}`}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        aria-label={`Upload ${label}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files[0])}
          id={`file-input-${label.toLowerCase().replace(/\s+/g,"-")}`}
        />

        <div className="upload-icon">
          <Icon />
        </div>
        <div className="upload-title">{label}</div>
        <div className="upload-desc">Drag & drop or click to browse</div>
        <div className="upload-types">
          {types.map((t) => <span key={t} className="type-chip">{t}</span>)}
        </div>
      </div>

      {uploading && (
        <div className="upload-progress">
          <div className="progress-bar-track">
            <div className="progress-bar-fill" />
          </div>
          <span className="text-muted fs-12">Processing…</span>
        </div>
      )}

      {result && (
        <div className={`upload-result ${result.type}`}>
          {result.type === "success" ? "✓ " : "✕ "}
          {result.message}
        </div>
      )}
    </div>
  );
}

export default function Upload() {
  const { fetchCandidates } = useCandidates();
  const { addToast } = useToast();
  const [csvUploading,    setCsvUploading]    = useState(false);
  const [resumeUploading, setResumeUploading] = useState(false);
  const [enableLlm,       setEnableLlm]       = useState(false);
  const [enrichLlm,       setEnrichLlm]       = useState(true);

  const uploadCSV = async (file) => {
    setCsvUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("enable_llm", enableLlm ? "true" : "false");
      const res  = await fetch(`${BASE}/candidates/from-csv`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "CSV upload failed");
      addToast(data.message, "success");
      fetchCandidates(1);
      return data;
    } finally {
      setCsvUploading(false);
    }
  };

  const uploadResume = async (file) => {
    setResumeUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("enrich_with_llm", enrichLlm ? "true" : "false");
      const res  = await fetch(`${BASE}/candidates/from-resume`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Resume upload failed");
      addToast(data.message, "success");
      fetchCandidates(1);
      return data;
    } finally {
      setResumeUploading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Upload Data</h1>
        <p>Ingest candidate data from recruiter CSV files or individual resumes</p>
      </div>

      <div className="upload-grid">
        {/* CSV */}
        <div className="card" style={{ padding: 24 }}>
          <div className="fw-600 mb-4" style={{ display:"flex", alignItems:"center", gap:8, fontSize:15 }}>
            <Table size={18} style={{ color:"var(--clr-primary)" }} />
            Recruiter CSV
          </div>

          <DropZone
            accept=".csv"
            label="CSV File"
            icon={Table}
            types={[".csv"]}
            onUpload={uploadCSV}
            uploading={csvUploading}
          />

          <div className="divider" />

          <label
            id="enable-llm-label"
            style={{ display:"flex", alignItems:"center", gap:10, cursor:"pointer", fontSize:13, color:"var(--clr-text-dim)" }}
          >
            <input
              id="enable-llm-checkbox"
              type="checkbox"
              checked={enableLlm}
              onChange={(e) => setEnableLlm(e.target.checked)}
              style={{ accentColor:"var(--clr-primary)" }}
            />
            Enable LLM conflict resolution (Gemini)
          </label>
        </div>

        {/* Resume */}
        <div className="card" style={{ padding: 24 }}>
          <div className="fw-600 mb-4" style={{ display:"flex", alignItems:"center", gap:8, fontSize:15 }}>
            <FileText size={18} style={{ color:"var(--clr-accent)" }} />
            Resume Upload
          </div>

          <DropZone
            accept=".pdf,.docx,.txt"
            label="Resume File"
            icon={UploadIcon}
            types={[".pdf", ".docx", ".txt"]}
            onUpload={uploadResume}
            uploading={resumeUploading}
          />

          <div className="divider" />

          <label
            id="enrich-llm-label"
            style={{ display:"flex", alignItems:"center", gap:10, cursor:"pointer", fontSize:13, color:"var(--clr-text-dim)" }}
          >
            <input
              id="enrich-llm-checkbox"
              type="checkbox"
              checked={enrichLlm}
              onChange={(e) => setEnrichLlm(e.target.checked)}
              style={{ accentColor:"var(--clr-primary)" }}
            />
            Extract structured data with Gemini AI
          </label>
        </div>
      </div>

      {/* Info box */}
      <div
        className="card"
        style={{ marginTop: 24, padding: "20px 24px", background:"var(--clr-surface-2)" }}
      >
        <div className="fw-600 mb-4" style={{ fontSize:14 }}>📋 How it works</div>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, fontSize:13, color:"var(--clr-text-dim)" }}>
          <div>
            <strong style={{ color:"var(--clr-text)" }}>CSV Upload</strong>
            <ul style={{ marginTop:6, paddingLeft:16, lineHeight:1.8 }}>
              <li>Parses flexible column names</li>
              <li>Deduplicates on email &amp; phone</li>
              <li>Indexes in MongoDB vector store</li>
            </ul>
          </div>
          <div>
            <strong style={{ color:"var(--clr-text)" }}>Resume Upload</strong>
            <ul style={{ marginTop:6, paddingLeft:16, lineHeight:1.8 }}>
              <li>Extracts text via LangChain</li>
              <li>Gemini structured extraction</li>
              <li>Merges with existing profile</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
