import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import { agentsEndpoint, type Agent } from '@/lib/agent-native';
import { fetchJSON } from '@/lib/api';
import ChatPage from './ChatPage';

export default function AgentChatPage() {
  const { agentId = '' } = useParams<{ agentId: string }>();
  const [loaded, setLoaded] = useState<{ id: string; agent?: Agent; error?: boolean }>({ id: '' });
  useEffect(() => {
    let active = true;
    void fetchJSON<{ agent: Agent; mode: string }>(`${agentsEndpoint}/${encodeURIComponent(agentId)}/chat`, { method: 'POST' })
      .then((result) => {
        if (result.mode !== 'conversation_only' || result.agent.id !== agentId) throw new Error('Agent chat is unavailable');
        if (active) setLoaded({ id: agentId, agent: result.agent });
      })
      .catch(() => { if (active) setLoaded({ id: agentId, error: true }); });
    return () => { active = false; };
  }, [agentId]);
  const agent = loaded.id === agentId ? loaded.agent : undefined;
  return <div className="flex min-h-0 flex-1 flex-col gap-3">
    <Link to={`/agents/${encodeURIComponent(agentId)}`} className="text-sm underline underline-offset-4">Agent details</Link>
    {loaded.id === agentId && loaded.error ? <p role="alert">Could not load this agent. Return to its details and try again.</p> : !agent ? <p role="status">Loading agent conversation…</p> : <>
      <header aria-label="Conversation agent" className="space-y-1 rounded-lg border p-3">
        <h1 className="text-xl font-semibold">{agent.name}</h1>
        <p className="whitespace-pre-wrap break-words text-sm">{agent.purpose}</p>
        <p className="text-xs text-muted-foreground">Purpose revision {agent.soul_revision} · Conversation only · Use agent details to view and control project work</p>
      </header>
      <ChatPage key={`${agent.id}:${agent.soul_revision}`} managedAgent={agent} />
    </>}
  </div>;
}
