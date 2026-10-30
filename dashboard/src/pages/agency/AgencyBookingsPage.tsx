import React, { useState, useEffect, useCallback } from 'react';
import {
  Calendar,
  Clock,
  Phone,
  Home,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Search,
  Filter,
  RefreshCw,
  Bot,
} from 'lucide-react';
import { apiClient, type BackendBooking } from '../../api/client';
import { AgentSocketClient } from '../../api/agentSocket';

export const AgencyBookingsPage: React.FC = () => {
  const [bookings, setBookings] = useState<BackendBooking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [selectedBooking, setSelectedBooking] = useState<BackendBooking | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [liveAlert, setLiveAlert] = useState<string | null>(null);

  const fetchBookings = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.bookings.list({
        status: statusFilter === 'all' ? undefined : statusFilter,
        search: search.trim() || undefined,
        size: 50,
      });
      setBookings(res.items);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch bookings.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search]);

  useEffect(() => {
    fetchBookings();
  }, [fetchBookings]);

  // Real-time socket listener for incoming AI bookings
  useEffect(() => {
    const socket = new AgentSocketClient({
      onBookingCreated: (newBooking: BackendBooking) => {
        setBookings((prev) => [newBooking, ...prev]);
        setLiveAlert(`New Viewing Booked for ${newBooking.visitor_name} (${newBooking.property_ref || 'Property'})`);
        setTimeout(() => setLiveAlert(null), 7000);
      },
      onBookingUpdated: (updated: BackendBooking) => {
        setBookings((prev) => prev.map((b) => (b.id === updated.id ? updated : b)));
      },
    });

    socket.connect();
    return () => socket.disconnect();
  }, []);

  const handleUpdateStatus = async (id: string, newStatus: 'confirmed' | 'canceled') => {
    try {
      setUpdatingId(id);
      let updated: BackendBooking;
      if (newStatus === 'canceled') {
        updated = await apiClient.bookings.cancel(id, 'Canceled from agency dashboard');
      } else {
        updated = await apiClient.bookings.update(id, { status: newStatus });
      }
      setBookings((prev) => prev.map((b) => (b.id === id ? updated : b)));
      if (selectedBooking?.id === id) {
        setSelectedBooking(updated);
      }
    } catch (err: any) {
      alert(`Error updating booking: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'confirmed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" /> Confirmed
          </span>
        );
      case 'canceled':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" /> Canceled
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-3.5 h-3.5" /> Pending Confirmation
          </span>
        );
    }
  };

  const formatDateTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Real-time alert pill */}
      {liveAlert && (
        <div className="bg-emerald-950/80 border border-emerald-500/30 text-emerald-200 px-4 py-3 rounded-xl flex items-center justify-between animate-in fade-in slide-in-from-top duration-300">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
            <p className="text-sm font-medium">{liveAlert}</p>
          </div>
          <button onClick={() => setLiveAlert(null)} className="text-xs text-emerald-400 hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Header & KPI Summary */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Calendar className="w-6 h-6 text-indigo-400" />
            Viewing Appointments
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Property viewings booked autonomously by AI Agent & visitor requests.
          </p>
        </div>
        <button
          onClick={fetchBookings}
          className="flex items-center gap-2 px-3.5 py-2 bg-zinc-900 border border-white/10 rounded-lg text-sm text-zinc-300 hover:text-white hover:bg-zinc-800 transition"
        >
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Filters & Search */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-zinc-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search visitor, phone, property..."
            className="w-full bg-[#121216] border border-white/10 rounded-xl pl-9 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-zinc-400 shrink-0" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full bg-[#121216] border border-white/10 rounded-xl px-3 py-2.5 text-sm text-zinc-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="confirmed">Confirmed</option>
            <option value="canceled">Canceled</option>
          </select>
        </div>

        <div className="flex items-center justify-end text-xs text-zinc-400">
          Showing <span className="font-semibold text-white mx-1">{bookings.length}</span> viewing appointments
        </div>
      </div>

      {/* Table & Details Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Bookings List */}
        <div className="lg:col-span-2 bg-[#0F0F12] border border-white/8 rounded-2xl overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-zinc-500 text-sm">Loading appointments...</div>
          ) : error ? (
            <div className="p-8 text-center text-rose-400 text-sm flex items-center justify-center gap-2">
              <AlertCircle className="w-4 h-4" /> {error}
            </div>
          ) : bookings.length === 0 ? (
            <div className="p-12 text-center text-zinc-500 text-sm">
              No viewing appointments found matching criteria.
            </div>
          ) : (
            <div className="divide-y divide-white/5 overflow-x-auto">
              {bookings.map((booking) => {
                const isSelected = selectedBooking?.id === booking.id;
                return (
                  <div
                    key={booking.id}
                    onClick={() => setSelectedBooking(booking)}
                    className={`p-4 transition cursor-pointer flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
                      isSelected ? 'bg-indigo-600/10 border-l-4 border-indigo-500' : 'hover:bg-white/[0.02]'
                    }`}
                  >
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-white truncate">{booking.visitor_name}</span>
                        {booking.source === 'ai_agent' && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium uppercase px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                            <Bot className="w-3 h-3" /> AI Booked
                          </span>
                        )}
                        {getStatusBadge(booking.status)}
                      </div>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-400">
                        <span className="flex items-center gap-1">
                          <Phone className="w-3.5 h-3.5" /> {booking.phone}
                        </span>
                        {booking.property_ref && (
                          <span className="flex items-center gap-1 truncate max-w-xs text-zinc-300">
                            <Home className="w-3.5 h-3.5 text-indigo-400" /> {booking.property_ref}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <div className="text-xs font-medium text-white flex items-center gap-1 justify-end">
                        <Clock className="w-3.5 h-3.5 text-zinc-400" />
                        {formatDateTime(booking.preferred_time)}
                      </div>
                      <span className="text-[11px] text-zinc-500">
                        Ref: {booking.id.slice(0, 8)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Booking Detail Card */}
        <div className="bg-[#0F0F12] border border-white/8 rounded-2xl p-5 space-y-5 h-fit sticky top-6">
          {selectedBooking ? (
            <>
              <div className="flex items-center justify-between pb-4 border-b border-white/8">
                <div>
                  <h3 className="font-bold text-base text-white">{selectedBooking.visitor_name}</h3>
                  <p className="text-xs text-zinc-400 mt-0.5">Booking Details & Actions</p>
                </div>
                {getStatusBadge(selectedBooking.status)}
              </div>

              <div className="space-y-3.5 text-sm">
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Appointment Time</label>
                  <div className="mt-1 flex items-center gap-2 text-white font-medium bg-zinc-900/60 p-2.5 rounded-lg border border-white/5">
                    <Calendar className="w-4 h-4 text-indigo-400" />
                    {formatDateTime(selectedBooking.preferred_time)}
                  </div>
                </div>

                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Target Property</label>
                  <p className="text-white mt-1 bg-zinc-900/60 p-2.5 rounded-lg border border-white/5">
                    {selectedBooking.property_ref || 'General Property Viewing Inquiry'}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Phone</label>
                    <p className="text-white mt-1 text-xs truncate bg-zinc-900/60 p-2 rounded-lg border border-white/5">
                      {selectedBooking.phone}
                    </p>
                  </div>
                  <div>
                    <label className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Email</label>
                    <p className="text-white mt-1 text-xs truncate bg-zinc-900/60 p-2 rounded-lg border border-white/5">
                      {selectedBooking.email || 'N/A'}
                    </p>
                  </div>
                </div>

                {selectedBooking.notes && (
                  <div>
                    <label className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Notes</label>
                    <p className="text-zinc-300 text-xs mt-1 bg-zinc-900/60 p-2.5 rounded-lg border border-white/5">
                      {selectedBooking.notes}
                    </p>
                  </div>
                )}
              </div>

              {/* Status Action Buttons */}
              <div className="pt-4 border-t border-white/8 space-y-2">
                {selectedBooking.status === 'pending' && (
                  <button
                    disabled={updatingId === selectedBooking.id}
                    onClick={() => handleUpdateStatus(selectedBooking.id, 'confirmed')}
                    className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-medium transition flex items-center justify-center gap-2"
                  >
                    <CheckCircle2 className="w-4 h-4" /> Confirm Appointment
                  </button>
                )}
                {selectedBooking.status !== 'canceled' && (
                  <button
                    disabled={updatingId === selectedBooking.id}
                    onClick={() => handleUpdateStatus(selectedBooking.id, 'canceled')}
                    className="w-full py-2.5 px-4 bg-zinc-900 hover:bg-rose-950/40 text-rose-400 border border-white/10 hover:border-rose-500/30 rounded-xl text-sm font-medium transition flex items-center justify-center gap-2"
                  >
                    <XCircle className="w-4 h-4" /> Cancel Appointment
                  </button>
                )}
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-zinc-500 text-sm">
              Select an appointment from the list to view contact details, schedule time, and confirm.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

