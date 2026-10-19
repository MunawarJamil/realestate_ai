import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  Trash2,
  Search,
  Layers,
  Database,
  FileCheck,
  RefreshCw,
  AlertCircle,
  Bot,
} from 'lucide-react';
import type { KnowledgeDoc, DocumentCategory } from '../../types/agency';
import type { BackendKnowledgeDoc, BackendSearchResult } from '../../api/client';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { apiClient, ApiError } from '../../api/client';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function mapBackendDoc(doc: BackendKnowledgeDoc): KnowledgeDoc {
  let mappedCategory: DocumentCategory = 'Brochure';
  const lower = (doc.title || doc.filename).toLowerCase();
  if (lower.includes('floor') || lower.includes('plan')) {
    mappedCategory = 'Floorplan';
  } else if (lower.includes('price') || lower.includes('inventory')) {
    mappedCategory = 'Pricing';
  } else if (lower.includes('payment') || lower.includes('schedule')) {
    mappedCategory = 'Payment Plan';
  }

  return {
    id: doc.id,
    title: doc.title || doc.filename,
    category: mappedCategory,
    file_name: doc.filename,
    file_size: formatBytes(doc.file_size_bytes),
    chunk_count: doc.chunk_count,
    status: doc.status === 'ready' ? 'indexed' : doc.status === 'failed' ? 'failed' : 'processing',
    uploaded_at: new Date(doc.created_at).toISOString().split('T')[0],
  };
}

