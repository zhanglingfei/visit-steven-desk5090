import { Wifi, WifiOff } from 'lucide-react';
import { useMetricsSocket } from '../hooks/useMetricsSocket';
import CpuChart from '../components/dashboard/CpuChart';
import MemoryChart from '../components/dashboard/MemoryChart';
import DiskChart from '../components/dashboard/DiskChart';
import NetworkChart from '../components/dashboard/NetworkChart';
import GpuCard from '../components/dashboard/GpuCard';
import TemperatureCard from '../components/dashboard/TemperatureCard';
import ProcessTable from '../components/dashboard/ProcessTable';
import SystemInfoCard from '../components/dashboard/SystemInfoCard';
import LoadAverageCard from '../components/dashboard/LoadAverageCard';

export default function DashboardPage() {
  const { current, history, connected } = useMetricsSocket();

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-gray-100">Dashboard</h1>
        <div className="flex items-center gap-2">
          {connected ? (
            <Wifi className="w-4 h-4 text-green-400" />
          ) : (
            <WifiOff className="w-4 h-4 text-red-400" />
          )}
          <span className={`text-xs ${connected ? 'text-green-400' : 'text-red-400'}`}>
            {connected ? 'Live' : 'Reconnecting...'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Row 1 */}
        <div className="xl:col-span-1">
          <SystemInfoCard />
        </div>
        <div className="xl:col-span-2">
          <CpuChart current={current} history={history} />
        </div>
        <div className="xl:col-span-1">
          <LoadAverageCard current={current} />
        </div>

        {/* Row 2 */}
        <div className="xl:col-span-2">
          <MemoryChart current={current} history={history} />
        </div>
        <div className="xl:col-span-2">
          <DiskChart current={current} history={history} />
        </div>

        {/* Row 3 */}
        <div className="xl:col-span-2">
          <NetworkChart current={current} history={history} />
        </div>
        <div className="xl:col-span-1">
          <GpuCard current={current} />
        </div>
        <div className="xl:col-span-1">
          <TemperatureCard current={current} />
        </div>

        {/* Row 4 */}
        <div className="xl:col-span-4">
          <ProcessTable current={current} />
        </div>
      </div>
    </div>
  );
}
