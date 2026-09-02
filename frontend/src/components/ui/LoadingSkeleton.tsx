import React from 'react';

export const KPICardSkeleton: React.FC = () => (
  <div className="bg-surface rounded-xl p-5 border border-surface-border animate-pulse">
    <div className="flex justify-between items-center mb-3">
      <div className="h-4 bg-surface-light rounded w-24"></div>
      <div className="h-4 bg-surface-light rounded w-8"></div>
    </div>
    <div className="h-8 bg-surface-light rounded w-32 mb-2"></div>
    <div className="h-3 bg-surface-light rounded w-20"></div>
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number; cols?: number }> = ({ rows = 5, cols = 6 }) => (
  <div className="bg-surface rounded-xl border border-surface-border overflow-hidden animate-pulse">
    <div className="p-4 border-b border-surface-border bg-surface-light/30 flex gap-4">
      {Array.from({ length: cols }).map((_, i) => (
        <div key={i} className="h-4 bg-surface-light rounded flex-1"></div>
      ))}
    </div>
    <div className="divide-y divide-surface-border">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="p-4 flex gap-4">
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="h-4 bg-surface-light/60 rounded flex-1"></div>
          ))}
        </div>
      ))}
    </div>
  </div>
);

export const ChartSkeleton: React.FC = () => (
  <div className="bg-surface rounded-xl p-5 border border-surface-border h-80 animate-pulse flex flex-col justify-between">
    <div className="h-5 bg-surface-light rounded w-36"></div>
    <div className="h-48 bg-surface-light/40 rounded w-full"></div>
    <div className="h-4 bg-surface-light/60 rounded w-full"></div>
  </div>
);
