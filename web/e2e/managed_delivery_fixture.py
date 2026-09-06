"""Test-only network fault at native outgoing WS frames, after real dispatch."""

from hashlib import sha256
import json
from pathlib import Path
import threading


def install_delivery_fault_fixture(app, require_owner, home):
    from fastapi import HTTPException, Request
    from agent_native.chat import issue_binding
    from agent_native.identity import OWNER
    from tui_gateway.ws import WSTransport

    lock = threading.Lock()
    rules = {}
    original_send = WSTransport._safe_send_many

    async def send_with_one_lost_ack(transport, lines):
        retained = []
        for line in lines:
            frame = json.loads(line)
            result = frame.get("result") or {}
            receipt = result.get("receipt") if isinstance(result, dict) else None
            binding = transport.managed_chat
            dropped = False
            if binding and receipt and result.get("status") == "streaming":
                with lock:
                    rule = rules.get(binding.agent_id)
                    if rule and rule["armed"]:
                        rule["armed"] = False
                        rule["dropped"].append(receipt["id"])
                        dropped = True
            if not dropped:
                retained.append(line)
        # Native requests, model invocations, transcript writes, events and all
        # receipt/status responses are untouched. Only one reply frame is lost.
        await original_send(transport, retained)

    WSTransport._safe_send_many = send_with_one_lost_ack

    @app.post("/__e2e__/drop-next-managed-ack")
    def arm(request: Request, body: dict):
        require_owner(request)
        binding = issue_binding(actor=OWNER, agent_id=body["agent_id"])
        with lock:
            rules[binding.agent_id] = {"armed": True, "dropped": []}
        return {"armed": True}

    @app.get("/__e2e__/managed-delivery/{agent_id}")
    def evidence(request: Request, agent_id: str, attach_token: str):
        require_owner(request)
        binding = issue_binding(actor=OWNER, agent_id=agent_id)
        if len(attach_token) != 32 or any(
            c not in "0123456789abcdef" for c in attach_token
        ):
            raise HTTPException(400, "Invalid test browser attach token")
        client_key = sha256(
            (binding.session_id + "\0" + attach_token).encode()
        ).hexdigest()
        path = (
            Path(home) / "agent-native" / "chat-clients" / client_key / "composer.json"
        )
        snapshot = json.loads(path.read_text()) if path.exists() else None
        with lock:
            dropped = list((rules.get(agent_id) or {}).get("dropped", []))
        return {"dropped_receipts": dropped, "composer": snapshot}

    app.router.routes.insert(0, app.router.routes.pop())
