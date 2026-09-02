import React, { useState, useEffect, useCallback } from 'react';
import { Search, Wrench, Star, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react';
import { api } from '../../api/client';
import { Mechanic } from '../../types';
import { OperationalStatusBadge, WorkloadBadgeComponent } from '../ui/Badge';
import { TableSkeleton } from '../ui/LoadingSkeleton';
import { ErrorState } from '../ui/ErrorState';

interface MechanicsListProps {
  onSelectBooking: (bookingId: number) => void;
  refreshTrigger?: number;
}

const PAGE_SIZE = 20;

export const MechanicsList: React.FC<MechanicsListProps> = ({ onSelectBooking, refreshTrigger = 0 }) => {
  const [mechanics, setMechanics] = useState<Mechanic[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMechanics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getMechanics({ search: search || undefined, page } as any);
      // Handle both paginated and flat array responses
      if (Array.isArray(res)) {
        setMechanics(res);
        setTotalCount(res.length);
      } else {
        const paginated = res as any;
        setMechanics(paginated.results || []);
        setTotalCount(paginated.count || 0);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load mechanics.');
    } finally {
      setLoading(false);
    }
  }, [search, page, refreshTrigger]);

  useEffect(() => {
    fetchMechanics();
  }, [fetchMechanics]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Mechanics &amp; Workload Fleet</h2>
          <p className="text-xs text-slate-400">
            Real-time fleet availability, derived operational workload, and active job assignments.
          </p>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search mechanics by name or phone..."
            className="w-full bg-surface border border-surface-border rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-orange-500"
          />
        </div>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={fetchMechanics} />
      ) : loading ? (
        <TableSkeleton rows={8} cols={6} />
      ) : (
        <>
          <div className="bg-surface rounded-xl border border-surface-border overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-surface-light/50 border-b border-surface-border text-slate-400 font-semibold uppercase tracking-wider">
                    <th className="py-3.5 px-4">Mechanic</th>
                    <th className="py-3.5 px-4">Phone</th>
                    <th className="py-3.5 px-4">Operational Status</th>
                    <th className="py-3.5 px-4">Workload Tier</th>
                    <th className="py-3.5 px-4">Active Jobs</th>
                    <th className="py-3.5 px-4">Completed Jobs</th>
                    <th className="py-3.5 px-4">Rating</th>
                    <th className="py-3.5 px-4">Current Primary Booking</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {mechanics.map((mech) => {
                    const isOverloaded = mech.workload_badge === 'OVERLOADED';
                    return (
                      <tr
                        key={mech.id}
                        className={`hover:bg-surface-light/40 transition-colors ${
                          isOverloaded ? 'bg-red-950/15' : ''
                        }`}
                      >
                        <td className="py-3 px-4">
                          <div className="font-bold text-slate-100 flex items-center gap-2">
                            <Wrench className="w-3.5 h-3.5 text-orange-400" />
                            {mech.name}
                          </div>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">{mech.phone}</td>
                        <td className="py-3 px-4">
                          <OperationalStatusBadge status={mech.operational_status} />
                        </td>
                        <td className="py-3 px-4">
                          <WorkloadBadgeComponent badge={mech.workload_badge} count={mech.active_jobs_count} />
                        </td>
                        <td className="py-3 px-4 font-mono font-bold">
                          <span className={mech.active_jobs_count >= 4 ? 'text-red-400 font-extrabold' : 'text-slate-200'}>
                            {mech.active_jobs_count}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">{mech.total_jobs_completed}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-1 text-amber-400 font-mono font-semibold">
                            <Star className="w-3 h-3 fill-current" />
                            {mech.rating}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          {mech.primary_booking ? (
                            <button
                              onClick={() => onSelectBooking(mech.primary_booking!.id)}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-light hover:bg-orange-600 hover:text-white text-orange-400 text-xs font-mono font-semibold transition-colors border border-surface-border"
                            >
                              <span>{mech.primary_booking.booking_number}</span>
                              <span className="text-[10px] text-slate-300">({mech.primary_booking.status})</span>
                              <ExternalLink className="w-3 h-3 ml-1" />
                            </button>
                          ) : (
                            <span className="text-slate-500 italic">None</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Server-side Pagination Footer */}
          {totalCount > PAGE_SIZE && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 border border-surface-border rounded-xl bg-surface-light/20 text-xs text-slate-400">
              <div>
                Showing <span className="font-semibold text-white">{(page - 1) * PAGE_SIZE + 1}</span> to{' '}
                <span className="font-semibold text-white">{Math.min(page * PAGE_SIZE, totalCount)}</span> of{' '}
                <span className="font-semibold text-white">{totalCount}</span> mechanics
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-light hover:bg-surface-lighter text-slate-200 border border-surface-border disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  Previous
                </button>
                <span className="font-mono px-2 font-medium text-slate-300">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-light hover:bg-surface-lighter text-slate-200 border border-surface-border disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
