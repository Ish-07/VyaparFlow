"use client";

import { useEffect, useState, useCallback } from "react";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { api, ApiError } from "@/lib/apiClient";
import type { DocumentResponse, RAGAnswerResponse } from "@/lib/types";

export default function DocumentsPage() {
  const { ready } = useRequireAuth();
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [ingesting, setIngesting] = useState(false);

  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<RAGAnswerResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [querying, setQuerying] = useState(false);
  const [ocrTitle, setOcrTitle] = useState("");
  const [ocrFile, setOcrFile] = useState<File | null>(null);
  const [ocrError, setOcrError] = useState<string | null>(null);
  const [ocrUploading, setOcrUploading] = useState(false);

  const refresh = useCallback(async () => {
    setDocuments(await api.listDocuments());
  }, []);

  useEffect(() => {
    if (ready) refresh();
  }, [ready, refresh]);

  async function handleIngest(e: React.FormEvent) {
    e.preventDefault();
    setIngestError(null);
    setIngesting(true);
    try {
      await api.ingestDocument({ title, text });
      setTitle("");
      setText("");
      await refresh();
    } catch (err) {
      setIngestError(
        err instanceof ApiError
          ? String(err.message)
          : "Something went wrong."
      );
    } finally {
      setIngesting(false);
    }
  }
  async function handleOcrUpload(e: React.FormEvent) {
  e.preventDefault();
  if (!ocrFile) return;

  setOcrError(null);
  setOcrUploading(true);

  try {
    await api.uploadDocument({
      title: ocrTitle,
      document_type: "invoice",
      file: ocrFile,
    });

    setOcrTitle("");
    setOcrFile(null);
    await refresh();
  } catch (err) {
    setOcrError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
  } finally {
    setOcrUploading(false);
  }
}

  async function handleQuery(e: React.FormEvent) {
    e.preventDefault();
    setQueryError(null);
    setAnswer(null);
    setQuerying(true);
    try {
      setAnswer(await api.queryDocuments({ query }));
    } catch (err) {
      setQueryError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    } finally {
      setQuerying(false);
    }
  }

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Documents</h1>

      <div className="card">
        <h2 className="text-sm font-semibold mb-3">Ask a question about your documents</h2>
        <form onSubmit={handleQuery} className="flex gap-2">
          <input
            placeholder="e.g. what are my supplier's payment terms?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1"
          />
          <button type="submit" className="btn-primary" disabled={querying}>
            {querying ? "Asking..." : "Ask"}
          </button>
        </form>
        {queryError && <p className="text-sm text-warn mt-2">{queryError}</p>}
        {answer && (
          <div className="mt-3 border border-line rounded-md p-3 text-sm bg-paper">
            <p>{answer.answer}</p>
            {answer.sources.length > 0 && (
              <div className="mt-2 pt-2 border-t border-line text-xs text-muted space-y-1">
                <p className="font-medium">Sources:</p>
                {answer.sources.map((s) => (
                  <p key={s.chunk_id}>
                    {s.document_title} — {(s.similarity * 100).toFixed(0)}% match
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold mb-3">Add a document</h2>
        <p className="text-xs text-muted mb-3">
          Paste text directly for now (invoice terms, supplier notes, policies) — file upload comes
          later.
        </p>
        <form onSubmit={handleIngest} className="space-y-3">
          <div>
            <label className="label">Title</label>
            <input required value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <label className="label">Text</label>
            <textarea
              required
              rows={5}
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>
          {ingestError && <p className="text-sm text-warn">{ingestError}</p>}
          <button type="submit" className="btn-primary" disabled={ingesting}>
            {ingesting ? "Ingesting..." : "Add document"}
          </button>
        </form>
      </div>
      <div className="card">
  <h2 className="text-sm font-semibold mb-3">Upload invoice/image with OCR</h2>
  <p className="text-xs text-muted mb-3">
    Upload a PNG, JPG, JPEG, or WEBP file. PaddleOCR will extract text and index it for RAG Q&A.
  </p>

  <form onSubmit={handleOcrUpload} className="space-y-3">
    <div>
      <label className="label">Title</label>
      <input
        required
        value={ocrTitle}
        onChange={(e) => setOcrTitle(e.target.value)}
        placeholder="e.g. Supplier Invoice"
      />
    </div>

    <div>
      <label className="label">Image file</label>
      <input
        required
        type="file"
        accept="image/png,image/jpeg,image/jpg,image/webp"
        onChange={(e) => setOcrFile(e.target.files?.[0] || null)}
      />
    </div>

    {ocrError && <p className="text-sm text-warn">{ocrError}</p>}

    <button type="submit" className="btn-primary" disabled={ocrUploading || !ocrFile}>
      {ocrUploading ? "Extracting & indexing..." : "Upload with OCR"}
    </button>
  </form>
</div>

<div className="card">
  <h2 className="text-sm font-semibold mb-3">Add a document manually</h2>
  <p className="text-xs text-muted mb-3">
    Paste text directly for now, such as invoice terms, supplier notes, or policies.
  </p>

  <form onSubmit={handleIngest} className="space-y-3">
    <div>
      <label className="label">Title</label>
      <input required value={title} onChange={(e) => setTitle(e.target.value)} />
    </div>

    <div>
      <label className="label">Text</label>
      <textarea
        required
        rows={5}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
    </div>

    {ingestError && <p className="text-sm text-warn">{ingestError}</p>}

    <button type="submit" className="btn-primary" disabled={ingesting}>
      {ingesting ? "Ingesting..." : "Add document"}
    </button>
  </form>
</div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-paper text-muted text-xs">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Title</th>
              <th className="text-left px-4 py-2 font-medium">Status</th>
              <th className="text-left px-4 py-2 font-medium">Chunks</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id} className="border-t border-line">
                <td className="px-4 py-2">{d.title}</td>
                <td className="px-4 py-2">{d.status}</td>
                <td className="px-4 py-2">{d.chunk_count}</td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-muted text-sm">
                  No documents yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
