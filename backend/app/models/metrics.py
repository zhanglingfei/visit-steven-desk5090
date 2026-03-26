from pydantic import BaseModel


class CpuMetrics(BaseModel):
    percent_per_core: list[float]
    percent_overall: float
    freq_current: float | None = None
    freq_max: float | None = None
    load_avg: tuple[float, float, float]
    core_count: int
    thread_count: int


class MemoryMetrics(BaseModel):
    ram_total: int
    ram_used: int
    ram_percent: float
    swap_total: int
    swap_used: int
    swap_percent: float


class DiskPartition(BaseModel):
    device: str
    mountpoint: str
    total: int
    used: int
    percent: float


class DiskMetrics(BaseModel):
    partitions: list[DiskPartition]
    read_rate: float  # bytes/s
    write_rate: float  # bytes/s


class NetworkInterface(BaseModel):
    name: str
    bytes_sent_rate: float  # bytes/s
    bytes_recv_rate: float  # bytes/s


class NetworkMetrics(BaseModel):
    interfaces: list[NetworkInterface]
    total_sent_rate: float
    total_recv_rate: float
    connection_count: int


class GpuMetrics(BaseModel):
    name: str | None = None
    utilization: float | None = None
    vram_total: int | None = None
    vram_used: int | None = None
    temperature: float | None = None
    available: bool = False


class TemperatureSensor(BaseModel):
    label: str
    current: float
    high: float | None = None
    critical: float | None = None


class ProcessInfo(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str
    username: str


class SystemMetrics(BaseModel):
    timestamp: float
    cpu: CpuMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    network: NetworkMetrics
    gpu: GpuMetrics
    temperatures: list[TemperatureSensor]
    processes: list[ProcessInfo]


class SystemInfo(BaseModel):
    hostname: str
    os: str
    kernel: str
    cpu_model: str
    cpu_cores: int
    cpu_threads: int
    ram_total: int
    uptime: float
