import { useEffect, useState } from 'react';
import { Wifi, WifiOff, Zap, Battery, Clock, TrendingUp, Activity } from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { usePowerSocket } from '../hooks/usePowerSocket';
import { getRecentReadings } from '../api/power';
import { PowerReadingEntry } from '../types/power';

function formatWatts(watts: number): string {
  if (watts >= 1000) return `${(watts / 1000).toFixed(2)} kW`;
  return `${watts.toFixed(1)} W`;
}

function formatKwh(kwh: number): string {
  if (kwh >= 1000) return `${(kwh / 1000).toFixed(3)} MWh`;
  if (kwh >= 1) return `${kwh.toFixed(3)} kWh`;
  return `${(kwh * 1000).toFixed(1)} Wh`;
}

function formatTime(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleTimeString();
}

function formatDuration(hours: number): string {
  const days = Math.floor(hours / 24);
  const remainingHours = Math.floor(hours % 24);
  const minutes = Math.floor((hours % 1) * 60);

  if (days > 0) return `${days}d ${remainingHours}h ${minutes}m`;
  if (remainingHours > 0) return `${remainingHours}h ${minutes}m`;
  return `${minutes}m`;
}

export default function PowerPage() {
  const { current, history, connected } = usePowerSocket();
  const [historicalData, setHistoricalData] = useState<PowerReadingEntry[]>([]);

  useEffect(() => {
    // Load initial historical data
    getRecentReadings(24).then((data) => {
      setHistoricalData(data.readings);
    });
  }, []);

  // Merge WebSocket history with historical data
  const allReadings = [...historicalData, ...history.map(h => ({ timestamp: h.timestamp, watts: h.watts }))];

  // Remove duplicates based on timestamp
  const uniqueReadings = allReadings.filter((reading, index, self) =>
    index === self.findIndex(r => Math.abs(r.timestamp - reading.timestamp) < 1)
  );

  const chartData = uniqueReadings.map((r) => ({
    time: formatTime(r.timestamp),
    watts: r.watts,
  }));

  // Calculate statistics from current history
  const avgWatts = history.length > 0
    ? history.reduce((sum, h) => sum + h.watts, 0) / history.length
    : 0;

  const maxWatts = history.length > 0
    ? Math.max(...history.map(h => h.watts))
    : 0;

  const minWatts = history.length > 0
    ? Math.min(...history.map(h => h.watts))
    : 0;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-yellow-500/20 rounded-lg">
            <Zap className="w-6 h-6 text-yellow-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-100">Power Monitoring</h1>
            <p className="text-sm text-gray-500">Real-time power consumption and energy usage</p>
          </div>
        </div>
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

      {/* Main Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Current Power */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-4 h-4 text-yellow-400" />
            <span className="text-sm text-gray-400">Current Power</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-gray-100">
              {current ? formatWatts(current.watts) : '--'}
            </span>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Source: <span className="text-gray-400 capitalize">{current?.source || 'Unknown'}</span>
          </div>
        </div>

        {/* Total Energy */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Battery className="w-4 h-4 text-green-400" />
            <span className="text-sm text-gray-400">Total Energy Used</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-gray-100">
              {current ? formatKwh(current.total_kwh) : '--'}
            </span>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Since monitoring started
          </div>
        </div>

        {/* Monitoring Duration */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-400">Monitoring Duration</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-gray-100">
              {current ? formatDuration(current.uptime_hours) : '--'}
            </span>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Continuous logging
          </div>
        </div>

        {/* Average Power */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-purple-400" />
            <span className="text-sm text-gray-400">Average (Last Hour)</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-gray-100">
              {avgWatts > 0 ? formatWatts(avgWatts) : '--'}
            </span>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Range: {minWatts > 0 ? formatWatts(minWatts) : '--'} - {maxWatts > 0 ? formatWatts(maxWatts) : '--'}
          </div>
        </div>
      </div>

      {/* Power Chart */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-gray-300">Power Consumption Over Time</h3>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-yellow-400"></span>
              <span className="text-gray-400">Power (W)</span>
            </span>
          </div>
        </div>

        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="powerGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#facc15" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#facc15" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="time"
                stroke="#6b7280"
                fontSize={10}
                tickLine={false}
                interval="preserveStartEnd"
                minTickGap={50}
              />
              <YAxis
                stroke="#6b7280"
                fontSize={10}
                tickLine={false}
                tickFormatter={(value) => `${value}W`}
              />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                formatter={(value) => [`${Number(value).toFixed(1)} W`, 'Power']}
              />
              <Area
                type="monotone"
                dataKey="watts"
                stroke="#facc15"
                fill="url(#powerGradient)"
                strokeWidth={2}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Additional Details */}
      {current && (current.voltage || current.current) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {current.voltage && (
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
              <span className="text-sm text-gray-400">Voltage</span>
              <p className="text-2xl font-bold text-gray-100 mt-1">{current.voltage.toFixed(2)} V</p>
            </div>
          )}
          {current.current && (
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
              <span className="text-sm text-gray-400">Current</span>
              <p className="text-2xl font-bold text-gray-100 mt-1">{current.current.toFixed(2)} A</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
