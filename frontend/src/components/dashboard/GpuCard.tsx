import { SystemMetrics } from '../../types/metrics';
import MetricGauge from './MetricGauge';

interface Props {
  current: SystemMetrics | null;
}

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 ** 3);
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / (1024 ** 2)).toFixed(0)} MB`;
}

export default function GpuCard({ current }: Props) {
  const gpu = current?.gpu;

  if (!gpu?.available) {
    return (
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">GPU</h3>
        <div className="text-xs text-gray-600 text-center py-4">No GPU detected</div>
      </div>
    );
  }

  // Check if we have detailed metrics (NVIDIA/ROCm) or basic (hwmon)
  const hasDetailedMetrics = gpu.utilization !== null && gpu.utilization !== undefined;
  const hasVramInfo = gpu.vram_total && gpu.vram_used;

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-300">GPU</h3>
        <span className="text-xs text-gray-500">{gpu.name}</span>
      </div>

      <div className="flex items-center justify-around">
        {hasDetailedMetrics ? (
          <div className="relative">
            <MetricGauge
              value={gpu.utilization ?? 0}
              label="Utilization"
              size={80}
              color="#f472b6"
            />
          </div>
        ) : (
          <div className="text-center py-2">
            <div className="text-xs text-gray-500 mb-1">Status</div>
            <div className="text-sm text-green-400 font-medium">Active</div>
            <div className="text-xs text-gray-600 mt-1">Basic monitoring</div>
          </div>
        )}
        {hasVramInfo && (
          <div className="relative">
            <MetricGauge
              value={(gpu.vram_used! / gpu.vram_total!) * 100}
              label="VRAM"
              size={80}
              color="#a78bfa"
            />
          </div>
        )}
      </div>

      <div className="mt-3 space-y-1 text-xs">
        {hasVramInfo && (
          <div className="flex justify-between text-gray-400">
            <span>VRAM</span>
            <span>{formatBytes(gpu.vram_used!)} / {formatBytes(gpu.vram_total!)}</span>
          </div>
        )}
        {gpu.temperature != null && (
          <div className="flex justify-between text-gray-400">
            <span>Temperature</span>
            <span className={gpu.temperature > 85 ? 'text-red-400' : gpu.temperature > 70 ? 'text-amber-400' : ''}>
              {gpu.temperature}°C
            </span>
          </div>
        )}
        {!hasDetailedMetrics && !hasVramInfo && gpu.temperature === null && (
          <div className="text-xs text-gray-600 text-center py-2">
            Limited info available
            <br />
            <span className="text-gray-700">Install ROCm for full metrics</span>
          </div>
        )}
      </div>
    </div>
  );
}
