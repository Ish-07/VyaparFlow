"use client";

import { useEffect, useState, useCallback } from "react";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { api, ApiError } from "@/lib/apiClient";
import type {
  DocumentContentResponse,
  DocumentResponse,
  RAGAnswerResponse,
} from "@/lib/types";
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
  const [selectedDocument, setSelectedDocument] = useState<DocumentResponse | null>(null);
  const [showDocument, setShowDocument] = useState(false);
  const [documentContent, setDocumentContent] = useState<DocumentContentResponse | null>(null);
  const [loadingDocument, setLoadingDocument] = useState(false);
  const [documentViewError, setDocumentViewError] = useState<string | null>(null);

  async function handleViewDocument() {
    if (!selectedDocument) return;

    if (showDocument) {
      setShowDocument(false);
      return;
    }

    setLoadingDocument(true);
    setDocumentViewError(null);

    try {
      const content = await api.getDocumentContent(selectedDocument.id);
      setDocumentContent(content);
      setShowDocument(true);
    } catch (err) {
      setDocumentViewError(
        err instanceof ApiError ? String(err.message) : "Something went wrong."
      );
    } finally {
      setLoadingDocument(false);
    }
  }

  const refresh = useCallback(async () => {
  const loadedDocuments = await api.listDocuments();

  setDocuments(loadedDocuments);

  setSelectedDocument((current) => {
    // Keep the document the user is currently viewing.
    if (
      current &&
      loadedDocuments.some((document) => document.id === current.id)
    ) {
      return current;
    }

    // On first load, select the newest document.
    return loadedDocuments[0] ?? null;
  });
}, []);

  useEffect(() => {
    if (ready) refresh();
  }, [ready, refresh]);

  async function handleIngest(e: React.FormEvent) {
    e.preventDefault();
    setIngestError(null);
    setIngesting(true);
    try {
      const createdDocument = await api.ingestDocument({ title, text });

setSelectedDocument(createdDocument);
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
    const createdDocument = await api.uploadDocument({
  title: ocrTitle,
  document_type: "invoice",
  file: ocrFile,
});

setSelectedDocument(createdDocument);
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

  if (!selectedDocument) {
    setQueryError("Please upload or select a document first.");
    return;
  }

  if (!query.trim()) {
    setQueryError("Please enter a question.");
    return;
  }

  setQuerying(true);

  try {
    setAnswer(
      await api.queryDocuments({
        query: query.trim(),
        document_id: selectedDocument.id,
      })
    );
  } catch (err) {
    setQueryError(
      err instanceof ApiError ? String(err.message) : "Something went wrong."
    );
  } finally {
    setQuerying(false);
  }
}

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Documents</h1>
      <section className="card space-y-6">
  <div>
    <h2 className="text-base font-semibold">
      Upload / Fetch Document
    </h2>
    <p className="text-xs text-muted mt-1">
      Upload a new document or work with the currently selected document.
    </p>
  </div>
      {selectedDocument ? (
  <div className="card">
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="label">Fetched document</p>
        <h2 className="text-base font-semibold">
          {selectedDocument.title}
        </h2>

        <p className="text-xs text-muted mt-1">
          {selectedDocument.document_type} · {selectedDocument.status} ·{" "}
          {selectedDocument.chunk_count} chunks
        </p>
      </div>

      <button
        type="button"
        className="btn-secondary shrink-0"
        onClick={handleViewDocument}
        disabled={loadingDocument}
      >
        {loadingDocument
          ? "Loading..."
          : showDocument
            ? "Hide Document"
            : "View Document"}
      </button>
    </div>

    {documentViewError && (
      <p className="text-sm text-warn mt-3">
        {documentViewError}
      </p>
    )}

    {showDocument && documentContent && (
      <div className="mt-4 border-t border-line pt-4">
        <p className="label">Document content</p>

        <pre className="whitespace-pre-wrap text-sm leading-6 bg-white border border-line rounded-md p-4 max-h-96 overflow-y-auto">
          {documentContent.content}
        </pre>
      </div>
    )}
  </div>
) : (
  <div className="card">
    <p className="text-sm text-muted">
      No documents uploaded yet.
    </p>
  </div>
)}

      <div className="card">
         <h2 className="text-sm font-semibold mb-1">
  Ask Question
</h2>

<p className="text-xs text-muted mb-3">
  {selectedDocument
    ? `Ask a question about "${selectedDocument.title}".`
    : "Upload or fetch a document before asking a question."}
</p>
        <form onSubmit={handleQuery} className="flex gap-2">
          <input
  placeholder="e.g. what are my supplier's payment terms?"
  value={query}
  onChange={(e) => setQuery(e.target.value)}
  className="flex-1"
  disabled={!selectedDocument}
/>
         <button
  type="submit"
  className="btn-primary"
  disabled={querying || !selectedDocument || !query.trim()}
>
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

      <section className="card space-y-6">
  {/* fetched document */}
  {/* Ask Question */}
  {/* OCR upload */}
  {/* manual document upload */}
</section>

     <section className="card p-0 overflow-hidden">
  <div className="p-5 border-b border-line">
    <h2 className="text-base font-semibold">
      Previously Uploaded Documents
    </h2>
    <p className="text-xs text-muted mt-1">
      Select a document to bring it into the main document section.
    </p>
  </div>

  {documents.length === 0 ? (
    <p className="px-5 py-6 text-center text-sm text-muted">
      No documents uploaded yet.
    </p>
  ) : (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-paper text-muted text-xs">
          <tr>
            <th className="text-left px-5 py-3 font-medium">
              Title
            </th>
            <th className="text-left px-5 py-3 font-medium">
              Status
            </th>
            <th className="text-left px-5 py-3 font-medium">
              Chunks
            </th>
            <th className="text-right px-5 py-3 font-medium">
              Action
            </th>
          </tr>
        </thead>

        <tbody>
          {documents.map((document) => {
            const isSelected =
              selectedDocument?.id === document.id;

            return (
              <tr
                key={document.id}
                className="border-t border-line"
              >
                <td className="px-5 py-3">
                  <div className="font-medium">
                    {document.title}
                  </div>

                  {isSelected && (
                    <span className="text-xs text-accent">
                      Currently fetched
                    </span>
                  )}
                </td>

                <td className="px-5 py-3 text-muted">
                  {document.status}
                </td>

                <td className="px-5 py-3 text-muted">
                  {document.chunk_count}
                </td>

                <td className="px-5 py-3 text-right">
                  <button
                    type="button"
                    className="btn-secondary text-xs"
                    disabled={isSelected}
                    onClick={() => {
                      setSelectedDocument(document);
                      setDocumentContent(null);
                      setShowDocument(false);
                      setDocumentViewError(null);

                      window.scrollTo({
                        top: 0,
                        behavior: "smooth",
                      });
                    }}
                  >
                    {isSelected ? "Fetched" : "Fetch"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  )}
</section>
    </section>
  </div>
  );
}
