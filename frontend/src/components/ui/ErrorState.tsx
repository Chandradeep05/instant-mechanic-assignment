import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Failed to load operational data',
  message = 'An unexpected error occurred while communicating with the LiveOps API.',
  onRetry,
}) => {
  return (
    <div className="bg-red-950/40 border border-red-800/80 rounded-xl p-6 text-center max-w-lg mx-auto my-8">
      <div className="w-12 h-12 rounded-full bg-red-900/50 flex items-center justify-center mx-auto mb-4 text-red-400">
        <AlertTriangle className="w-6 h-6" />
      </div>
      <h3 className="text-lg font-semibold text-red-200 mb-2">{title}</h3>
      <p className="text-sm text-red-300/80 mb-5">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg transition-colors shadow-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Retry Request
        </button>
      )}
    </div>
  );
};
