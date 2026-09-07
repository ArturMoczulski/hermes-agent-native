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


class WorkLimits(BaseModel):
    model_config = ConfigDict(extra='forbid')
    timeout_seconds: int = Field(strict=True, ge=1, le=3600)
    max_iterations: int = Field(strict=True, ge=1, le=100)


class ConfigureWork(WorkLimits):
    expected_revision: int = Field(strict=True, ge=1)


class CreateAgent(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=20000)
    work: WorkLimits | None = None


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


@router.post('/{agent_id}/setup/retry')
def retry_agent_setup(agent_id: str, actor=Depends(owner_session)):
    from agent_native.startup import retry_setup
    from agent_native.plane_operation_lock import OperationBusy
    with connect_closing(board='default') as conn:
        try:
            return retry_setup(conn, actor=actor, agent_id=agent_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
        except (identity.ConflictError, OperationBusy) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/{agent_id}/chat')
def open_agent_chat(agent_id: str, actor=Depends(owner_session)):
    from agent_native.chat import issue_binding
    try:
        binding = issue_binding(actor=actor, agent_id=agent_id)
        with connect_closing(board='default') as conn:
            agent = identity.get_root(conn, actor=actor, agent_id=agent_id)
        binding.validate()
        return {'agent': agent, 'session_id': binding.session_id, 'mode': 'conversation_only'}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='Agent not found') from exc
    except (PermissionError, identity.ConflictError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/{agent_id}/work')
def configure_work(agent_id: str, body: ConfigureWork, actor=Depends(owner_session)):
    from agent_native.work_state import configure
    with connect_closing(board='default') as conn:
        try:
            configure(conn, actor=actor, agent_id=agent_id, expected_revision=body.expected_revision,
                      limits=body.model_dump(exclude={'expected_revision'}))
            return identity.get_root(conn, actor=actor, agent_id=agent_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/{agent_id}/work/pause')
def pause_work(agent_id: str, actor=Depends(owner_session)):
    from agent_native.work_state import request_pause
    with connect_closing(board='default') as conn:
        try:
            request_pause(conn, actor=actor, agent_id=agent_id)
            return identity.get_root(conn, actor=actor, agent_id=agent_id)
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get('/{agent_id}/stories/{story_id}/versions/{version}')
def read_story(agent_id: str, story_id: str, version: int, actor=Depends(owner_session)):
    from agent_native.story_store import read_story as read
    with connect_closing(board='default') as conn:
        try:
            identity.get_root(conn, actor=actor, agent_id=agent_id)
            return read(conn,agent_id,story_id,version)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Story not found') from exc
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=409, detail='Story content could not be verified') from exc
