import React from 'react';
import { BookingStatus, AlertSeverity, OperationalStatus, WorkloadBadge, AvailabilityStatus } from '../../types';

interface StatusBadgeProps {
  status: BookingStatus;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const styles: Record<BookingStatus, string> = {
    PENDING: 'bg-amber-950/70 text-amber-300 border-amber-800/80',
    ASSIGNED: 'bg-blue-950/70 text-blue-300 border-blue-800/80',
    ON_THE_WAY: 'bg-indigo-950/70 text-indigo-300 border-indigo-800/80',
    ARRIVED: 'bg-purple-950/70 text-purple-300 border-purple-800/80',
    IN_PROGRESS: 'bg-orange-950/70 text-orange-300 border-orange-800/80 animate-pulse-subtle',
    COMPLETED: 'bg-emerald-950/70 text-emerald-300 border-emerald-800/80',
    CANCELLED: 'bg-rose-950/70 text-rose-300 border-rose-800/80',
  };

  const labels: Record<BookingStatus, string> = {
    PENDING: 'Pending',
    ASSIGNED: 'Assigned',
    ON_THE_WAY: 'On The Way',
    ARRIVED: 'Arrived',
    IN_PROGRESS: 'In Progress',
    COMPLETED: 'Completed',
    CANCELLED: 'Cancelled',
  };

  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span
      className={`inline-flex items-center rounded-md border font-mono uppercase tracking-wider ${sizeClass} ${
        styles[status] || 'bg-gray-800 text-gray-300 border-gray-700'
      }`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-80" />
      {labels[status] || status}
    </span>
  );
};

export const SeverityBadge: React.FC<{ severity: AlertSeverity }> = ({ severity }) => {
  const styles: Record<AlertSeverity, string> = {
    CRITICAL: 'bg-red-950 text-red-300 border-red-700/80',
    HIGH: 'bg-amber-950 text-amber-300 border-amber-700/80',
    WARNING: 'bg-yellow-950 text-yellow-300 border-yellow-700/80',
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider border ${
        styles[severity]
      }`}
    >
      {severity}
    </span>
  );
};

export const OperationalStatusBadge: React.FC<{ status: OperationalStatus }> = ({ status }) => {
  const styles: Record<OperationalStatus, string> = {
    AVAILABLE: 'bg-emerald-950/60 text-emerald-300 border-emerald-800',
    ASSIGNED: 'bg-blue-950/60 text-blue-300 border-blue-800',
    ON_JOB: 'bg-orange-950/60 text-orange-300 border-orange-800',
    BREAK: 'bg-yellow-950/60 text-yellow-300 border-yellow-800',
    OFFLINE: 'bg-zinc-800 text-zinc-400 border-zinc-700',
  };

  const labels: Record<OperationalStatus, string> = {
    AVAILABLE: 'Available',
    ASSIGNED: 'Assigned',
    ON_JOB: 'On Job',
    BREAK: 'On Break',
    OFFLINE: 'Offline',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
        styles[status] || 'bg-gray-800 text-gray-300 border-gray-700'
      }`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current" />
      {labels[status] || status}
    </span>
  );
};

export const WorkloadBadgeComponent: React.FC<{ badge: WorkloadBadge; count: number }> = ({ badge, count }) => {
  const styles: Record<WorkloadBadge, string> = {
    IDLE: 'bg-slate-800 text-slate-300 border-slate-700',
    ACTIVE: 'bg-blue-950 text-blue-300 border-blue-800',
    BUSY: 'bg-amber-950 text-amber-300 border-amber-800',
    OVERLOADED: 'bg-red-950 text-red-300 border-red-800 font-bold',
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs border ${
        styles[badge] || 'bg-gray-800 text-gray-300'
      }`}
    >
      {badge} ({count})
    </span>
  );
};
