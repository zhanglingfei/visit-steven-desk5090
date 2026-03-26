import { useCallback, useEffect, useRef, useState } from 'react';
import { SystemMetrics } from '../types/metrics';

const MAX_HISTORY = 60;

export function useMetricsSocket() {
  const [current, setCurrent] = useState<SystemMetrics | null>(null);
  const [history, setHistory] = useState<SystemMetrics[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const timerRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(
      `${proto}//${window.location.host}/api/ws/metrics?token=${token}`
    );
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      retryRef.current = 0;
    };

    ws.onmessage = (event) => {
      const data: SystemMetrics = JSON.parse(event.data);
      setCurrent(data);
      setHistory((prev) => {
        const next = [...prev, data];
        return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next;
      });
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      // Exponential backoff reconnect
      const delay = Math.min(1000 * 2 ** retryRef.current, 30000);
      retryRef.current++;
      timerRef.current = window.setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { current, history, connected };
}
