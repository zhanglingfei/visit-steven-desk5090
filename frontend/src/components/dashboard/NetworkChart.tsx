import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { Wifi, ArrowDown, ArrowUp } from 'lucide-react';
import { SystemMetrics } from '../../types/metrics';

interface Props {
  current: SystemMetrics | null;
  history: SystemMetrics[];
}

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 ** 3);
  const mb = bytes / (1024 ** 2);
  const kb = bytes / 1024;
  if (gb >= 1) return `${gb.toFixed(2)} GB/s`;
  if (mb >= 1) return `${mb.toFixed(2)} MB/s`;
  if (kb >= 1) return `${kb.toFixed(2)} KB/s`;
  return `${bytes.toFixed(0)} B/s`;
}

export default function NetworkChart({ current, history }: Props) {
  const chartData = history.map((m, i) => ({
    i,
    sent: m.network.total_sent_rate,
    recv: m.network.total_recv_rate,
  }));

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Wifi className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-medium text-gray-300">Network</h3>
        </div>
        {current && (
          <div className="flex gap-3 text-xs">
            <span className="flex items-center gap-1 text-cyan-400">
              <ArrowDown className="w-3 h-3" />
              {formatBytes(current.network.total_recv_rate)}
            </span>
            <span className="flex items-center gap-1 text-pink-400">
              <ArrowUp className="w-3 h-3" />
              {formatBytes(current.network.total_sent_rate)}
            </span>
          </div>
        )}
      </div>

      <div className="h-28 mb-3">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis hide />
            <YAxis hide />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
              labelStyle={{ display: 'none' }}
              formatter={(value) => formatBytes(Number(value))}
            />
            <Area
              type="monotone"
              dataKey="recv"
              stroke="#06b6d4"
              fill="#06b6d420"
              strokeWidth={2}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="sent"
              stroke="#ec4899"
              fill="#ec489920"
              strokeWidth={2}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {current && (
        <div className="text-xs text-gray-500 text-right">
          {current.network.connection_count} active connections
        </div>
      )}
    </div>
  );
}
