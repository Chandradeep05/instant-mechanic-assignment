import React, { useState } from 'react';
import { AlertCircle, AlertTriangle, Clock, UserCheck, CheckCircle2, ChevronRight, ShieldAlert } from 'lucide-react';
import { AttentionItem, AlertSeverity } from '../../types';
import { SeverityBadge } from '../ui/Badge';

interface AttentionPanelProps {
  attentionItems: AttentionItem[];
  isLoading: boolean;
  onActionClick: (item: AttentionItem) => void;
}

export const AttentionPanel: React.FC<AttentionPanelProps> = ({
  attentionItems,
  isLoading,
  onActionClick,
}) => {
  const [filter, setFilter] = useState<'ALL' | AlertSeverity>('ALL');

  const filteredItems = filter === 'ALL'
    ? attentionItems
    : attentionItems.filter((i) => i.severity === filter);

  const criticalCount = attentionItems.filter((i) => i.severity === 'CRITICAL').length;
  const highCount = attentionItems.filter((i) => i.severity === 'HIGH').length;
  const warningCount = attentionItems.filter((i) => i.severity === 'WARNING').length;

  return (
    <div className="bg-surface rounded-xl border border-surface-border p-6 shadow-md">
      {/* Panel Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 mb-4 border-b border-surface-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30 flex items-center justify-center">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-tight">Requires Attention</h2>
              <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-red-950 text-red-400 border border-red-800">
                {attentionItems.length} Active
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Deterministic ops rules monitoring dispatch delays, unassigned queues, and overload thresholds.
            </p>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 bg-surface-light/70 p-1 rounded-lg border border-surface-border text-xs">
          <button
            onClick={() => setFilter('ALL')}
            className={`px-2.5 py-1 rounded font-medium transition-all ${
              filter === 'ALL' ? 'bg-slate-700 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({attentionItems.length})
          </button>
          <button
            onClick={() => setFilter('CRITICAL')}
            className={`px-2.5 py-1 rounded font-medium transition-all ${
              filter === 'CRITICAL' ? 'bg-red-700 text-white shadow' : 'text-red-400 hover:text-red-300'
            }`}
          >
            Critical ({criticalCount})
          </button>
          <button
            onClick={() => setFilter('HIGH')}
            className={`px-2.5 py-1 rounded font-medium transition-all ${
              filter === 'HIGH' ? 'bg-amber-700 text-white shadow' : 'text-amber-400 hover:text-amber-300'
            }`}
          >
            High ({highCount})
          </button>
          <button
            onClick={() => setFilter('WARNING')}
            className={`px-2.5 py-1 rounded font-medium transition-all ${
              filter === 'WARNING' ? 'bg-yellow-700 text-white shadow' : 'text-yellow-400 hover:text-yellow-300'
            }`}
          >
            Warning ({warningCount})
          </button>
        </div>
      </div>

      {/* Alerts Content */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-surface-light/40 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <div className="w-12 h-12 rounded-full bg-emerald-950/60 border border-emerald-800 text-emerald-400 flex items-center justify-center mb-3">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h4 className="text-sm font-semibold text-slate-200">No Operations In Jeopardy</h4>
          <p className="text-xs text-slate-400 mt-1 max-w-sm">
            All active bookings and mechanics are within healthy response and workload thresholds.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {filteredItems.map((item) => {
            const isCrit = item.severity === 'CRITICAL';
            const isHigh = item.severity === 'HIGH';

            return (
              <div
                key={item.id}
                className={`flex flex-col justify-between p-4 rounded-xl border transition-all ${
                  isCrit
                    ? 'bg-red-950/25 border-red-800/60 hover:border-red-600'
                    : isHigh
                    ? 'bg-amber-950/25 border-amber-800/60 hover:border-amber-600'
                    : 'bg-yellow-950/25 border-yellow-800/60 hover:border-yellow-600'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={item.severity} />
                      {item.booking_number && (
                        <span className="font-mono text-xs font-semibold text-slate-300">
                          {item.booking_number}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  <h4 className="text-sm font-bold text-white tracking-tight mb-1">{item.title}</h4>
                  <p className="text-xs text-slate-300/80 mb-4">{item.details}</p>
                </div>

                <div className="flex items-center justify-end pt-2 border-t border-surface-border/50">
                  <button
                    onClick={() => onActionClick(item)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      isCrit
                        ? 'bg-red-600 hover:bg-red-500 text-white shadow-sm shadow-red-500/20'
                        : isHigh
                        ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-sm shadow-amber-500/20'
                        : 'bg-yellow-600 hover:bg-yellow-500 text-white shadow-sm shadow-yellow-500/20'
                    }`}
                  >
                    {item.action_type === 'ASSIGN_MECHANIC' ? (
                      <>
                        <UserCheck className="w-3.5 h-3.5" />
                        Assign Mechanic
                      </>
                    ) : (
                      <>
                        <span>View Details</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
