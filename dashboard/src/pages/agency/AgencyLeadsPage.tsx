import React, { useState } from 'react';
import { Link } from '@tanstack/react-router';
import {
  Search,
  Plus,
  Flame,
  Phone,
  Mail,
  MapPin,
  CheckCircle2,
  FileSpreadsheet,
  MessageSquare,
  Users,
} from 'lucide-react';
import type { Lead, LeadStatus } from '../../types/agency';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';

export const AgencyLeadsPage: React.FC = () => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | LeadStatus>('all');
  const [scoreFilter, setScoreFilter] = useState<'all' | 'hot' | 'warm'>('all');
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // New Lead Form State
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [budget, setBudget] = useState('');
  const [propertyType, setPropertyType] = useState('');
  const [location, setLocation] = useState('');
  const [notes, setNotes] = useState('');

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2500);
  };

  const filteredLeads = leads.filter((lead) => {
    const matchesSearch =
      lead.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.phone.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.property_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.preferred_location.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'all' || lead.status === statusFilter;

    let matchesScore = true;
    if (scoreFilter === 'hot') matchesScore = lead.qualification_score >= 85;
    if (scoreFilter === 'warm')
      matchesScore = lead.qualification_score >= 70 && lead.qualification_score < 85;

    return matchesSearch && matchesStatus && matchesScore;
  });

  const handleStatusChange = (leadId: string, nextStatus: LeadStatus) => {
    setLeads((prev) =>
      prev.map((l) => (l.id === leadId ? { ...l, status: nextStatus } : l))
    );
    showToast('Lead status updated!');
  };

  const handleAddLead = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const newLead: Lead = {
      id: `lead-${Date.now().toString().slice(-4)}`,
      name: name.trim(),
      email: email.trim(),
      phone: phone.trim(),
      budget: budget.trim() || 'Custom Quote',
      property_type: propertyType.trim() || 'Luxury Residential',
      preferred_location: location.trim() || 'Dubai',
      qualification_score: 85,
      status: 'new',
      created_at: 'Just now',
      notes: notes.trim() || 'Manually added to CRM pipeline.',
    };

    setLeads([newLead, ...leads]);
    setIsAddOpen(false);
    setName('');
    setEmail('');
    setPhone('');
    setBudget('');
    setPropertyType('');
    setLocation('');
    setNotes('');
    showToast('New lead added to CRM!');
  };


  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/8">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">CRM Qualified Leads</h2>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#F97316]/10 text-[#F97316] border border-[#F97316]/20">
              {leads.length} Total
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Buyer leads scored automatically by conversational AI.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => showToast('Leads CSV exported to downloads!')}
          >
            <FileSpreadsheet className="w-4 h-4 mr-1.5 text-zinc-400" />
            <span>Export CSV</span>
          </Button>
          <Button variant="primary" size="sm" onClick={() => setIsAddOpen(true)}>
            <Plus className="w-4 h-4 mr-1.5" />
            <span>Add Lead</span>
          </Button>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="p-3.5 sm:p-4 rounded-xl bg-[#151517] border border-white/8 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search leads by name, email, phone, location..."
            className="w-full pl-9 pr-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316]"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Status filter */}
          <div className="flex items-center gap-1 bg-[#0B0B0D] p-1 rounded-lg border border-white/5 overflow-x-auto">
            {(['all', 'new', 'contacted', 'viewing_scheduled'] as const).map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium capitalize transition-colors cursor-pointer shrink-0 ${
                  statusFilter === s
                    ? 'bg-white/10 text-white font-semibold'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {s.replace('_', ' ')}
              </button>
            ))}
          </div>

          {/* Score filter */}
          <select
            value={scoreFilter}
            onChange={(e) => setScoreFilter(e.target.value as any)}
            className="px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
          >
            <option value="all">All AI Scores</option>
            <option value="hot">Hot Intent (Score &ge; 85)</option>
            <option value="warm">Warm Intent (Score 70-84)</option>
          </select>
        </div>
      </div>

      {/* Leads Table */}
      <div className="rounded-xl bg-[#151517] border border-white/8 overflow-hidden shadow-lg">
        <div className="w-full overflow-x-auto">
          <table className="w-full text-left text-xs min-w-[880px]">
            <thead>
              <tr className="border-b border-white/8 text-zinc-400 uppercase tracking-wider text-[11px] bg-white/[0.01]">
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Lead Contact</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Property Interest</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Budget Tier</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">AI Score</th>
                <th className="py-3.5 px-6 font-semibold whitespace-nowrap">Status Stage</th>
                <th className="py-3.5 px-6 font-semibold text-right whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredLeads.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-zinc-500 text-xs">
                    <div className="flex flex-col items-center justify-center gap-3 max-w-md mx-auto">
                      <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-zinc-400">
                        <Users className="w-6 h-6 text-[#F97316]" />
                      </div>
                      <h4 className="text-sm font-semibold text-white">No CRM Leads Captured Yet</h4>
                      <p className="text-xs text-zinc-400 leading-relaxed">
                        When visitors interact with your web chat widget, the AI automatically qualifies their buyer intent, captures contact info (phone, email), budget tier, and preferred properties.
                      </p>
                      <div className="flex items-center gap-2 pt-2">
                        <Button variant="secondary" size="sm" onClick={() => setIsAddOpen(true)}>
                          <Plus className="w-3.5 h-3.5 mr-1" />
                          <span>Add Lead Manually</span>
                        </Button>
                        <Link to="/app/conversations">
                          <Button variant="primary" size="sm">
                            <MessageSquare className="w-3.5 h-3.5 mr-1" />
                            <span>View Live Conversations</span>
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredLeads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-white/[0.02] transition-colors">
                    {/* Contact (Name, Phone below, Email below) */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <div className="font-semibold text-sm text-white">{lead.name}</div>
                      <div className="text-[11px] text-zinc-400 font-mono mt-1 flex items-center gap-1.5">
                        <Phone className="w-3 h-3 text-zinc-500 shrink-0" />
                        <span>{lead.phone}</span>
                      </div>
                      <div className="text-[11px] text-zinc-400 mt-0.5 flex items-center gap-1.5">
                        <Mail className="w-3 h-3 text-zinc-500 shrink-0" />
                        <span>{lead.email}</span>
                      </div>
                    </td>

                    {/* Property Interest */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <div className="font-medium text-zinc-200">{lead.property_type}</div>
                      <div className="text-[11px] text-zinc-400 mt-0.5 flex items-center gap-1.5">
                        <MapPin className="w-3 h-3 text-zinc-500 shrink-0" />
                        <span>{lead.preferred_location}</span>
                      </div>
                    </td>

                    {/* Budget Tier */}
                    <td className="py-4 px-6 whitespace-nowrap font-mono text-zinc-200 font-medium">
                      <span className="bg-[#0B0B0D] px-2.5 py-1 rounded border border-white/5 text-[11px] text-emerald-400 inline-block">
                        {lead.budget}
                      </span>
                    </td>

                    {/* Score */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 font-bold text-xs whitespace-nowrap shrink-0">
                        <Flame className="w-3 h-3 shrink-0" />
                        <span>{lead.qualification_score}/100</span>
                      </div>
                    </td>

                    {/* Status Dropdown */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <select
                        value={lead.status}
                        onChange={(e) => handleStatusChange(lead.id, e.target.value as LeadStatus)}
                        className="px-2.5 py-1 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs font-medium text-zinc-200 focus:outline-none focus:border-[#F97316]"
                      >
                        <option value="new">New</option>
                        <option value="contacted">Contacted</option>
                        <option value="viewing_scheduled">Viewing Scheduled</option>
                        <option value="closed">Closed / Won</option>
                      </select>
                    </td>

                    {/* Actions */}
                    <td className="py-4 px-6 text-right whitespace-nowrap">
                      <Link to="/app/conversations">
                        <Button
                          variant="secondary"
                          size="sm"
                          title="View AI Chat Transcript"
                        >
                          <MessageSquare className="w-3.5 h-3.5 text-zinc-400 mr-1 shrink-0" />
                          <span>Transcript</span>
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ADD LEAD MODAL */}
      <Modal
        isOpen={isAddOpen}
        onClose={() => setIsAddOpen(false)}
        title="Add New Qualified Lead"
        description="Manually record a prospective real estate buyer into the agency CRM pipeline."
      >
        <form onSubmit={handleAddLead} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
              Buyer Full Name
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Rashid Al-Ghurair"
              className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-[#F97316]"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="rashid@holdings.ae"
                className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-[#F97316]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                Phone Number
              </label>
              <input
                type="text"
                required
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+971 50 123 4567"
                className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-[#F97316]"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                Budget Tier
              </label>
              <input
                type="text"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="e.g. 12,000,000 AED"
                className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-[#F97316]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                Preferred Area
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Palm Jumeirah, Downtown"
                className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-[#F97316]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
              Property Type & Requirements
            </label>
            <input
              type="text"
              value={propertyType}
              onChange={(e) => setPropertyType(e.target.value)}
              placeholder="e.g. 4-Bed Beach Villa, High floor penthouse"
              className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-[#F97316]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
              Agent Notes
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any specific client requirements or timeline..."
              className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-[#F97316]"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              type="button"
              variant="ghost"
              size="md"
              onClick={() => setIsAddOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="md">
              Save Lead to Pipeline
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
