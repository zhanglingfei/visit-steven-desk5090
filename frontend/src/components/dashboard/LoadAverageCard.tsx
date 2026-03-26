import { Activity } from 'lucide-react';
import { SystemMetrics } from '../../types/metrics';

interface Props {
  current: SystemMetrics | null;
}

export default function LoadAverageCard({ current }: Props) {
  const load = current?.cpu.load_avg;

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-4 h-4 text-purple-400" />
        <h3 className="text-sm font-medium text-gray-300">Load Average</h3>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-100">{load ? load[0].toFixed(2) : '-'}</p>
          <p className="text-xs text-gray-500">1 min</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-100">{load ? load[1].toFixed(2) : '-'}</p>
          <p className="text-xs text-gray-500">5 min</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-100">{load ? load[2].toFixed(2) : '-'}</p>
          <p className="text-xs text-gray-500">15 min</p>
        </div>
      </div>
    </div>
  );
}
