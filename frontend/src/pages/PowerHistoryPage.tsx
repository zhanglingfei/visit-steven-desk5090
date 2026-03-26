import { useState } from 'react';
import { Calendar, Search, Zap, TrendingUp, Clock, Database } from 'lucide-react';
import { getPowerHistory, getRecentReadings } from '../api/power';
import { PowerHistoryResponse } from '../types/power';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

function formatKwh(kwh: number): string {
  if (kwh >= 1000) return `${(kwh / 1000).toFixed(3)} MWh`;
  if (kwh >= 1) return `${kwh.toFixed(4)} kWh`;
  return `${(kwh * 1000).toFixed(2)} Wh`;
}

function formatWatts(watts: number): string {
  if (watts >= 1000) return `${(watts / 1000).toFixed(2)} kW`;
  return `${watts.toFixed(1)} W`;
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' });
}

// Convert a Date to datetime-local string
// datetime-local input uses local system time, so we just format the Date directly
function formatDateToInput(date: Date): string {
  // toISOString returns UTC time, so we need to adjust for local timezone
  const tzOffset = date.getTimezoneOffset() * 60 * 1000; // in milliseconds
  const localDate = new Date(date.getTime() - tzOffset);
  return localDate.toISOString().slice(0, 16);
}

// Parse a datetime-local string to UTC Date
// datetime-local input returns local time (JST), and new Date() treats it as local
// So we just need to return the Date object directly
function parseLocalInputToUTC(localString: string): Date {
  // new Date('2026-03-25T15:06') treats the input as local time (JST)
  // and the resulting Date object is already the correct UTC timestamp
  return new Date(localString);
}

// Get current datetime string for max attribute (in local time)
function getCurrentDateTime(): string {
  const now = new Date();
  return formatDateToInput(now);
}

// Check if a datetime-local string is in the future
function isFutureDate(dateString: string): boolean {
  const date = parseLocalInputToUTC(dateString);
  const now = new Date();
  return date.getTime() > now.getTime();
}

