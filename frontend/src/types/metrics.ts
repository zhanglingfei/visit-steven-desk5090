export interface CpuMetrics {
  percent_per_core: number[];
  percent_overall: number;
  freq_current: number | null;
  freq_max: number | null;
  load_avg: [number, number, number];
  core_count: number;
  thread_count: number;
}

export interface MemoryMetrics {
  ram_total: number;
  ram_used: number;
  ram_percent: number;
  swap_total: number;
  swap_used: number;
  swap_percent: number;
}

export interface DiskPartition {
  device: string;
  mountpoint: string;
  total: number;
  used: number;
  percent: number;
}

export interface DiskMetrics {
  partitions: DiskPartition[];
  read_rate: number;
  write_rate: number;
}

export interface NetworkInterface {
  name: string;
  bytes_sent_rate: number;
  bytes_recv_rate: number;
}

export interface NetworkMetrics {
  interfaces: NetworkInterface[];
  total_sent_rate: number;
  total_recv_rate: number;
  connection_count: number;
}

export interface GpuMetrics {
  name: string | null;
  utilization: number | null;
  vram_total: number | null;
  vram_used: number | null;
  temperature: number | null;
  available: boolean;
}

export interface TemperatureSensor {
  label: string;
  current: number;
  high: number | null;
  critical: number | null;
}

export interface ProcessInfo {
  pid: number;
  name: string;
  cpu_percent: number;
  memory_percent: number;
  status: string;
  username: string;
}

export interface SystemMetrics {
  timestamp: number;
  cpu: CpuMetrics;
  memory: MemoryMetrics;
  disk: DiskMetrics;
  network: NetworkMetrics;
  gpu: GpuMetrics;
  temperatures: TemperatureSensor[];
  processes: ProcessInfo[];
}

export interface SystemInfo {
  hostname: string;
  os: string;
  kernel: string;
  cpu_model: string;
  cpu_cores: number;
  cpu_threads: number;
  ram_total: number;
  uptime: number;
}
