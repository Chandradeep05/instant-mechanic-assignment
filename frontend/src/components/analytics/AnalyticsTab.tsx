import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import { BarChart3, TrendingUp, PieChart as PieIcon, Layers } from 'lucide-react';
import { api } from '../../api/client';
import {
  BookingsTimelineDataPoint,
  RevenueTimelineDataPoint,
  StatusDistributionDataPoint,
  ServiceBreakdownDataPoint,
} from '../../types';
import { ChartSkeleton } from '../ui/LoadingSkeleton';
import { ErrorState } from '../ui/ErrorState';

const STATUS_COLORS: Record<string, string> = {
  COMPLETED: '#10B981',
  IN_PROGRESS: '#F97316',
  ARRIVED: '#A855F7',
  ON_THE_WAY: '#6366F1',
  ASSIGNED: '#3B82F6',
  PENDING: '#F59E0B',
  CANCELLED: '#EF4444',
};

export const AnalyticsTab: React.FC = () => {
  const [bookingRange, setBookingRange] = useState<'24h' | '7d' | '30d'>('7d');
  const [revenueRange, setRevenueRange] = useState<'7d' | '30d'>('7d');

  const [bookingsData, setBookingsData] = useState<BookingsTimelineDataPoint[]>([]);
  const [revenueData, setRevenueData] = useState<RevenueTimelineDataPoint[]>([]);
  const [statusData, setStatusData] = useState<StatusDistributionDataPoint[]>([]);
  const [servicesData, setServicesData] = useState<ServiceBreakdownDataPoint[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      const [bRes, rRes, sRes, srvRes] = await Promise.all([
        api.getAnalyticsBookings(bookingRange),
        api.getAnalyticsRevenue(revenueRange),
        api.getAnalyticsStatus(),
        api.getAnalyticsServices(),
      ]);

      setBookingsData(bRes.data);
      setRevenueData(rRes.data);
      setStatusData(sRes.distribution);
      setServicesData(srvRes.services);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch analytics data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [bookingRange, revenueRange]);

  if (error) {
    return <ErrorState message={error} onRetry={fetchAnalytics} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Operations Analytics & Trends</h2>
          <p className="text-xs text-slate-400">
            Real-time ORM aggregated insights into dispatch volume, completed revenue, and service patterns.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Bookings Timeline Chart */}
        <div className="bg-surface rounded-xl border border-surface-border p-5 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center">
                <BarChart3 className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Bookings Over Time</h3>
                <span className="text-xs text-slate-400">Total requests created vs completed</span>
              </div>
            </div>

            <div className="flex items-center bg-surface-light p-1 rounded-lg border border-surface-border text-xs">
              {(['24h', '7d', '30d'] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => setBookingRange(r)}
                  className={`px-2.5 py-1 rounded font-medium transition-all ${
                    bookingRange === r ? 'bg-orange-500 text-white shadow font-semibold' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {r.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <ChartSkeleton />
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={bookingsData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorBookings" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                  <XAxis dataKey="timestamp" stroke="#64748B" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748B" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.5rem' }}
                    labelStyle={{ color: '#F3F4F6', fontWeight: 'bold' }}
                  />
                  <Legend verticalAlign="top" height={36} />
                  <Area type="monotone" dataKey="bookings" stroke="#3B82F6" strokeWidth={2} fillOpacity={1} fill="url(#colorBookings)" name="Created" />
                  <Area type="monotone" dataKey="completed" stroke="#10B981" strokeWidth={2} fillOpacity={1} fill="url(#colorCompleted)" name="Completed" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* 2. Revenue Timeline Chart */}
        <div className="bg-surface rounded-xl border border-surface-border p-5 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
                <TrendingUp className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Completed Revenue</h3>
                <span className="text-xs text-slate-400">Daily gross booking value</span>
              </div>
            </div>

            <div className="flex items-center bg-surface-light p-1 rounded-lg border border-surface-border text-xs">
              {(['7d', '30d'] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => setRevenueRange(r)}
                  className={`px-2.5 py-1 rounded font-medium transition-all ${
                    revenueRange === r ? 'bg-orange-500 text-white shadow font-semibold' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {r.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <ChartSkeleton />
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={revenueData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                  <XAxis dataKey="timestamp" stroke="#64748B" fontSize={11} tickLine={false} />
                  <YAxis
                    stroke="#64748B"
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={(v) => `₹${v.toLocaleString('en-IN')}`}
                  />
                  <Tooltip
                    formatter={(value: any) => [`₹${Number(value).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`, 'Revenue']}
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.5rem' }}
                    labelStyle={{ color: '#F3F4F6', fontWeight: 'bold' }}
                  />
                  <Bar dataKey="revenue" fill="#10B981" radius={[4, 4, 0, 0]} name="Revenue (₹)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* 3. Status Distribution (Donut Chart) */}
        <div className="bg-surface rounded-xl border border-surface-border p-5 shadow-sm flex flex-col justify-between">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center justify-center">
              <PieIcon className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Status Breakdown</h3>
              <span className="text-xs text-slate-400">Distribution across active and terminal states</span>
            </div>
          </div>

          {loading ? (
            <ChartSkeleton />
          ) : (
            <div className="flex flex-col sm:flex-row items-center gap-4 h-72">
              <div className="w-full sm:w-1/2 h-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusData}
                      dataKey="count"
                      nameKey="status"
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={3}
                    >
                      {statusData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={STATUS_COLORS[entry.status] || '#64748B'} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(val: any, name: any, item: any) => [`${val} (${item.payload.percentage}%)`, name]}
                      contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.5rem' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="w-full sm:w-1/2 grid grid-cols-2 gap-2 text-xs">
                {statusData.map((item) => (
                  <div key={item.status} className="flex items-center gap-2 p-1.5 rounded bg-surface-light/40">
                    <span
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: STATUS_COLORS[item.status] || '#64748B' }}
                    />
                    <div className="truncate">
                      <div className="font-semibold text-slate-200 truncate">{item.status}</div>
                      <div className="text-slate-400 font-mono">{item.count} ({item.percentage}%)</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 4. Service Breakdown Chart */}
        <div className="bg-surface rounded-xl border border-surface-border p-5 shadow-sm flex flex-col justify-between">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-orange-500/10 text-orange-400 border border-orange-500/20 flex items-center justify-center">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Services & Category Breakdown</h3>
              <span className="text-xs text-slate-400">Total job volume and generated revenue per category</span>
            </div>
          </div>

          {loading ? (
            <ChartSkeleton />
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={servicesData}
                  layout="vertical"
                  margin={{ top: 5, right: 20, left: 40, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                  <XAxis type="number" stroke="#64748B" fontSize={11} tickLine={false} />
                  <YAxis
                    dataKey="name"
                    type="category"
                    stroke="#64748B"
                    fontSize={10}
                    tickLine={false}
                    width={110}
                    tickFormatter={(val) => (val.length > 16 ? `${val.substring(0, 14)}...` : val)}
                  />
                  <Tooltip
                    formatter={(value: any, name: any) => [
                      name === 'total_revenue' ? `₹${Number(value).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : value,
                      name === 'total_revenue' ? 'Revenue' : 'Jobs Booked',
                    ]}
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.5rem' }}
                  />
                  <Bar dataKey="total_bookings" fill="#F97316" radius={[0, 4, 4, 0]} name="Jobs Booked" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
