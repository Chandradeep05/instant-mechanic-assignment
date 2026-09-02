import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  delta?: number;
  deltaLabel?: string;
  subtitle?: string;
  icon: React.ReactNode;
  iconBg?: string;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  delta,
  deltaLabel = 'vs yesterday',
  subtitle,
  icon,
  iconBg = 'bg-orange-500/10 text-orange-400 border-orange-500/20',
}) => {
  return (
    <div className="bg-surface rounded-xl p-5 border border-surface-border hover:border-slate-700 transition-all shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${iconBg}`}>
          {icon}
        </div>
      </div>
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">{value}</div>
        {delta !== undefined && (
          <div
            className={`inline-flex items-center text-xs font-semibold px-1.5 py-0.5 rounded ${
              delta >= 0
                ? 'text-emerald-400 bg-emerald-950/60 border border-emerald-800/60'
                : 'text-rose-400 bg-rose-950/60 border border-rose-800/60'
            }`}
          >
            {delta >= 0 ? <ArrowUpRight className="w-3 h-3 mr-0.5" /> : <ArrowDownRight className="w-3 h-3 mr-0.5" />}
            {delta >= 0 ? `+${delta}%` : `${delta}%`}
          </div>
        )}
      </div>
      {(deltaLabel || subtitle) && (
        <div className="text-xs text-slate-500 mt-2 truncate">
          {subtitle || `${delta !== undefined ? (delta >= 0 ? 'Increased' : 'Decreased') : ''} ${deltaLabel}`}
        </div>
      )}
    </div>
  );
};
