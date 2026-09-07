import React from 'react';
import { Card } from '../../../shared/components/Card';

export const LiquidityEvents: React.FC = () => {
  return (
    <Card title="Related Liquidity Sweeps">
      <p className="text-xs text-slate-400">
        Trade triggered within 90 seconds of the London open liquidity sweep.
      </p>
    </Card>
  );
};
