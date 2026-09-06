import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface Props { channel: string; agentId: string }

/** Connection only; native TUI events own reply progress and errors. */
export function ManagedChatStatus({ channel, agentId }: Props) {
  const [status, setStatus] = useState('Connecting conversation activity…');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    let socket: WebSocket | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    void api.buildWsUrl('/api/events', { channel }).then((url) => {
      if (!active) return;
      socket = new WebSocket(url);
      socket.onopen = () => { if (active) setStatus('Conversation connected'); };
      socket.onmessage = (event) => {
        if (!active) return;
        try {
          const frame = JSON.parse(String(event.data));
          if (frame.params?.type !== 'session.info') return;
          const info = frame.params.payload;
          if (info?.managed_agent?.id !== agentId) return;
          setStatus(`${info.model || 'Configured model'} · Conversation connected`);
        } catch { /* Ignore unrelated frames on the native event stream. */ }
      };
      socket.onclose = () => {
        if (!active) return;
        setStatus('Conversation activity disconnected; reconnecting…');
        timer = setTimeout(() => setRetry((n) => n + 1), 2000);
      };
    }).catch(() => { if (active) setStatus('Conversation activity unavailable. Reload to reconnect.'); });
    return () => { active = false; clearTimeout(timer); socket?.close(); };
  }, [channel, agentId, retry]);
  return <p role="status" aria-label="Conversation connection" className="text-xs text-muted-foreground">{status}</p>;
}
