import asyncio
import platform
import time
from functools import partial

import psutil

from app.models.metrics import (
    CpuMetrics,
    DiskMetrics,
    DiskPartition,
    GpuMetrics,
    MemoryMetrics,
    NetworkInterface,
    NetworkMetrics,
    ProcessInfo,
    SystemInfo,
    SystemMetrics,
    TemperatureSensor,
)
from app.utils.gpu import get_gpu_metrics


class MetricsCollector:
    def __init__(self):
        self._prev_disk_io = None
        self._prev_net_io = None
        self._prev_time = None
        # Prime cpu_percent so first real call returns meaningful values
        psutil.cpu_percent(interval=0, percpu=True)

    def _collect_cpu(self) -> CpuMetrics:
        per_core = psutil.cpu_percent(interval=0, percpu=True)
        overall = sum(per_core) / len(per_core) if per_core else 0.0
        freq = psutil.cpu_freq()
        load = psutil.getloadavg()
        return CpuMetrics(
            percent_per_core=per_core,
            percent_overall=round(overall, 1),
            freq_current=round(freq.current, 0) if freq else None,
            freq_max=round(freq.max, 0) if freq and freq.max else None,
            load_avg=(round(load[0], 2), round(load[1], 2), round(load[2], 2)),
            core_count=psutil.cpu_count(logical=False) or 0,
            thread_count=psutil.cpu_count(logical=True) or 0,
        )

    def _collect_memory(self) -> MemoryMetrics:
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        return MemoryMetrics(
            ram_total=vm.total,
            ram_used=vm.used,
            ram_percent=vm.percent,
            swap_total=sw.total,
            swap_used=sw.used,
            swap_percent=sw.percent,
        )

    def _collect_disk(self) -> DiskMetrics:
        now = time.time()
        partitions = []
        seen = set()
        for p in psutil.disk_partitions(all=False):
            if p.mountpoint in seen:
                continue
            seen.add(p.mountpoint)
            try:
                usage = psutil.disk_usage(p.mountpoint)
                partitions.append(
                    DiskPartition(
                        device=p.device,
                        mountpoint=p.mountpoint,
                        total=usage.total,
                        used=usage.used,
                        percent=usage.percent,
                    )
                )
            except PermissionError:
                continue

        io = psutil.disk_io_counters()
        read_rate = 0.0
        write_rate = 0.0
        if self._prev_disk_io and self._prev_time:
            dt = now - self._prev_time
            if dt > 0:
                read_rate = (io.read_bytes - self._prev_disk_io.read_bytes) / dt
                write_rate = (io.write_bytes - self._prev_disk_io.write_bytes) / dt
        self._prev_disk_io = io

        return DiskMetrics(
            partitions=partitions,
            read_rate=round(max(read_rate, 0), 0),
            write_rate=round(max(write_rate, 0), 0),
        )

    def _collect_network(self) -> NetworkMetrics:
        now = time.time()
        counters = psutil.net_io_counters(pernic=True)
        interfaces = []
        total_sent_rate = 0.0
        total_recv_rate = 0.0

        for name, io in counters.items():
            if name == "lo":
                continue
            sent_rate = 0.0
            recv_rate = 0.0
            if self._prev_net_io and name in self._prev_net_io and self._prev_time:
                dt = now - self._prev_time
                if dt > 0:
                    prev = self._prev_net_io[name]
                    sent_rate = (io.bytes_sent - prev.bytes_sent) / dt
                    recv_rate = (io.bytes_recv - prev.bytes_recv) / dt
            total_sent_rate += max(sent_rate, 0)
            total_recv_rate += max(recv_rate, 0)
            interfaces.append(
                NetworkInterface(
                    name=name,
                    bytes_sent_rate=round(max(sent_rate, 0), 0),
                    bytes_recv_rate=round(max(recv_rate, 0), 0),
                )
            )

        self._prev_net_io = counters

        try:
            conn_count = len(psutil.net_connections(kind="inet"))
        except (psutil.AccessDenied, PermissionError):
            conn_count = 0

        return NetworkMetrics(
            interfaces=interfaces,
            total_sent_rate=round(total_sent_rate, 0),
            total_recv_rate=round(total_recv_rate, 0),
            connection_count=conn_count,
        )

    def _collect_temperatures(self) -> list[TemperatureSensor]:
        sensors = []
        try:
            temps = psutil.sensors_temperatures()
            for chip, entries in temps.items():
                for entry in entries:
                    label = f"{chip}/{entry.label}" if entry.label else chip
                    sensors.append(
                        TemperatureSensor(
                            label=label,
                            current=entry.current,
                            high=entry.high,
                            critical=entry.critical,
                        )
                    )
        except (AttributeError, RuntimeError):
            pass
        return sensors

    def _collect_processes(self) -> list[ProcessInfo]:
        procs = []
        for p in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent", "status", "username"]
        ):
            try:
                info = p.info
                procs.append(
                    ProcessInfo(
                        pid=info["pid"],
                        name=info["name"] or "unknown",
                        cpu_percent=info["cpu_percent"] or 0.0,
                        memory_percent=round(info["memory_percent"] or 0.0, 1),
                        status=info["status"] or "unknown",
                        username=info["username"] or "unknown",
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda p: p.cpu_percent, reverse=True)
        return procs[:15]

    def collect_all(self) -> SystemMetrics:
        cpu = self._collect_cpu()
        memory = self._collect_memory()
        disk = self._collect_disk()
        network = self._collect_network()
        gpu = get_gpu_metrics()
        temps = self._collect_temperatures()
        procs = self._collect_processes()
        now = time.time()
        self._prev_time = now
        return SystemMetrics(
            timestamp=now,
            cpu=cpu,
            memory=memory,
            disk=disk,
            network=network,
            gpu=gpu,
            temperatures=temps,
            processes=procs,
        )

    @staticmethod
    def get_system_info() -> SystemInfo:
        uname = platform.uname()
        cpu_model = uname.processor or uname.machine
        # Try to get a better CPU model name
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu_model = line.split(":")[1].strip()
                        break
        except (FileNotFoundError, PermissionError):
            pass

        return SystemInfo(
            hostname=uname.node,
            os=f"{platform.system()} {platform.release()}",
            kernel=uname.release,
            cpu_model=cpu_model,
            cpu_cores=psutil.cpu_count(logical=False) or 0,
            cpu_threads=psutil.cpu_count(logical=True) or 0,
            ram_total=psutil.virtual_memory().total,
            uptime=time.time() - psutil.boot_time(),
        )


# Singleton
collector = MetricsCollector()


async def collect_metrics_async() -> SystemMetrics:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, collector.collect_all)
