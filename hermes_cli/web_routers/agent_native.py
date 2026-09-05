"""Owner dashboard operations for inactive agent-native records.

Only the existing dashboard owner session is accepted. Scoped automation tokens
cannot promote themselves to OWNER through request data or general middleware.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from agent_native import identity
from hermes_cli.kanban_db_connect import connect_closing


def owner_session(request: Request):
    from hermes_cli.web_server import _require_token
    _require_token(request)
    return identity.OWNER


router = APIRouter(prefix='/api/agent-native/agents')


class CreateAgent(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=20000)


@router.get('')
def list_agents(actor=Depends(owner_session)):
    with connect_closing(board='default') as conn:
        return identity.list_roots(conn, actor=actor)


@router.post('', status_code=201)
def create_agent(body: CreateAgent, actor=Depends(owner_session)):
    with connect_closing(board='default') as conn:
        try:
            return identity.create_root(conn, actor=actor, **body.model_dump())
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get('/{agent_id}')
def read_agent(agent_id: str, actor=Depends(owner_session)):
    with connect_closing(board='default') as conn:
        try:
            return identity.get_root(conn, actor=actor, agent_id=agent_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
