import { useEffect, useRef, useState, useCallback } from 'react';

export type ConnectionState = 'LIVE' | 'CONNECTING' | 'RECONNECTING' | 'POLLING_FALLBACK';

interface LiveOpsSocketOptions {
  onEvent?: (event: string, data: any) => void;
  enablePollingFallback?: boolean;
  pollingIntervalMs?: number;
}

export function useLiveOpsSocket(options: LiveOpsSocketOptions = {}) {
  const { onEvent, enablePollingFallback = true, pollingIntervalMs = 12000 } = options;
  const [connectionState, setConnectionState] = useState<ConnectionState>('CONNECTING');
  const [lastEvent, setLastEvent] = useState<{ event: string; data: any; timestamp: number } | null>(null);
  const [eventCount, setEventCount] = useState(0);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 3;

  // Use a monotonically increasing generation ID to identify the "current" socket.
  // This eliminates the race condition where an old socket's onclose fires after
  // a new socket has already been created, preventing duplicate connections.
  const generationRef = useRef(0);

  const onEventRef = useRef(onEvent);
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  const connect = useCallback(() => {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

    let wsHost = import.meta.env.VITE_WS_URL;
    if (!wsHost) {
      if (window.location.port === '5173') {
        // Local Vite dev: proxy to backend on 8000
        wsHost = `${wsProto}//${window.location.hostname}:8000/ws/operations/`;
      } else {
        // Same-origin production
        wsHost = `${wsProto}//${window.location.host}/ws/operations/`;
      }
    }

    // Increment generation — any socket from a previous generation is stale.
    const thisGeneration = ++generationRef.current;

    try {
      setConnectionState(retryCountRef.current > 0 ? 'RECONNECTING' : 'CONNECTING');
      const ws = new WebSocket(wsHost);
      socketRef.current = ws;

      ws.onopen = () => {
        // Only process if this socket is still the current generation
        if (generationRef.current !== thisGeneration) return;
        setConnectionState('LIVE');
        retryCountRef.current = 0;
      };

      ws.onmessage = (event) => {
        // Ignore messages from stale sockets
        if (generationRef.current !== thisGeneration) return;

        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'pong' || payload.type === 'connection.ack') {
            return;
          }

          const eventType = payload.type || 'booking.updated';
          const eventData = payload.data || payload;

          setLastEvent({
            event: eventType,
            data: eventData,
            timestamp: Date.now(),
          });
          setEventCount((prev) => prev + 1);

          if (onEventRef.current) {
            onEventRef.current(eventType, eventData);
          }
        } catch (err) {
          console.error('Error parsing WS message:', err);
        }
      };

      ws.onerror = () => {
        // onerror always triggers onclose, handle there
      };

      ws.onclose = () => {
        // KEY FIX: Only process onclose for the CURRENT generation socket.
        // If this socket is stale (from a previous connect() call), ignore it entirely.
        // This prevents the race where old socket's onclose schedules a reconnect
        // while the new socket already exists.
        if (generationRef.current !== thisGeneration) return;

        socketRef.current = null;

        if (retryCountRef.current < maxRetries) {
          retryCountRef.current += 1;
          setConnectionState('RECONNECTING');
          reconnectTimeoutRef.current = window.setTimeout(() => {
            if (generationRef.current === thisGeneration) {
              connect();
            }
          }, Math.min(1000 * Math.pow(2, retryCountRef.current), 5000));
        } else if (enablePollingFallback) {
          setConnectionState('POLLING_FALLBACK');
        }
      };
    } catch (err) {
      if (enablePollingFallback) {
        setConnectionState('POLLING_FALLBACK');
      }
    }
  }, [enablePollingFallback]);

  useEffect(() => {
    connect();

    // Heartbeat ping interval
    const pingInterval = window.setInterval(() => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
      }
    }, 25000);

    return () => {
      // Increment generation to invalidate the current socket — its onclose
      // will see a stale generation and do nothing (no spurious reconnect).
      generationRef.current++;
      window.clearInterval(pingInterval);
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }
      socketRef.current?.close();
    };
  }, [connect]);

  // Handle polling fallback
  useEffect(() => {
    if (connectionState === 'POLLING_FALLBACK') {
      const pollTimer = window.setInterval(() => {
        if (onEventRef.current) {
          onEventRef.current('poll.trigger', { timestamp: Date.now() });
        }
      }, pollingIntervalMs);

      return () => window.clearInterval(pollTimer);
    }
  }, [connectionState, pollingIntervalMs]);

  const reconnect = useCallback(() => {
    // Close existing socket and invalidate its generation before reconnecting.
    // The old socket's onclose will see a stale generation and not schedule a duplicate.
    socketRef.current?.close();
    socketRef.current = null;
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
    }
    retryCountRef.current = 0;
    connect();
  }, [connect]);

  return {
    connectionState,
    lastEvent,
    eventCount,
    reconnect,
  };
}
