import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
}) => {
  return (
    <div className="bg-surface/50 border border-surface-border rounded-xl p-8 text-center max-w-md mx-auto my-6">
      <div className="w-12 h-12 rounded-full bg-surface-light flex items-center justify-center mx-auto mb-4 text-slate-400">
        {icon || <Inbox className="w-6 h-6" />}
      </div>
      <h4 className="text-base font-semibold text-slate-200 mb-1">{title}</h4>
      <p className="text-sm text-slate-400 mb-4">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
