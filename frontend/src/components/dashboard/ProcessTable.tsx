import { Activity } from 'lucide-react';
import { SystemMetrics } from '../../types/metrics';

interface Props {
  current: SystemMetrics | null;
}

export default function ProcessTable({ current }: Props) {
  const processes = current?.processes ?? [];

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-4 h-4 text-blue-400" />
        <h3 className="text-sm font-medium text-gray-300">Top Processes</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-2 px-2">PID</th>
              <th className="text-left py-2 px-2">Name</th>
              <th className="text-left py-2 px-2">User</th>
              <th className="text-right py-2 px-2">CPU %</th>
              <th className="text-right py-2 px-2">Mem %</th>
              <th className="text-left py-2 px-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {processes.map((p) => (
              <tr key={p.pid} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="py-2 px-2 text-gray-400 font-mono">{p.pid}</td>
                <td className="py-2 px-2 text-gray-300 truncate max-w-[200px]">{p.name}</td>
                <td className="py-2 px-2 text-gray-500 truncate max-w-[100px]">{p.username}</td>
                <td className="py-2 px-2 text-right">
                  <span className={p.cpu_percent > 50 ? 'text-red-400' : p.cpu_percent > 20 ? 'text-amber-400' : 'text-gray-300'}>
                    {p.cpu_percent.toFixed(1)}
                  </span>
                </td>
                <td className="py-2 px-2 text-right">
                  <span className={p.memory_percent > 10 ? 'text-purple-400' : 'text-gray-300'}>
                    {p.memory_percent.toFixed(1)}
                  </span>
                </td>
                <td className="py-2 px-2">
                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] ${
                    p.status === 'running' ? 'bg-green-500/20 text-green-400' :
                    p.status === 'sleeping' ? 'bg-blue-500/20 text-blue-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {p.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
