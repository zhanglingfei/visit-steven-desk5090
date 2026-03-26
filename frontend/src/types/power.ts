export interface PowerMetrics {
  timestamp: number;
  watts: number;
  voltage: number | null;
  current: number | null;
  source: string;
  total_kwh: number;
  uptime_hours: number;
}

export interface PowerHistoryResponse {
  start_date: string;
  end_date: string;
  total_kwh: number;
  avg_watts: number;
  max_watts: number;
  min_watts: number;
  readings_count: number;
  hours_span: number;
}

export interface PowerReadingEntry {
  timestamp: number;
  watts: number;
}

export interface RecentPowerResponse {
  readings: PowerReadingEntry[];
  count: number;
}
