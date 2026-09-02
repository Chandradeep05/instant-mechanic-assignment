import {
  Calendar,
  IndianRupee,
  Users,
  Wrench,
  CheckCircle,
  Clock,
  XCircle,
  TrendingUp,
  UserPlus,
  Timer,
  Zap,
} from 'lucide-react';
import { OverviewKPIs, AttentionItem } from '../../types';
import { KPICard } from './KPICard';
import { AttentionPanel } from '../attention/AttentionPanel';
import { KPICardSkeleton } from '../ui/LoadingSkeleton';

interface OverviewTabProps {
  kpis: OverviewKPIs | null;
  attentionItems: AttentionItem[];
  isLoading: boolean;
  onAttentionAction: (item: AttentionItem) => void;
  onViewBookings: (statusFilter?: string) => void;
  onViewMechanics: () => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  kpis,
  attentionItems,
  isLoading,
  onAttentionAction,
  onViewBookings,
  onViewMechanics,
}) => {
  // Format currency in INR (Indian Rupees)
  const formatINR = (value: number) =>
    `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      {/* 1. Requires Attention Operations Cockpit Panel (Promoted to Tier 1) */}
      <AttentionPanel
        attentionItems={attentionItems}
        isLoading={isLoading}
        onActionClick={onAttentionAction}
      />

      {/* 2. Primary KPI Metric Cards Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">LiveOps Performance Metrics</h3>
          <span className="text-xs text-slate-500 font-mono">Deltas calculated server-side vs yesterday</span>
        </div>

        {isLoading || !kpis ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <KPICardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Today's Bookings */}
            <div onClick={() => onViewBookings()} className="cursor-pointer">
              <KPICard
                title="Today's Bookings"
                value={kpis.today_bookings}
                delta={kpis.today_bookings_delta_pct}
                icon={<Calendar className="w-4 h-4" />}
                iconBg="bg-blue-500/10 text-blue-400 border-blue-500/20"
              />
            </div>

            {/* Total Revenue */}
            <KPICard
              title="Total Revenue (Completed)"
              value={formatINR(kpis.total_revenue)}
              subtitle="Sum of completed jobs"
              icon={<IndianRupee className="w-4 h-4" />}
              iconBg="bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
            />

            {/* Today's Revenue */}
            <KPICard
              title="Today's Revenue"
              value={formatINR(kpis.today_revenue)}
              delta={kpis.today_revenue_delta_pct}
              icon={<TrendingUp className="w-4 h-4" />}
              iconBg="bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
            />

            {/* Active Mechanics */}
            <div onClick={() => onViewMechanics()} className="cursor-pointer">
              <KPICard
                title="Active Mechanics"
                value={`${kpis.active_mechanics}`}
                subtitle={`${kpis.available_mechanics} available • ${kpis.busy_mechanics} on jobs`}
                icon={<Wrench className="w-4 h-4" />}
                iconBg="bg-orange-500/10 text-orange-400 border-orange-500/20"
              />
            </div>

            {/* Total Bookings */}
            <KPICard
              title="Total Lifetime Bookings"
              value={kpis.total_bookings}
              subtitle="All historical & active"
              icon={<Calendar className="w-4 h-4" />}
              iconBg="bg-purple-500/10 text-purple-400 border-purple-500/20"
            />

            {/* Completed */}
            <div onClick={() => onViewBookings('COMPLETED')} className="cursor-pointer">
              <KPICard
                title="Completed Jobs"
                value={kpis.completed_bookings}
                subtitle={`${kpis.total_bookings ? Math.round((kpis.completed_bookings / kpis.total_bookings) * 100) : 0}% completion rate`}
                icon={<CheckCircle className="w-4 h-4" />}
                iconBg="bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              />
            </div>

            {/* Pending */}
            <div onClick={() => onViewBookings('PENDING')} className="cursor-pointer">
              <KPICard
                title="Pending Dispatch"
                value={kpis.pending_bookings}
                subtitle="Awaiting mechanic pickup"
                icon={<Clock className="w-4 h-4" />}
                iconBg="bg-amber-500/10 text-amber-400 border-amber-500/20"
              />
            </div>

            {/* Cancelled */}
            <div onClick={() => onViewBookings('CANCELLED')} className="cursor-pointer">
              <KPICard
                title="Cancelled Bookings"
                value={kpis.cancelled_bookings}
                subtitle={`${kpis.total_bookings ? Math.round((kpis.cancelled_bookings / kpis.total_bookings) * 100) : 0}% cancellation rate`}
                icon={<XCircle className="w-4 h-4" />}
                iconBg="bg-rose-500/10 text-rose-400 border-rose-500/20"
              />
            </div>
          </div>
        )}
      </div>

      {/* 3. Secondary Row: Availability & Efficiency Stats */}
      {kpis && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
          <div className="bg-surface/70 rounded-xl p-4 border border-surface-border flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
              <CheckCircle className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-slate-400 font-medium">Available Mechanics</div>
              <div className="text-xl font-bold text-white">{kpis.available_mechanics} ready</div>
            </div>
          </div>

          <div className="bg-surface/70 rounded-xl p-4 border border-surface-border flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-slate-400 font-medium">Busy / Dispatched</div>
              <div className="text-xl font-bold text-white">{kpis.busy_mechanics} active</div>
            </div>
          </div>

          <div className="bg-surface/70 rounded-xl p-4 border border-surface-border flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center">
              <UserPlus className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-slate-400 font-medium">New Customers (Today)</div>
              <div className="text-xl font-bold text-white">
                {kpis.new_customers}{' '}
                <span className="text-xs text-slate-400 font-normal">
                  ({kpis.new_customers_delta >= 0 ? `+${kpis.new_customers_delta}` : kpis.new_customers_delta} vs yest)
                </span>
              </div>
            </div>
          </div>

          <div className="bg-surface/70 rounded-xl p-4 border border-surface-border flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-orange-500/10 text-orange-400 border border-orange-500/20 flex items-center justify-center">
              <Timer className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-slate-400 font-medium">Avg Assignment Time</div>
              <div className="text-xl font-bold text-white">
                {kpis.avg_response_time_minutes != null
                  ? `${kpis.avg_response_time_minutes} min`
                  : <span className="text-slate-500 text-sm">— No data yet</span>
                }
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
