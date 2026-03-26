import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { HardDrive } from 'lucide-react';
import { SystemMetrics } from '../../types/metrics';

interface Props {
  current: SystemMetrics | null;
  history: SystemMetrics[];
}

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 ** 3);
  const mb = bytes / (1024 ** 2);
  if (gb >= 1) return `${gb.toFixed(1)} GB/s`;
  if (mb >= 1) return `${mb.toFixed(1)} MB/s`;
  return `${bytes.toFixed(0)} B/s`;
}

function formatStorage(bytes: number): string {
  const gb = bytes / (1024 ** 3);
  const tb = gb / 1024;
  if (tb >= 1) return `${tb.toFixed(1)} TB`;
  return `${gb.toFixed(0)} GB`;
}

export default function DiskChart({ current, history }: Props) {
  const chartData = history.map((m, i) => ({
    i,
    read: m.disk.read_rate,
    write: m.disk.write_rate,
  }));

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <HardDrive className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-medium text-gray-300">Disk I/O</h3>
        </div>
        {current && (
          <div className="flex gap-3 text-xs">
            <span className="text-emerald-400">
              R: {formatBytes(current.disk.read_rate)}
            </span>
            <span className="text-amber-400">
              W: {formatBytes(current.disk.write_rate)}
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
              dataKey="read"
              stroke="#10b981"
              fill="#10b98120"
              strokeWidth={2}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="write"
              stroke="#f59e0b"
              fill="#f59e0b20"
              strokeWidth={2}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {current && (
        <div className="space-y-1 max-h-24 overflow-y-auto">
          {current.disk.partitions.map((p, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <div className="w-24 truncate text-gray-400">{p.device}</div>
              <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${p.percent}%` }}
                />
              </div>
              <div className="w-16 text-right text-gray-500">
                {formatStorage(p.used)} / {formatStorage(p.total)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
