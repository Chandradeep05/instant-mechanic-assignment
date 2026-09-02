import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
  UserCheck,
  RotateCcw,
  Plus,
} from 'lucide-react';
import { api } from '../../api/client';
import { BookingListItem, BookingStatus, ServiceCategory, PaginatedResponse } from '../../types';
import { StatusBadge } from '../ui/Badge';
import { TableSkeleton } from '../ui/LoadingSkeleton';
import { ErrorState } from '../ui/ErrorState';
import { EmptyState } from '../ui/EmptyState';
import { CreateBookingModal } from './CreateBookingModal';

interface BookingsTableProps {
  initialStatusFilter?: string;
  onSelectBooking: (bookingId: number) => void;
  refreshTrigger?: number;
}

export const BookingsTable: React.FC<BookingsTableProps> = ({
  initialStatusFilter = '',
  onSelectBooking,
  refreshTrigger = 0,
}) => {
  const [bookings, setBookings] = useState<BookingListItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>(initialStatusFilter);
  const [serviceFilter, setServiceFilter] = useState<number | undefined>(undefined);
  const [ordering, setOrdering] = useState<string>('-created_at');

  const [services, setServices] = useState<ServiceCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  useEffect(() => {
    if (initialStatusFilter !== undefined) {
      setStatusFilter(initialStatusFilter);
      setPage(1);
    }
  }, [initialStatusFilter]);

  // Load service categories for filter dropdown
  useEffect(() => {
    api.getServiceCategories().then(setServices).catch(console.error);
  }, []);

  const fetchBookings = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getBookings({
        page,
        status: statusFilter || undefined,
        service_category: serviceFilter || undefined,
        search: search || undefined,
        ordering,
      });

      setBookings(res.results);
      setTotalCount(res.count);
    } catch (err: any) {
      setError(err.message || 'Failed to load bookings list.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBookings();
  }, [page, statusFilter, serviceFilter, ordering, refreshTrigger]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchBookings();
  };

  const handleResetFilters = () => {
    setSearch('');
    setStatusFilter('');
    setServiceFilter(undefined);
    setOrdering('-created_at');
    setPage(1);
  };

  const handleExportCSV = () => {
    if (!bookings.length) return;

    const escapeCSVField = (value: unknown): string => {
      const str = String(value ?? '');
      // Prefix formula-starting chars to prevent spreadsheet injection
      const safe = /^[=+\-@]/.test(str) ? `'${str}` : str;
      // Escape embedded double-quotes by doubling them, then wrap the whole field
      return `"${safe.replace(/"/g, '""')}"`;
    };

    const headers = ['Booking Number', 'Status', 'Amount', 'Customer', 'Phone', 'Vehicle', 'Service', 'Mechanic', 'Created At'];
    const rows = bookings.map((b) => [
      b.booking_number,
      b.status,
      b.amount,
      b.customer_name,
      b.customer_phone,
      b.vehicle_info,
      b.service_name,
      b.mechanic_name || 'Unassigned',
      b.created_at,
    ].map(escapeCSVField));

    const csvContent = 'data:text/csv;charset=utf-8,'
      + [headers.map(escapeCSVField).join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `liveops-bookings-page-${page}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div className="space-y-4">
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Bookings & Dispatch Table</h2>
          <p className="text-xs text-slate-400">
            Real-time server-side paginated list with granular status, service, and text filters.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-orange-500 hover:bg-orange-600 text-white transition-colors shadow-sm shadow-orange-500/20"
          >
            <Plus className="w-3.5 h-3.5" />
            New Booking
          </button>
          <button
            onClick={handleExportCSV}
            disabled={loading || bookings.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-light hover:bg-surface-lighter text-slate-200 border border-surface-border transition-colors disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-surface rounded-xl border border-surface-border p-4 shadow-sm">
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Search Input */}
          <div className="lg:col-span-2 relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search booking #, customer, phone, vehicle, mechanic..."
              className="w-full bg-surface-light/80 border border-surface-border rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-orange-500 transition-colors"
            />
          </div>

          {/* Status Filter */}
          <div>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-surface-light/80 border border-surface-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500"
            >
              <option value="">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="ASSIGNED">Assigned</option>
              <option value="ON_THE_WAY">On The Way</option>
              <option value="ARRIVED">Arrived</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>

          {/* Service Filter */}
          <div>
            <select
              value={serviceFilter || ''}
              onChange={(e) => {
                setServiceFilter(e.target.value ? Number(e.target.value) : undefined);
                setPage(1);
              }}
              className="w-full bg-surface-light/80 border border-surface-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500"
            >
              <option value="">All Services</option>
              {services.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          {/* Sort Selector & Reset */}
          <div className="flex gap-2">
            <select
              value={ordering}
              onChange={(e) => setOrdering(e.target.value)}
              className="flex-1 bg-surface-light/80 border border-surface-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500"
            >
              <option value="-created_at">Newest First</option>
              <option value="created_at">Oldest First</option>
              <option value="-amount">Amount: High to Low</option>
              <option value="amount">Amount: Low to High</option>
            </select>

            <button
              type="button"
              onClick={handleResetFilters}
              title="Reset Filters"
              className="px-2.5 py-2 bg-surface-light hover:bg-surface-lighter text-slate-400 hover:text-white rounded-lg border border-surface-border transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>

      {/* Bookings Table View */}
      {error ? (
        <ErrorState message={error} onRetry={fetchBookings} />
      ) : loading ? (
        <TableSkeleton rows={8} cols={7} />
      ) : bookings.length === 0 ? (
        <EmptyState
          title="No bookings match your filters"
          description="Try broadening your search term or clearing the active status/service filters."
          action={
            <button
              onClick={handleResetFilters}
              className="px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-lg text-xs font-semibold"
            >
              Reset All Filters
            </button>
          }
        />
      ) : (
        <div className="bg-surface rounded-xl border border-surface-border overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-surface-light/50 border-b border-surface-border text-slate-400 font-semibold uppercase tracking-wider">
                  <th className="py-3.5 px-4">Booking #</th>
                  <th className="py-3.5 px-4">Customer</th>
                  <th className="py-3.5 px-4">Vehicle</th>
                  <th className="py-3.5 px-4">Service</th>
                  <th className="py-3.5 px-4">Mechanic</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Amount</th>
                  <th className="py-3.5 px-4">Created</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {bookings.map((booking) => (
                  <tr
                    key={booking.id}
                    onClick={() => onSelectBooking(booking.id)}
                    className="hover:bg-surface-light/40 transition-colors cursor-pointer group"
                  >
                    <td className="py-3 px-4 font-mono font-bold text-orange-400 whitespace-nowrap">
                      {booking.booking_number}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-200">{booking.customer_name}</div>
                      <div className="text-slate-400 font-mono text-[11px]">{booking.customer_phone}</div>
                    </td>
                    <td className="py-3 px-4 text-slate-300 whitespace-nowrap">{booking.vehicle_info}</td>
                    <td className="py-3 px-4 font-medium text-slate-200 whitespace-nowrap">{booking.service_name}</td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      {booking.mechanic_name ? (
                        <span className="font-medium text-slate-200 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          {booking.mechanic_name}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-red-400 bg-red-950/40 px-2 py-0.5 rounded border border-red-800/60 font-semibold text-[11px]">
                          <UserCheck className="w-3 h-3" />
                          Unassigned
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <StatusBadge status={booking.status} size="sm" />
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-100 whitespace-nowrap">
                      ₹{Number(booking.amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap font-mono text-[11px]">
                      {new Date(booking.created_at).toLocaleDateString()}{' '}
                      {new Date(booking.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectBooking(booking.id);
                        }}
                        className="p-1.5 bg-surface-light hover:bg-orange-600 text-slate-300 hover:text-white rounded-lg transition-colors inline-flex items-center justify-center"
                        title="View details & status timeline"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Server-side Pagination Footer */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 border-t border-surface-border bg-surface-light/20 text-xs text-slate-400">
            <div>
              Showing <span className="font-semibold text-white">{(page - 1) * pageSize + 1}</span> to{' '}
              <span className="font-semibold text-white">{Math.min(page * pageSize, totalCount)}</span> of{' '}
              <span className="font-semibold text-white">{totalCount}</span> bookings
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
        </div>
      )}

      {/* New Booking Creation Modal */}
      <CreateBookingModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onBookingCreated={(newBooking) => {
          fetchBookings();
          onSelectBooking(newBooking.id);
        }}
      />
    </div>
  );
};
