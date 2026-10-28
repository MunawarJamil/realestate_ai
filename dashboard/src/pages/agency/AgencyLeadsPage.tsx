import React, { useEffect, useState, useMemo } from 'react';
import {
  Search,
  Plus,
  Flame,
  Phone,
  Mail,
  MapPin,
  Download,
  Sparkles,
  RefreshCw,
  TrendingUp,
  Award,
  Users,
} from 'lucide-react';
import { apiClient, type BackendLead } from '../../api/client';
import { AgentSocketClient } from '../../api/agentSocket';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';

export const AgencyLeadsPage: React.FC = () => {
  const [leads, setLeads] = useState<BackendLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [scoreFilter, setScoreFilter] = useState<'all' | 'hot' | 'warm' | 'cold'>('all');
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [selectedLead, setSelectedLead] = useState<BackendLead | null>(null);

  // New Lead Form State
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [intent, setIntent] = useState<'buy' | 'rent' | 'invest'>('buy');
  const [propertyType, setPropertyType] = useState('');
  const [location, setLocation] = useState('');
  const [budgetMax, setBudgetMax] = useState('');
  const [notes, setNotes] = useState('');

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const loadLeads = async () => {
    try {
      setLoading(true);
      const res = await apiClient.leads.list({ size: 100 });
      setLeads(res.items);
    } catch (err: any) {
      showToast(`Failed to load leads: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLeads();

    const socket = new AgentSocketClient({
      onLeadCreated: (lead: BackendLead) => {
        setLeads((prev) => [lead, ...prev.filter((l) => l.id !== lead.id)]);
        showToast(`✨ New Lead Captured: ${lead.contact_name || 'Prospect'}!`);
      },
      onLeadUpdated: (lead: BackendLead) => {
        setLeads((prev) => prev.map((l) => (l.id === lead.id ? lead : l)));
      },
      onHotLeadAlert: (lead: BackendLead) => {
        showToast(`🔥 HOT LEAD ALERT: ${lead.contact_name || 'VIP Client'} (Score: ${lead.ai_score}/100)`);
      },
    });
    socket.connect();
  }, []);

  const handleStatusChange = async (leadId: string, nextStatus: any) => {
    try {
      const updated = await apiClient.leads.update(leadId, { status: nextStatus });
      setLeads((prev) => prev.map((l) => (l.id === leadId ? updated : l)));
      showToast('Lead status updated!');
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const handleAddLead = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      const newLead = await apiClient.leads.create({
        contact_name: name.trim(),
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
        intent,
        property_type: propertyType.trim() || undefined,
        preferred_location: location.trim() || undefined,
        budget_max: budgetMax ? Number(budgetMax) : undefined,
        notes: notes.trim() || undefined,
        status: 'new',
      });
      setLeads([newLead, ...leads]);
      setIsAddOpen(false);
      setName('');
      setEmail('');
      setPhone('');
      setBudgetMax('');
      setPropertyType('');
      setLocation('');
      setNotes('');
      showToast('New lead added to CRM!');
    } catch (err: any) {
      showToast(`Failed to create: ${err.message}`);
    }
  };

  const exportCSV = () => {
    if (leads.length === 0) return;
    const headers = ['Name', 'Phone', 'Email', 'Intent', 'Location', 'Budget Max', 'Score', 'Status', 'Created At'];
    const rows = leads.map((l) => [
      l.contact_name || '',
      l.phone || '',
      l.email || '',
      l.intent,
      l.preferred_location || '',
      l.budget_max || '',
      l.ai_score,
      l.status,
      l.created_at,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `leads_export_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredLeads = useMemo(() => {
    return leads.filter((lead) => {
      const matchesSearch =
        (lead.contact_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (lead.email || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (lead.phone || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (lead.preferred_location || '').toLowerCase().includes(searchTerm.toLowerCase());

      const matchesStatus = statusFilter === 'all' || lead.status === statusFilter;
      const matchesScore = scoreFilter === 'all' || lead.score_category === scoreFilter;

      return matchesSearch && matchesStatus && matchesScore;
    });
  }, [leads, searchTerm, statusFilter, scoreFilter]);

  const stats = useMemo(() => {
    const hot = leads.filter((l) => l.score_category === 'hot').length;
    const warm = leads.filter((l) => l.score_category === 'warm').length;
    const closed = leads.filter((l) => l.status === 'closed').length;
    return { hot, warm, closed, total: leads.length };
  }, [leads]);

  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto font-sans">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#151517] border border-[#F97316]/30 text-[#F97316] px-4 py-3 rounded-xl shadow-2xl backdrop-blur-md">
          {toastMessage}
        </div>
      )}

      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/8">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">CRM Qualified Leads</h2>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#F97316]/10 text-[#F97316] border border-[#F97316]/20">
              Live Pipeline
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time auto-qualified leads extracted by the conversational AI engine.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="secondary" size="sm" onClick={exportCSV}>
            <Download className="w-4 h-4 mr-1.5 text-zinc-400" />
            <span>Export CSV</span>
          </Button>
          <Button variant="primary" size="sm" onClick={() => setIsAddOpen(true)}>
            <Plus className="w-4 h-4 mr-1.5" />
            <span>Add Lead</span>
          </Button>
        </div>
      </div>

      {/* 4 Focused KPI Cards (Identical style to /app Overview) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* KPI 1: Total Leads */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-2">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            <span>Total Pipeline</span>
            <div className="w-8 h-8 rounded-lg bg-[#F97316]/10 flex items-center justify-center text-[#F97316]">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {stats.total}
          </div>
          <div className="mt-2 text-[11px] text-zinc-400">
            <span>Prospective clients captured</span>
          </div>
        </div>

        {/* KPI 2: Hot Leads */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-2">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            <span>Hot Leads (≥85)</span>
            <div className="w-8 h-8 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-400">
              <Flame className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {stats.hot}
          </div>
          <div className="mt-2 text-[11px] text-zinc-400">
            <span>Immediate buyer intent</span>
          </div>
        </div>

        {/* KPI 3: Warm Leads */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-2">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            <span>Warm Leads (70-84)</span>
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {stats.warm}
          </div>
          <div className="mt-2 text-[11px] text-zinc-400">
            <span>Active consideration</span>
          </div>
        </div>

        {/* KPI 4: Closed Won */}
        <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-2">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            <span>Closed Won</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {stats.closed}
          </div>
          <div className="mt-2 text-[11px] text-zinc-400">
            <span>Successfully closed deals</span>
          </div>
        </div>
      </div>

      {/* Search & Filters Bar */}
      <div className="p-3.5 sm:p-4 rounded-xl bg-[#151517] border border-white/8 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search leads by name, email, phone, location..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316]"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={scoreFilter}
            onChange={(e) => setScoreFilter(e.target.value as any)}
            className="px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
          >
            <option value="all">All AI Scores</option>
            <option value="hot">🔥 Hot Leads (≥85)</option>
            <option value="warm">⚡ Warm Leads (70-84)</option>
            <option value="cold">❄️ Cold Leads (&lt;70)</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
          >
            <option value="all">All Statuses</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Qualified</option>
            <option value="lost">Lost</option>
            <option value="closed">Closed</option>
          </select>

          <Button variant="secondary" size="sm" onClick={loadLeads} title="Refresh Leads">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Leads Table */}
      <div className="rounded-xl bg-[#151517] border border-white/8 overflow-hidden shadow-lg">
        <div className="w-full overflow-x-auto">
          <table className="w-full text-left text-xs min-w-[880px]">
            <thead>
              <tr className="border-b border-white/8 text-zinc-400 uppercase tracking-wider text-[11px] bg-white/[0.01]">
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Lead Contact</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Preference & Budget</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">AI Score</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Status Stage</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Date</th>
                <th className="py-3.5 px-6 font-semibold text-right whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading && leads.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-zinc-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto text-[#F97316] mb-2" />
                    <span>Loading leads pipeline...</span>
                  </td>
                </tr>
              ) : filteredLeads.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-zinc-500 text-xs">
                    <div className="flex flex-col items-center justify-center gap-3 max-w-md mx-auto">
                      <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-zinc-400">
                        <Users className="w-6 h-6 text-[#F97316]" />
                      </div>
                      <h4 className="text-sm font-semibold text-white">No CRM Leads Found</h4>
                      <p className="text-xs text-zinc-400 leading-relaxed">
                        When visitors interact with your chat assistant, high-intent buyers and renters are qualified and recorded here in real-time.
                      </p>
                      <div className="flex items-center gap-2 pt-2">
                        <Button variant="secondary" size="sm" onClick={() => setIsAddOpen(true)}>
                          <Plus className="w-3.5 h-3.5 mr-1" />
                          <span>Add Lead Manually</span>
                        </Button>
                      </div>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredLeads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-white/[0.02] transition-colors">
                    {/* Contact */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <div className="font-semibold text-sm text-white">{lead.contact_name || 'Anonymous Prospect'}</div>
                      <div className="text-[11px] text-zinc-400 font-mono mt-1 flex items-center gap-1.5">
                        {lead.phone ? (
                          <>
                            <Phone className="w-3 h-3 text-zinc-500 shrink-0" />
                            <span>{lead.phone}</span>
                          </>
                        ) : (
                          <span className="text-zinc-600">No phone provided</span>
                        )}
                      </div>
                      {lead.email && (
                        <div className="text-[11px] text-zinc-400 mt-0.5 flex items-center gap-1.5">
                          <Mail className="w-3 h-3 text-zinc-500 shrink-0" />
                          <span>{lead.email}</span>
                        </div>
                      )}
                    </td>

                    {/* Preference & Budget */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <div className="font-medium text-zinc-200 capitalize">
                        {lead.intent} {lead.property_type ? `• ${lead.property_type}` : ''}
                      </div>
                      <div className="text-[11px] text-zinc-400 mt-0.5 flex items-center gap-2">
                        {lead.preferred_location && (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-zinc-500 shrink-0" />
                            <span>{lead.preferred_location}</span>
                          </span>
                        )}
                        {lead.budget_max && (
                          <span className="font-mono text-[#F97316]">
                            Up to {lead.currency} {Number(lead.budget_max).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Score Badge */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <div
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-bold text-xs whitespace-nowrap ${
                          lead.score_category === 'hot'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            : lead.score_category === 'warm'
                            ? 'bg-[#F97316]/10 text-[#F97316] border border-[#F97316]/20'
                            : 'bg-zinc-800 text-zinc-400 border border-white/5'
                        }`}
                      >
                        {lead.score_category === 'hot' && <Flame className="w-3 h-3 shrink-0" />}
                        <span>{lead.ai_score}/100</span>
                      </div>
                    </td>

                    {/* Status Select */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <select
                        value={lead.status}
                        onChange={(e) => handleStatusChange(lead.id, e.target.value)}
                        className="px-2.5 py-1 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs font-medium text-zinc-200 focus:outline-none focus:border-[#F97316]"
                      >
                        <option value="new">New</option>
                        <option value="contacted">Contacted</option>
                        <option value="qualified">Qualified</option>
                        <option value="lost">Lost</option>
                        <option value="closed">Closed</option>
                      </select>
                    </td>

                    {/* Date */}
                    <td className="py-4 px-6 whitespace-nowrap text-zinc-400 text-[11px]">
                      {new Date(lead.created_at).toLocaleDateString()}
                    </td>

                    {/* Actions */}
                    <td className="py-4 px-6 text-right whitespace-nowrap">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedLead(lead)}
                        className="text-[#F97316] hover:text-[#EA580C]"
                      >
                        <Sparkles className="w-3.5 h-3.5 mr-1" />
                        <span>Breakdown</span>
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* AI Score Breakdown Modal */}
      {selectedLead && (
        <Modal
          isOpen={!!selectedLead}
          onClose={() => setSelectedLead(null)}
          title="AI Lead Qualification Breakdown"
          description={`Evaluation matrix for ${selectedLead.contact_name || 'Prospect'}`}
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3.5 bg-[#0B0B0D] rounded-xl border border-white/8">
              <span className="text-xs text-zinc-400">Total Qualification Score</span>
              <span className="text-xl font-bold text-[#F97316]">{selectedLead.ai_score} / 100</span>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between items-center py-1.5 border-b border-white/5">
                <span className="text-zinc-400">Budget Clarity (Max 30 pts):</span>
                <span className="font-semibold text-white">{selectedLead.score_breakdown?.budget_score ?? 0} pts</span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-white/5">
                <span className="text-zinc-400">Timeline Urgency (Max 25 pts):</span>
                <span className="font-semibold text-white">{selectedLead.score_breakdown?.timeline_score ?? 0} pts</span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-white/5">
                <span className="text-zinc-400">Buyer Intent (Max 25 pts):</span>
                <span className="font-semibold text-white">{selectedLead.score_breakdown?.intent_score ?? 0} pts</span>
              </div>
              <div className="flex justify-between items-center py-1.5">
                <span className="text-zinc-400">Contact Details (Max 20 pts):</span>
                <span className="font-semibold text-white">{selectedLead.score_breakdown?.contact_score ?? 0} pts</span>
              </div>
            </div>

            {selectedLead.score_breakdown?.rationale && (
              <div className="p-3 bg-[#F97316]/5 border border-[#F97316]/20 rounded-xl text-xs text-zinc-300">
                <strong className="text-[#F97316] block mb-1">AI Analyst Summary:</strong>
                {selectedLead.score_breakdown.rationale}
              </div>
            )}

            {selectedLead.notes && (
              <div className="p-3 bg-[#0B0B0D] border border-white/8 rounded-xl text-xs text-zinc-400">
                <strong className="text-zinc-300 block mb-1">Client Notes:</strong>
                {selectedLead.notes}
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Add Lead Modal */}
      {isAddOpen && (
        <Modal
          isOpen={isAddOpen}
          onClose={() => setIsAddOpen(false)}
          title="Add New Qualified Lead"
          description="Record a prospective real estate client manually into the CRM."
        >
          <form onSubmit={handleAddLead} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                Contact Full Name *
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Tariq Mansoor"
                className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="tariq@example.ae"
                  className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                  Phone Number
                </label>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+971 50 123 4567"
                  className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                  Intent
                </label>
                <select
                  value={intent}
                  onChange={(e) => setIntent(e.target.value as any)}
                  className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
                >
                  <option value="buy">Buy</option>
                  <option value="rent">Rent</option>
                  <option value="invest">Invest</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                  Budget Max (AED)
                </label>
                <input
                  type="number"
                  value={budgetMax}
                  onChange={(e) => setBudgetMax(e.target.value)}
                  placeholder="e.g. 3500000"
                  className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                  Property Type
                </label>
                <input
                  type="text"
                  value={propertyType}
                  onChange={(e) => setPropertyType(e.target.value)}
                  placeholder="e.g. 4-Bed Beach Villa"
                  className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                  Preferred Location
                </label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. Palm Jumeirah"
                  className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                Client Notes
              </label>
              <textarea
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Client specific requirements or timeline..."
                className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button type="button" variant="ghost" size="md" onClick={() => setIsAddOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="md">
                Save Lead
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};
