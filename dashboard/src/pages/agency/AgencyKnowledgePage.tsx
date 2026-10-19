import React, { useState } from 'react';
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  Trash2,
  RotateCcw,
  Search,
  Layers,
  Database,
  FileCheck,
  Sparkles,
} from 'lucide-react';
import { initialDocuments } from '../../mock/agencyData';
import type { KnowledgeDoc, DocumentCategory } from '../../types/agency';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

export const AgencyKnowledgePage: React.FC = () => {
  const [documents, setDocuments] = useState<KnowledgeDoc[]>(initialDocuments);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'all' | DocumentCategory>('all');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Upload simulation state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [docTitle, setDocTitle] = useState('');
  const [docCategory, setDocCategory] = useState<DocumentCategory>('Brochure');
  const [selectedFileName, setSelectedFileName] = useState('');

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2500);
  };

  const filteredDocs = documents.filter((doc) => {
    const matchesSearch =
      doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.file_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || doc.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const handleSimulatedUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!docTitle.trim() || !selectedFileName) return;

    setIsUploading(true);
    setUploadProgress(20);

    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 95) {
          clearInterval(interval);
          setTimeout(() => {
            setIsUploading(false);
            setUploadProgress(0);

            const randomChunks = Math.floor(Math.random() * 40) + 30;
            const newDoc: KnowledgeDoc = {
              id: `doc-${Date.now().toString().slice(-4)}`,
              title: docTitle.trim(),
              category: docCategory,
              file_name: selectedFileName,
              file_size: `${(Math.random() * 10 + 2).toFixed(1)} MB`,
              chunk_count: randomChunks,
              status: 'indexed',
              uploaded_at: new Date().toISOString().split('T')[0],
            };

            setDocuments([newDoc, ...documents]);
            setDocTitle('');
            setSelectedFileName('');
            showToast(`Document successfully chunked & indexed into Qdrant! (${randomChunks} vectors)`);
          }, 400);
          return 100;
        }
        return prev + 25;
      });
    }, 200);
  };

  const handleDeleteDoc = (docId: string, title: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== docId));
    showToast(`Removed "${title}" from vector collection.`);
  };

  const handleReindex = (docId: string) => {
    setDocuments((prev) =>
      prev.map((d) => (d.id === docId ? { ...d, status: 'processing' } : d))
    );
    showToast('Re-indexing vector chunks in Qdrant...');

    setTimeout(() => {
      setDocuments((prev) =>
        prev.map((d) => (d.id === docId ? { ...d, status: 'indexed' } : d))
      );
      showToast('Re-indexing complete. Vectors up to date.');
    }, 1200);
  };

  const totalChunks = documents.reduce((sum, d) => sum + d.chunk_count, 0);

  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header and Telemetry */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/8">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Knowledge Base
            </h2>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
              {documents.length} Files
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Property brochures and floorplans parsed for grounded AI answers.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-zinc-400 bg-[#151517] border border-white/8 px-3 py-1.5 rounded-lg">
            <Database className="w-3.5 h-3.5 text-[#F97316]" />
            <span>Qdrant Isolated Collection:</span>
            <strong className="text-white font-mono">{totalChunks} Chunks</strong>
          </div>
        </div>
      </div>

      {/* 2-Column Layout: Upload Section & Documents Library */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Card (1 Col) */}
        <div className="p-6 rounded-xl bg-[#151517] border border-white/8 space-y-4">
          <div className="flex items-center gap-2">
            <UploadCloud className="w-4 h-4 text-[#F97316]" />
            <h3 className="text-sm font-semibold text-white">Ingest New Property Document</h3>
          </div>
          <p className="text-xs text-zinc-400">
            Upload PDF brochures, floorplans, or price guides to give your AI assistant verified knowledge.
          </p>

          <form onSubmit={handleSimulatedUpload} className="space-y-3">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                Document Title
              </label>
              <input
                type="text"
                required
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

            {/* Fake file picker */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                Attach PDF File
              </label>
              <label className="flex flex-col items-center justify-center p-4 border border-dashed border-white/15 rounded-xl bg-[#0B0B0D] hover:border-[#F97316]/50 transition-colors cursor-pointer">
                <FileText className="w-6 h-6 text-zinc-500 mb-1" />
                <span className="text-xs text-zinc-300 font-medium">
                  {selectedFileName || 'Click to select PDF document'}
                </span>
                <span className="text-[10px] text-zinc-500 mt-0.5">
                  PDF, Markdown, or TXT up to 50MB
                </span>
                <input
                  type="file"
                  accept=".pdf,.txt,.md"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) setSelectedFileName(file.name);
                  }}
                />
              </label>
            </div>

            {/* Ingestion Progress Bar */}
            {isUploading && (
              <div className="space-y-1.5 p-3 rounded-lg bg-[#0B0B0D] border border-white/5">
                <div className="flex items-center justify-between text-xs text-zinc-300 font-medium">
                  <span className="flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3 text-[#F97316] animate-spin" />
                    Chunking & Embedding...
                  </span>
                  <span className="font-mono text-[#F97316]">{uploadProgress}%</span>
                </div>
                <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-[#F97316] to-[#EA580C] transition-all duration-200"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="md"
              className="w-full mt-2"
              disabled={isUploading || !docTitle.trim() || !selectedFileName}
            >
              <UploadCloud className="w-4 h-4 mr-1.5" />
              <span>{isUploading ? 'Ingesting into Qdrant...' : 'Upload & Vectorize'}</span>
            </Button>
          </form>
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
              {(['all', 'Brochure', 'Floorplan', 'Payment Plan'] as const).map((cat) => (
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
                  {filteredDocs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-12 text-center text-zinc-500 text-xs">
                        No property documents found matching your filter.
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
                            {doc.file_name} • {doc.file_size}
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
                            variant={doc.status === 'indexed' ? 'success' : 'warning'}
                            size="sm"
                          >
                            {doc.status === 'indexed' ? 'Indexed in Qdrant' : 'Chunking...'}
                          </Badge>
                        </td>

                        {/* Actions */}
                        <td className="py-4 px-5 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleReindex(doc.id)}
                              title="Re-chunk and update embeddings in Qdrant"
                            >
                              <RotateCcw className="w-3.5 h-3.5 text-zinc-400" />
                            </Button>
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
