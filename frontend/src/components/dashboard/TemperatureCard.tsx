import { Thermometer } from 'lucide-react';
import { SystemMetrics } from '../../types/metrics';

interface Props {
  current: SystemMetrics | null;
}

export default function TemperatureCard({ current }: Props) {
  const temps = current?.temperatures ?? [];

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <Thermometer className="w-4 h-4 text-orange-400" />
        <h3 className="text-sm font-medium text-gray-300">Temperatures</h3>
      </div>

      {temps.length === 0 ? (
        <div className="text-xs text-gray-600 text-center py-4">No sensors available</div>
      ) : (
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {temps.map((t, i) => {
            const pct = t.critical ? (t.current / t.critical) * 100 : (t.current / 110) * 100;
            const color = t.current > (t.critical ?? 100) ? '#ef4444' : t.current > (t.high ?? 80) ? '#f59e0b' : '#22c55e';
            return (
              <div key={i}>
                <div className="flex justify-between text-xs mb-0.5">
                  <span className="text-gray-400 truncate max-w-[140px]">{t.label}</span>
                  <span style={{ color }}>{t.current.toFixed(0)}°C</span>
                </div>
                <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(pct, 100)}%`, background: color }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
