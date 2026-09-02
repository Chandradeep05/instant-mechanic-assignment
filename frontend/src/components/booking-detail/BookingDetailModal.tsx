import React, { useState, useEffect } from 'react';
import {
  X,
  User,
  Car,
  Wrench,
  Clock,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  Shield,
  Send,
  UserPlus,
  FileText,
} from 'lucide-react';
import { api } from '../../api/client';
import { BookingDetail, BookingStatus, Mechanic } from '../../types';
import { StatusBadge, OperationalStatusBadge } from '../ui/Badge';
import { TableSkeleton } from '../ui/LoadingSkeleton';
import { ErrorState } from '../ui/ErrorState';

interface BookingDetailModalProps {
  bookingId: number | null;
  onClose: () => void;
  onBookingUpdated: () => void;
}

// Statuses where mechanic reassignment is blocked by the backend
const REASSIGNMENT_BLOCKED_STATUSES: BookingStatus[] = ['ON_THE_WAY', 'ARRIVED', 'IN_PROGRESS'];

export const BookingDetailModal: React.FC<BookingDetailModalProps> = ({
  bookingId,
  onClose,
  onBookingUpdated,
}) => {
  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [mechanics, setMechanics] = useState<Mechanic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Transition form state
  const [selectedNextStatus, setSelectedNextStatus] = useState<BookingStatus | ''>('');
  const [transitionNotes, setTransitionNotes] = useState('');
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Assignment form state
  const [selectedMechanicId, setSelectedMechanicId] = useState<number | ''>('');
  const [assignNotes, setAssignNotes] = useState('');
  const [isAssigning, setIsAssigning] = useState(false);

  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchDetail = async () => {
    if (!bookingId) return;
    try {
      setLoading(true);
      setError(null);

      // Fetch booking detail and ALL mechanics (page_size=100 to ensure all 25 are included).
      // The assignment dropdown must show every mechanic, not just page 1 of paginated results.
      const [detailRes, mechRes] = await Promise.all([
        api.getBookingDetail(bookingId),
        api.getMechanics({ page_size: 100 } as any),
      ]);

      setBooking(detailRes);
      if (detailRes.allowed_transitions.length > 0) {
        setSelectedNextStatus(detailRes.allowed_transitions[0]);
      } else {
        setSelectedNextStatus('');
      }

      const mechsList = Array.isArray(mechRes) ? mechRes : (mechRes as any).results || [];
      setMechanics(mechsList);
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.message || 'Failed to load booking details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [bookingId]);

  if (!bookingId) return null;

  const handleTransitionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedNextStatus || !booking) return;

    try {
      setIsTransitioning(true);
      setError(null);
      const updated = await api.transitionBooking(booking.id, selectedNextStatus as BookingStatus, transitionNotes);
      setBooking(updated);
      setTransitionNotes('');
      if (updated.allowed_transitions.length > 0) {
        setSelectedNextStatus(updated.allowed_transitions[0]);
      } else {
        setSelectedNextStatus('');
      }
      setActionSuccess(`Status transitioned to ${updated.status} successfully!`);
      onBookingUpdated();
      setTimeout(() => setActionSuccess(null), 3500);
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.message || 'Transition failed.');
    } finally {
      setIsTransitioning(false);
    }
  };

  const handleAssignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMechanicId || !booking) return;

    try {
      setIsAssigning(true);
      setError(null);
      const updated = await api.assignMechanic(booking.id, Number(selectedMechanicId), assignNotes);
      setBooking(updated);
      setAssignNotes('');
      setSelectedMechanicId('');
      setActionSuccess(`Mechanic assigned successfully!`);
      onBookingUpdated();
      setTimeout(() => setActionSuccess(null), 3500);
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.message || 'Assignment failed.');
    } finally {
      setIsAssigning(false);
    }
  };

  const isTerminal = booking?.status === 'COMPLETED' || booking?.status === 'CANCELLED';

  // Hide the assignment panel when the backend will reject reassignment anyway
  const canAssignMechanic = booking && !isTerminal &&
    !REASSIGNMENT_BLOCKED_STATUSES.includes(booking.status as BookingStatus);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6">
      <div className="bg-surface border border-surface-border rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-border bg-surface-light/40">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xl font-extrabold text-orange-400">
              {booking?.booking_number || 'Booking Details'}
            </span>
            {booking && <StatusBadge status={booking.status} />}
            {booking?.is_demo_scenario && (
              <span className="px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800 text-[11px] font-semibold">
                Live Scenario Item
              </span>
            )}
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-light transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {actionSuccess && (
            <div className="p-3 bg-emerald-950/70 border border-emerald-800 rounded-xl text-emerald-300 text-xs font-semibold flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-400" />
              {actionSuccess}
            </div>
          )}

          {error && <ErrorState message={error} onRetry={fetchDetail} />}

          {loading || !booking ? (
            <TableSkeleton rows={4} cols={3} />
          ) : (
            <>
              {/* Top Entities Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Customer Info */}
                <div className="bg-surface-light/40 rounded-xl p-4 border border-surface-border">
                  <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
                    <User className="w-4 h-4 text-orange-400" />
                    Customer Details
                  </div>
                  <div className="text-sm font-bold text-white">{booking.customer.name}</div>
                  <div className="text-xs text-slate-300 font-mono mt-0.5">{booking.customer.phone}</div>
                  <div className="text-xs text-slate-400 mt-0.5 truncate">{booking.customer.email || 'No email registered'}</div>
                </div>

                {/* Vehicle Info */}
                <div className="bg-surface-light/40 rounded-xl p-4 border border-surface-border">
                  <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
                    <Car className="w-4 h-4 text-blue-400" />
                    Vehicle Details
                  </div>
                  <div className="text-sm font-bold text-white">
                    {booking.vehicle.make} {booking.vehicle.model}
                  </div>
                  <div className="text-xs font-mono text-orange-300 mt-0.5 font-bold">
                    {booking.vehicle.registration_number}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5 uppercase tracking-wider">
                    {booking.vehicle.vehicle_type}
                  </div>
                </div>

                {/* Service & Pricing */}
                <div className="bg-surface-light/40 rounded-xl p-4 border border-surface-border">
                  <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
                    <Wrench className="w-4 h-4 text-emerald-400" />
                    Service & Pricing
                  </div>
                  <div className="text-sm font-bold text-white">{booking.service_category.name}</div>
                  <div className="text-xs font-mono text-emerald-400 font-bold mt-0.5">
                    Amount: ₹{Number(booking.amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5 truncate">
                    {booking.service_category.description || 'Standard rate applied'}
                  </div>
                </div>
              </div>

              {/* Operations Control Actions Box */}
              {!isTerminal && (
                <div className={`grid grid-cols-1 ${canAssignMechanic ? 'md:grid-cols-2' : ''} gap-4 bg-surface-light/20 p-4 rounded-xl border border-surface-border`}>
                  {/* Status Transition Control */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-1.5">
                      <ArrowRight className="w-4 h-4 text-orange-400" />
                      Advance Lifecycle State
                    </h4>
                    {booking.allowed_transitions.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No further status transitions permitted.</p>
                    ) : (
                      <form onSubmit={handleTransitionSubmit} className="space-y-2.5">
                        <div className="flex gap-2">
                          <select
                            value={selectedNextStatus}
                            onChange={(e) => setSelectedNextStatus(e.target.value as BookingStatus)}
                            className="flex-1 bg-surface-light border border-surface-border rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-orange-500 font-mono"
                          >
                            {booking.allowed_transitions.map((st) => (
                              <option key={st} value={st}>
                                Transition to: {st}
                              </option>
                            ))}
                          </select>

                          <button
                            type="submit"
                            disabled={isTransitioning || !selectedNextStatus}
                            className="px-3 py-1.5 bg-orange-600 hover:bg-orange-500 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 inline-flex items-center gap-1.5 shadow-sm"
                          >
                            <Send className="w-3.5 h-3.5" />
                            {isTransitioning ? 'Updating...' : 'Execute'}
                          </button>
                        </div>
                        <input
                          type="text"
                          value={transitionNotes}
                          onChange={(e) => setTransitionNotes(e.target.value)}
                          placeholder="Optional transition notes..."
                          className="w-full bg-surface-light border border-surface-border rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-orange-500"
                        />
                      </form>
                    )}
                  </div>

                  {/* Mechanic Assignment Control — hidden when backend rejects reassignment */}
                  {canAssignMechanic && (
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-1.5">
                        <UserPlus className="w-4 h-4 text-blue-400" />
                        {booking.mechanic ? 'Reassign Mechanic' : 'Assign Mechanic'}
                      </h4>
                      <form onSubmit={handleAssignSubmit} className="space-y-2.5">
                        <div className="flex gap-2">
                          <select
                            value={selectedMechanicId}
                            onChange={(e) => setSelectedMechanicId(e.target.value ? Number(e.target.value) : '')}
                            className="flex-1 bg-surface-light border border-surface-border rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-orange-500"
                          >
                            <option value="">Select Mechanic...</option>
                            {mechanics
                              .filter((m) => m.availability_status !== 'OFFLINE')
                              .map((m) => (
                                <option key={m.id} value={m.id}>
                                  {m.name} ({m.operational_status} • {m.active_jobs_count} jobs)
                                </option>
                              ))}
                          </select>

                          <button
                            type="submit"
                            disabled={isAssigning || !selectedMechanicId}
                            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 inline-flex items-center gap-1.5 shadow-sm"
                          >
                            <UserPlus className="w-3.5 h-3.5" />
                            {isAssigning ? 'Assigning...' : 'Assign'}
                          </button>
                        </div>
                        <input
                          type="text"
                          value={assignNotes}
                          onChange={(e) => setAssignNotes(e.target.value)}
                          placeholder="Optional assignment notes..."
                          className="w-full bg-surface-light border border-surface-border rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-orange-500"
                        />
                      </form>
                    </div>
                  )}
                </div>
              )}

              {/* Status History Timeline (Audit Requirement) */}
              <div>
                <h4 className="text-sm font-bold text-white tracking-tight mb-3 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-orange-400" />
                  Status History & Dispatch Audit Trail
                </h4>

                <div className="bg-surface-light/30 rounded-xl p-4 border border-surface-border">
                  {booking.status_history.length === 0 ? (
                    <p className="text-xs text-slate-400">No transition history recorded yet.</p>
                  ) : (
                    <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-700">
                      {booking.status_history.map((hist, index) => {
                        const isLatest = index === booking.status_history.length - 1;
                        return (
                          <div key={hist.id} className="relative group">
                            {/* Dot */}
                            <span
                              className={`absolute -left-6 top-1 w-2.5 h-2.5 rounded-full border-2 ${
                                isLatest
                                  ? 'bg-orange-500 border-orange-300 ring-4 ring-orange-500/20'
                                  : 'bg-slate-600 border-slate-400'
                              }`}
                            />

                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                              <div className="flex items-center gap-2">
                                <span className="font-mono text-xs font-bold text-slate-300">
                                  {hist.previous_status}
                                </span>
                                <ArrowRight className="w-3 h-3 text-slate-500" />
                                <StatusBadge status={hist.new_status as BookingStatus} size="sm" />
                              </div>

                              <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                                <span className="px-1.5 py-0.5 rounded bg-surface text-slate-300 text-[10px] font-semibold border border-surface-border">
                                  {hist.changed_by}
                                </span>
                                <span>{new Date(hist.changed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                              </div>
                            </div>

                            {hist.notes && (
                              <p className="text-xs text-slate-400 mt-1 pl-1 italic">"{hist.notes}"</p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-surface-border bg-surface-light/40 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-surface-light hover:bg-surface-lighter text-slate-200 text-xs font-semibold rounded-lg border border-surface-border transition-colors"
          >
            Close Drawer
          </button>
        </div>
      </div>
    </div>
  );
};
