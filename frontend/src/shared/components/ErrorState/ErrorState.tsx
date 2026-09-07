import React from 'react';
import { AlertTriangle } from 'lucide-react';

export interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  message = 'Failed to load data. Please check connection.',
  onRetry,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 bg-rose-950/20 border border-rose-900/40 rounded-xl text-center ${className}`}>
      <div className="w-10 h-10 text-rose-400 mb-2 flex items-center justify-center rounded-full bg-rose-900/30">
        <AlertTriangle className="w-5 h-5 text-rose-400" />
      </div>
      <p className="text-sm text-rose-300 font-medium mb-3">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1.5 text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white rounded-md transition"
        >
          Retry Connection
        </button>
      )}
    </div>
  );
};