export default function PowerHistoryPage() {
  // Initialize with local times
  const [startDate, setStartDate] = useState<string>(
    formatDateToInput(new Date(Date.now() - 24 * 60 * 60 * 1000))
  );
  const [endDate, setEndDate] = useState<string>(
    formatDateToInput(new Date())
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PowerHistoryResponse | null>(null);
  const [chartData, setChartData] = useState<{ time: string; watts: number }[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleQuery = async () => {
    setLoading(true);
    setError(null);
    setResult(null); // Clear previous result
    setChartData([]); // Clear previous chart data
    try {
      // Validate no future dates
      if (isFutureDate(startDate)) {
        setError('開始日は未来にできません / Start date cannot be in the future');
        setLoading(false);
        return;
      }
      if (isFutureDate(endDate)) {
        setError('終了日は未来にできません / End date cannot be in the future');
        setLoading(false);
        return;
      }

      // Parse datetime-local input to Date objects for API
      const startUTC = parseLocalInputToUTC(startDate);
      const endUTC = parseLocalInputToUTC(endDate);

      if (startUTC >= endUTC) {
        setError('開始日は終了日より前である必要があります / Start date must be before end date');
        setLoading(false);
        return;
      }

      // Get history stats
      const history = await getPowerHistory(startUTC, endUTC);
      setResult(history);

      // Get readings for chart (up to 24 hours)
      const hoursDiff = (endUTC.getTime() - startUTC.getTime()) / (1000 * 60 * 60);
      const chartHours = Math.min(Math.ceil(hoursDiff), 24);

      const recent = await getRecentReadings(chartHours);
      const filtered = recent.readings.filter(
        r => r.timestamp >= startUTC.getTime() / 1000 && r.timestamp <= endUTC.getTime() / 1000
      );

      setChartData(
        filtered.map(r => ({
          time: new Date(r.timestamp * 1000).toLocaleTimeString('ja-JP', { timeZone: 'Asia/Tokyo' }),
          watts: r.watts,
        }))
      );
    } catch (err: any) {
      setError(err.response?.data?.detail || '履歴の取得に失敗しました / Failed to fetch power history');
    } finally {
      setLoading(false);
    }
  };

  // Quick select handlers
  const setQuickRange = async (hours: number) => {
    const end = new Date();
    const start = new Date(Date.now() - hours * 60 * 60 * 1000);
    const newEndDate = formatDateToInput(end);
    const newStartDate = formatDateToInput(start);
    setEndDate(newEndDate);
    setStartDate(newStartDate);

    // Automatically trigger query with new dates
    setLoading(true);
    setError(null);
    try {
      const startUTC = parseLocalInputToUTC(newStartDate);
      const endUTC = parseLocalInputToUTC(newEndDate);

      // Get history stats
      const history = await getPowerHistory(startUTC, endUTC);
      setResult(history);

      // Get readings for chart (up to 24 hours)
      const hoursDiff = (endUTC.getTime() - startUTC.getTime()) / (1000 * 60 * 60);
      const chartHours = Math.min(Math.ceil(hoursDiff), 24);

      const recent = await getRecentReadings(chartHours);
      const filtered = recent.readings.filter(
        r => r.timestamp >= startUTC.getTime() / 1000 && r.timestamp <= endUTC.getTime() / 1000
      );

      setChartData(
        filtered.map(r => ({
          time: new Date(r.timestamp * 1000).toLocaleTimeString('ja-JP', { timeZone: 'Asia/Tokyo' }),
          watts: r.watts,
        }))
      );
    } catch (err: any) {
      setError(err.response?.data?.detail || '履歴の取得に失敗しました / Failed to fetch power history');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-green-500/20 rounded-lg">
          <Calendar className="w-6 h-6 text-green-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-100">Energy History</h1>
          <p className="text-sm text-gray-500">Query power consumption by date range (JST/日本時間)</p>
        </div>
      </div>

      {/* Query Form */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Start Date (JST)</label>
            <input
              type="datetime-local"
              value={startDate}
              max={getCurrentDateTime()}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500/50"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">End Date (JST)</label>
            <input
              type="datetime-local"
              value={endDate}
              max={getCurrentDateTime()}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500/50"
            />
          </div>

          <div>
            <button
              onClick={handleQuery}
              disabled={loading}
              className="w-full px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-green-600/50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Querying...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  Query
                </>
              )}
            </button>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setQuickRange(1)}
              className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded-lg transition-colors"
            >
              1H
            </button>
            <button
              onClick={() => setQuickRange(6)}
              className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded-lg transition-colors"
            >
              6H
            </button>
            <button
              onClick={() => setQuickRange(24)}
              className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded-lg transition-colors"
            >
              24H
            </button>
            <button
              onClick={() => setQuickRange(168)}
              className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded-lg transition-colors"
            >
              7D
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {/* Total Energy */}
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-4 h-4 text-yellow-400" />
                <span className="text-sm text-gray-400">Total Energy</span>
              </div>
              <p className="text-2xl font-bold text-gray-100">{formatKwh(result.total_kwh)}</p>
              <p className="text-xs text-gray-500 mt-1">
                {result.hours_span.toFixed(1)} hours period
              </p>
            </div>

            {/* Average Power */}
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-blue-400" />
                <span className="text-sm text-gray-400">Average Power</span>
              </div>
              <p className="text-2xl font-bold text-gray-100">{formatWatts(result.avg_watts)}</p>
              <p className="text-xs text-gray-500 mt-1">
                Based on {result.readings_count} readings
              </p>
            </div>

            {/* Peak Power */}
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-green-400" />
                <span className="text-sm text-gray-400">Peak Power</span>
              </div>
              <p className="text-2xl font-bold text-gray-100">{formatWatts(result.max_watts)}</p>
              <p className="text-xs text-gray-500 mt-1">
                Min: {formatWatts(result.min_watts)}
              </p>
            </div>

            {/* Time Span */}
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="w-4 h-4 text-purple-400" />
                <span className="text-sm text-gray-400">Time Span</span>
              </div>
              <p className="text-lg font-bold text-gray-100">
                {result.hours_span >= 24
                  ? `${(result.hours_span / 24).toFixed(1)} days`
                  : `${result.hours_span.toFixed(1)} hours`}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {result.readings_count} data points
              </p>
            </div>
          </div>

          {/* Chart */}
          {chartData.length > 0 && (
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 mb-6">
              <h3 className="text-sm font-medium text-gray-300 mb-4">Power Usage During Period</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="historyGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
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
                      stroke="#10b981"
                      fill="url(#historyGradient)"
                      strokeWidth={2}
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Period Info */}
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Database className="w-4 h-4 text-gray-400" />
              <h3 className="text-sm font-medium text-gray-300">Query Details</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">From:</span>
                <span className="text-gray-300 ml-2">{formatDateTime(result.start_date)}</span>
              </div>
              <div>
                <span className="text-gray-500">To:</span>
                <span className="text-gray-300 ml-2">{formatDateTime(result.end_date)}</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
