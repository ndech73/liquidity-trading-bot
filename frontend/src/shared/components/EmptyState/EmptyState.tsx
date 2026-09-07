import React from 'react';
import { BarChart3 } from 'lucide-react';

export interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Data Available',
  description = 'No active records found for the selected criteria.',
  icon,
  action,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 border border-dashed border-slate-800 rounded-xl text-center ${className}`}>
      <div className="text-slate-500 mb-2 flex items-center justify-center">
        {icon || <BarChart3 className="w-8 h-8 text-slate-500" />}
      </div>
      <h4 className="text-sm font-semibold text-slate-300 mb-1">{title}</h4>
      <p className="text-xs text-slate-400 max-w-sm mb-4">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