export const AgencyKnowledgePage: React.FC = () => {
  const [documents, setDocuments] = useState<KnowledgeDoc[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'all' | DocumentCategory>('all');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Upload Form State
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docTitle, setDocTitle] = useState('');
  const [docCategory, setDocCategory] = useState<DocumentCategory>('Brochure');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Qdrant Live Search Tester State
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<BackendSearchResult[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const fetchDocuments = useCallback(async (isPolling = false) => {
    if (!isPolling) setIsLoading(true);
    try {
      const res = await apiClient.agency.listDocuments({ limit: 100 });
      setDocuments(res.items.map(mapBackendDoc));
      setErrorBanner(null);
    } catch (err: unknown) {
      if (!isPolling) {
        if (err instanceof ApiError) {
          setErrorBanner(`Failed to load knowledge documents (${err.status}): ${err.message}`);
        } else {
          setErrorBanner('Could not connect to FastAPI backend at http://localhost:8000.');
        }
      }
    } finally {
      if (!isPolling) setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Polling: Auto-refresh if any doc is currently processing or pending
  const hasProcessingDocs = documents.some((d) => d.status === 'processing');
  useEffect(() => {
    if (!hasProcessingDocs) return;

    const interval = setInterval(() => {
      fetchDocuments(true);
    }, 3500);

    return () => clearInterval(interval);
  }, [hasProcessingDocs, fetchDocuments]);

  const filteredDocs = documents.filter((doc) => {
    const matchesSearch =
      doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.file_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || doc.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError('Please select a PDF, Markdown, or TXT file.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      const res = await apiClient.agency.uploadDocument(
        selectedFile,
        docTitle.trim() || undefined
      );

      // Prepend newly accepted doc
      setDocuments((prev) => [mapBackendDoc(res), ...prev]);
      setSelectedFile(null);
      setDocTitle('');
      if (fileInputRef.current) fileInputRef.current.value = '';

      showToast('Document uploaded! Processing and vectorizing chunks into Qdrant...');
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setUploadError(err.message);
      } else {
        setUploadError('Network error uploading file to backend.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteDoc = async (docId: string, title: string) => {
    if (!confirm(`Are you sure you want to delete "${title}"? This will delete its vector chunks.`)) {
      return;
    }

    try {
      await apiClient.agency.deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      showToast(`Removed "${title}" from database and vector index.`);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to delete document';
      alert(`Error deleting document: ${msg}`);
    }
  };

  const handleTestSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setSearchError(null);
    setSearchResults(null);

    try {
      const res = await apiClient.agency.searchKnowledge(searchQuery.trim(), 4);
      setSearchResults(res.results);
      if (res.results.length === 0) {
        showToast('No matching chunks found above threshold.');
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setSearchError(err.message);
      } else {
        setSearchError('Search failed. Ensure vector collection is initialized.');
      }
    } finally {
      setIsSearching(false);
    }
  };

  const totalChunks = documents.reduce((sum, d) => sum + (d.chunk_count || 0), 0);

  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Backend Communication Alert */}
      {errorBanner && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-start justify-between gap-3 text-xs text-amber-300">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Backend Notice</p>
              <p className="text-amber-300/80 mt-0.5">{errorBanner}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={() => fetchDocuments()}>
            <span>Retry</span>
          </Button>
        </div>
      )}

      {/* Header and Telemetry */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/8">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Knowledge Base
            </h2>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
              {documents.length} Files
            </span>
            <button
              onClick={() => fetchDocuments()}
              disabled={isLoading}
              title="Refresh Knowledge Base"
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Real documents parsed, chunked, and embedded into Qdrant for strict assistant grounding.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-zinc-400 bg-[#151517] border border-white/8 px-3 py-1.5 rounded-lg">
            <Database className="w-3.5 h-3.5 text-[#F97316]" />
            <span>Qdrant Isolated Chunks:</span>
            <strong className="text-white font-mono">{totalChunks} Vectors</strong>
          </div>
        </div>
      </div>

      {/* 2-Column Layout: Upload Section & Documents Library */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Card (1 Col) */}
        <div className="space-y-6">
          <div className="p-6 rounded-xl bg-[#151517] border border-white/8 space-y-4">
            <div className="flex items-center gap-2">
              <UploadCloud className="w-4 h-4 text-[#F97316]" />
              <h3 className="text-sm font-semibold text-white">Ingest New Property Document</h3>
            </div>
            <p className="text-xs text-zinc-400">
              Upload PDF brochures, floorplans, or price guides to give your AI assistant verified knowledge.
            </p>

            <form onSubmit={handleFileUpload} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                  Document Title (Optional)
                </label>
                <input
                  type="text"
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  placeholder="e.g. Palm Jumeirah Signature Villas"
                  className="w-full px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                  Document Category
                </label>
                <select
                  value={docCategory}
                  onChange={(e) => setDocCategory(e.target.value as DocumentCategory)}
                  className="w-full px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
                >
                  <option value="Brochure">Property Brochure (Specifications & Amenities)</option>
                  <option value="Floorplan">Floorplan (Layouts & Sq.Ft dimensions)</option>
                  <option value="Payment Plan">Payment Plan & Escrow Schedules</option>
                  <option value="Pricing">Official Pricing & Inventory Sheet</option>
                </select>
              </div>

              {/* Real file picker */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                  Attach Document (PDF, TXT, MD) *
                </label>
                <label className="flex flex-col items-center justify-center p-5 border border-dashed border-white/15 rounded-xl bg-[#0B0B0D] hover:border-[#F97316]/50 transition-colors cursor-pointer text-center">
                  <FileText className="w-6 h-6 text-[#F97316] mb-1.5" />
                  <span className="text-xs text-zinc-300 font-medium">
                    {selectedFile ? selectedFile.name : 'Click to select document'}
                  </span>
                  <span className="text-[10px] text-zinc-500 mt-1">
                    {selectedFile
                      ? `${formatBytes(selectedFile.size)} • Ready to upload`
                      : 'PDF, Markdown, or TXT up to 20MB'}
                  </span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.txt,.md"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        setSelectedFile(file);
                        if (!docTitle) setDocTitle(file.name.replace(/\.[^/.]+$/, ''));
                        setUploadError(null);
                      }
                    }}
                  />
                </label>
              </div>

              {uploadError && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{uploadError}</span>
                </div>
              )}

              <Button
                type="submit"
                variant="primary"
                size="md"
                className="w-full mt-2"
                disabled={isUploading || !selectedFile}
              >
                <UploadCloud className="w-4 h-4 mr-1.5" />
                <span>{isUploading ? 'Uploading to FastAPI...' : 'Upload & Vectorize'}</span>
              </Button>
            </form>
          </div>

          {/* Qdrant Semantic Search Tester */}
          <div className="p-6 rounded-xl bg-[#151517] border border-white/8 space-y-3.5">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-white">Qdrant Retrieval Tester</h3>
            </div>
            <p className="text-xs text-zinc-400">
              Test semantic search across your ingested property chunks directly.
            </p>

            <form onSubmit={handleTestSearch} className="space-y-2.5">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="e.g. 4 bed beachfront with private pool..."
                  className="w-full pl-8 pr-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#F97316]"
                />
              </div>
              <Button
                type="submit"
                variant="secondary"
                size="sm"
                className="w-full"
                disabled={isSearching || !searchQuery.trim()}
              >
                <span>{isSearching ? 'Querying Qdrant...' : 'Search Vector Collection'}</span>
              </Button>
            </form>

            {searchError && (
              <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                {searchError}
              </div>
            )}

            {searchResults && searchResults.length > 0 && (
              <div className="space-y-2 mt-3 pt-3 border-t border-white/8">
                <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block">
                  Top Grounded Results ({searchResults.length})
                </span>
                {searchResults.map((res, idx) => (
                  <div
                    key={res.id || idx}
                    className="p-3 rounded-lg bg-[#0B0B0D] border border-white/5 space-y-1 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-zinc-500">
                        Score: {(res.score * 100).toFixed(1)}% match
                      </span>
                      <span className="text-[10px] text-emerald-400 font-semibold bg-emerald-500/10 px-1.5 py-0.5 rounded">
                        Vector Match
                      </span>
                    </div>
                    <p className="text-zinc-300 line-clamp-3 text-[11px] leading-relaxed">
                      "{res.content}"
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Documents Library Table (2 Cols) */}
        <div className="lg:col-span-2 space-y-4">
          {/* Search & Category Filter */}
          <div className="p-3.5 rounded-xl bg-[#151517] border border-white/8 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search knowledge documents..."
                className="w-full pl-9 pr-3 py-1.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316]"
              />
            </div>

            <div className="flex items-center gap-1.5">
              {(['all', 'Brochure', 'Floorplan', 'Payment Plan', 'Pricing'] as const).map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium capitalize transition-colors cursor-pointer ${
                    categoryFilter === cat
                      ? 'bg-white/10 text-white font-semibold'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Table */}
          <div className="rounded-xl bg-[#151517] border border-white/8 overflow-hidden shadow-lg">
            <div className="w-full overflow-x-auto">
              <table className="w-full text-left text-xs min-w-[760px]">
                <thead>
                  <tr className="border-b border-white/8 text-zinc-400 uppercase tracking-wider text-[11px] bg-white/[0.01]">
                    <th className="py-3.5 px-5 font-semibold whitespace-nowrap">Document Title</th>
                    <th className="py-3.5 px-5 font-semibold whitespace-nowrap">Category</th>
                    <th className="py-3.5 px-5 font-semibold whitespace-nowrap">Qdrant Chunks</th>
                    <th className="py-3.5 px-5 font-semibold whitespace-nowrap">Status</th>
                    <th className="py-3.5 px-5 font-semibold text-right whitespace-nowrap">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {isLoading ? (
                    <tr>
                      <td colSpan={5} className="py-16 text-center text-zinc-500">
                        <RefreshCw className="w-5 h-5 text-[#F97316] animate-spin inline-block mr-2" />
                        Loading agency knowledge documents from database...
                      </td>
                    </tr>
                  ) : filteredDocs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-16 text-center text-zinc-500 text-xs">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <FileText className="w-6 h-6 text-zinc-600" />
                          <p>No property documents uploaded yet.</p>
                          <p className="text-[11px] text-zinc-600">
                            Use the form on the left to upload your first brochure or floorplan.
                          </p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredDocs.map((doc) => (
                      <tr key={doc.id} className="hover:bg-white/[0.02] transition-colors">
                        {/* Title & File */}
                        <td className="py-4 px-5 whitespace-nowrap">
                          <div className="font-semibold text-sm text-white flex items-center gap-2">
                            <FileCheck className="w-4 h-4 text-blue-400 shrink-0" />
                            <span>{doc.title}</span>
                          </div>
                          <div className="text-[11px] text-zinc-500 font-mono mt-0.5 ml-6">
                            {doc.file_name} • {doc.file_size} • {doc.uploaded_at}
                          </div>
                        </td>

                        {/* Category */}
                        <td className="py-4 px-5 whitespace-nowrap">
                          <span className="text-[11px] font-medium text-zinc-300 bg-white/5 px-2.5 py-1 rounded border border-white/5 whitespace-nowrap">
                            {doc.category}
                          </span>
                        </td>

                        {/* Chunks */}
                        <td className="py-4 px-5 font-mono text-zinc-200 whitespace-nowrap">
                          <div className="flex items-center gap-1.5">
                            <Layers className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                            <span className="text-emerald-400 font-bold">{doc.chunk_count}</span>
                            <span className="text-zinc-500 text-[11px]">vectors</span>
                          </div>
                        </td>

                        {/* Status */}
                        <td className="py-4 px-5 whitespace-nowrap">
                          <Badge
                            variant={
                              doc.status === 'indexed'
                                ? 'success'
                                : doc.status === 'failed'
                                ? 'danger'
                                : 'warning'
                            }
                            size="sm"
                          >
                            {doc.status === 'indexed'
                              ? 'Indexed in Qdrant'
                              : doc.status === 'failed'
                              ? 'Ingestion Failed'
                              : 'Processing Chunks...'}
                          </Badge>
                        </td>

                        {/* Actions */}
                        <td className="py-4 px-5 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={() => handleDeleteDoc(doc.id, doc.title)}
                              title="Delete from knowledge base"
                            >
                              <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
