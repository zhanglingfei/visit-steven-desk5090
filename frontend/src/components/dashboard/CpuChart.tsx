import {
  LineChart,
  Line,
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

export default function CpuChart({ current, history }: Props) {
  const chartData = history.map((m, i) => ({
    i,
    overall: m.cpu.percent_overall,
  }));

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-300">CPU Usage</h3>
        {current && (
          <span className="text-xs text-gray-500">
            {current.cpu.freq_current ? `${current.cpu.freq_current} MHz` : ''}
            {' · '}{current.cpu.core_count}C/{current.cpu.thread_count}T
          </span>
        )}
      </div>

      <div className="flex items-center gap-6">
        <div className="relative">
          <MetricGauge
            value={current?.cpu.percent_overall ?? 0}
            label="Overall"
            size={100}
          />
        </div>
        <div className="flex-1 h-32">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis hide />
              <YAxis domain={[0, 100]} hide />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ display: 'none' }}
              />
              <Line
                type="monotone"
                dataKey="overall"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {current && (
        <div className="mt-3 grid grid-cols-8 gap-1">
          {current.cpu.percent_per_core.map((pct, i) => (
            <div key={i} className="text-center">
              <div
                className="h-2 rounded-full mx-auto transition-all duration-300"
                style={{
                  width: '100%',
                  background: `linear-gradient(90deg, ${pct > 90 ? '#ef4444' : pct > 70 ? '#f59e0b' : '#3b82f6'} ${pct}%, #1f2937 ${pct}%)`,
                }}
              />
              <span className="text-[9px] text-gray-600">{i}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
