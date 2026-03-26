import { useEffect, useState } from 'react';
import { Server, Cpu, HardDrive, Clock } from 'lucide-react';
import api from '../../api/client';
import { SystemInfo } from '../../types/metrics';

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h ${mins}m`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 ** 3);
  return `${gb.toFixed(1)} GB`;
}

export default function SystemInfoCard() {
  const [info, setInfo] = useState<SystemInfo | null>(null);

  useEffect(() => {
    api.get('/system/info').then((res) => setInfo(res.data));
  }, []);

  if (!info) {
    return (
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4 animate-pulse">
        <div className="h-4 bg-gray-800 rounded w-1/2 mb-4"></div>
        <div className="space-y-2">
          <div className="h-3 bg-gray-800 rounded"></div>
          <div className="h-3 bg-gray-800 rounded w-3/4"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4">
        <Server className="w-5 h-5 text-blue-400" />
        <h3 className="text-sm font-medium text-gray-300">System Info</h3>
      </div>

      <div className="space-y-3">
        <div className="flex items-start gap-3">
          <Cpu className="w-4 h-4 text-gray-500 mt-0.5" />
          <div>
            <p className="text-xs text-gray-500">Hostname</p>
            <p className="text-sm text-gray-200 font-mono">{info.hostname}</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Server className="w-4 h-4 text-gray-500 mt-0.5" />
          <div>
            <p className="text-xs text-gray-500">OS</p>
            <p className="text-sm text-gray-200">{info.os}</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Cpu className="w-4 h-4 text-gray-500 mt-0.5" />
          <div>
            <p className="text-xs text-gray-500">CPU</p>
            <p className="text-sm text-gray-200">{info.cpu_model}</p>
            <p className="text-xs text-gray-500">{info.cpu_cores}C / {info.cpu_threads}T</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <HardDrive className="w-4 h-4 text-gray-500 mt-0.5" />
          <div>
            <p className="text-xs text-gray-500">RAM</p>
            <p className="text-sm text-gray-200">{formatBytes(info.ram_total)}</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Clock className="w-4 h-4 text-gray-500 mt-0.5" />
          <div>
            <p className="text-xs text-gray-500">Uptime</p>
            <p className="text-sm text-gray-200">{formatUptime(info.uptime)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
