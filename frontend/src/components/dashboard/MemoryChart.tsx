import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { SystemMetrics } from '../../types/metrics';
import MetricGauge from './MetricGauge';

interface Props {
  current: SystemMetrics | null;
  history: SystemMetrics[];
}

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 ** 3);
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / (1024 ** 2)).toFixed(0)} MB`;
}

export default function MemoryChart({ current, history }: Props) {
  const chartData = history.map((m, i) => ({
    i,
    ram: m.memory.ram_percent,
    swap: m.memory.swap_percent,
  }));

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-300">Memory</h3>
        {current && (
          <span className="text-xs text-gray-500">
            {formatBytes(current.memory.ram_used)} / {formatBytes(current.memory.ram_total)}
          </span>
        )}
      </div>

      <div className="flex items-center gap-6">
        <div className="flex gap-3">
          <div className="relative">
            <MetricGauge
              value={current?.memory.ram_percent ?? 0}
              label="RAM"
              size={80}
              color="#8b5cf6"
            />
          </div>
          <div className="relative">
            <MetricGauge
              value={current?.memory.swap_percent ?? 0}
              label="Swap"
              size={80}
              color="#6366f1"
            />
          </div>
        </div>
        <div className="flex-1 h-28">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis hide />
              <YAxis domain={[0, 100]} hide />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ display: 'none' }}
              />
              <Area
                type="monotone"
                dataKey="ram"
                stroke="#8b5cf6"
                fill="#8b5cf620"
                strokeWidth={2}
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="swap"
                stroke="#6366f1"
                fill="#6366f120"
                strokeWidth={1}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
