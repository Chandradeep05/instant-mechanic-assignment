import React, { useState, useEffect } from 'react';
import { Search, User, Car, DollarSign, Calendar, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../../api/client';
import { Customer } from '../../types';
import { TableSkeleton } from '../ui/LoadingSkeleton';
import { ErrorState } from '../ui/ErrorState';

export const CustomersList: React.FC = () => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCustomers = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getCustomers({ page, search: search || undefined });
      setCustomers(res.results);
      setTotalCount(res.count);
    } catch (err: any) {
      setError(err.message || 'Failed to load customers.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, [page, search]);

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Customer Directory</h2>
          <p className="text-xs text-slate-400">
            Customer lifetime value, registered vehicles, and booking history.
          </p>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by name, phone, email..."
            className="w-full bg-surface border border-surface-border rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-orange-500"
          />
        </div>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={fetchCustomers} />
      ) : loading ? (
        <TableSkeleton rows={8} cols={6} />
      ) : (
        <div className="bg-surface rounded-xl border border-surface-border overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-surface-light/50 border-b border-surface-border text-slate-400 font-semibold uppercase tracking-wider">
                  <th className="py-3.5 px-4">Customer</th>
                  <th className="py-3.5 px-4">Contact</th>
                  <th className="py-3.5 px-4">Registered Vehicles</th>
                  <th className="py-3.5 px-4">Total Bookings</th>
                  <th className="py-3.5 px-4">Lifetime Spend</th>
                  <th className="py-3.5 px-4">Last Booking Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {customers.map((c) => (
                  <tr key={c.id} className="hover:bg-surface-light/40 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-100 flex items-center gap-2">
                        <User className="w-3.5 h-3.5 text-orange-400" />
                        {c.name}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-mono text-slate-300">{c.phone}</div>
                      <div className="text-slate-400 text-[11px] truncate max-w-xs">{c.email || 'No email'}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1.5 max-w-xs">
                        {c.vehicles.map((v) => (
                          <span
                            key={v.id}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-light border border-surface-border text-slate-300 text-[11px]"
                          >
                            <Car className="w-3 h-3 text-slate-400" />
                            {v.make} {v.model} ({v.registration_number})
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-200">{c.total_bookings}</td>
                    <td className="py-3 px-4 font-mono font-bold text-emerald-400">
                      ₹{Number(c.lifetime_value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                      {c.last_booking_date ? new Date(c.last_booking_date).toLocaleDateString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between p-4 border-t border-surface-border bg-surface-light/20 text-xs text-slate-400">
            <div>
              Showing <span className="font-semibold text-white">{(page - 1) * pageSize + 1}</span> to{' '}
              <span className="font-semibold text-white">{Math.min(page * pageSize, totalCount)}</span> of{' '}
              <span className="font-semibold text-white">{totalCount}</span> customers
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-light hover:bg-surface-lighter text-slate-200 border border-surface-border disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Previous
              </button>
              <span className="font-mono text-slate-300">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-light hover:bg-surface-lighter text-slate-200 border border-surface-border disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
