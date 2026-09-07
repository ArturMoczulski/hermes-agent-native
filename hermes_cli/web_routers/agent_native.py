"""Owner dashboard operations for agent-native identity, work and inspection.

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
model_router = APIRouter(prefix='/api/agent-native/models')


class WorkLimits(BaseModel):
    model_config = ConfigDict(extra='forbid')
    timeout_seconds: int = Field(strict=True, ge=1, le=3600)
    max_iterations: int = Field(strict=True, ge=1, le=100)


class ConfigureWork(WorkLimits):
    expected_revision: int = Field(strict=True, ge=1)


class ModelChoice(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    provider: str = Field(min_length=1, max_length=256)
    model: str = Field(min_length=1, max_length=256)
    reasoning_effort: str = Field(default='default', min_length=1, max_length=32, strict=True)


class ChangeModel(ModelChoice):
    expected_revision: int = Field(strict=True, ge=1)


class CreateAgent(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=20000)
    work: WorkLimits | None = None
    model_selection: ModelChoice | None = None


@router.get('')
def list_agents(actor=Depends(owner_session)):
    with connect_closing(board='default') as conn:
        return identity.list_roots(conn, actor=actor)


@router.post('', status_code=201)
def create_agent(body: CreateAgent, actor=Depends(owner_session)):
    with connect_closing(board='default') as conn:
        try:
            return identity.create_root(conn, actor=actor, **body.model_dump(exclude_unset=True))
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


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
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


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
        except LookupError as exc:
            raise HTTPException(status_code=404, detail='Story not found') from exc
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=409, detail='Story content could not be verified') from exc


@router.get('/{agent_id}/outputs/{output_id}/versions/{version}')
def read_output(agent_id: str, output_id: str, version: int, actor=Depends(owner_session)):
    from agent_native.output_store import read_output as read
    with connect_closing(board='default') as conn:
        try:
            identity.get_root(conn, actor=actor, agent_id=agent_id)
            return read(conn, agent_id, output_id, version)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail='Output not found') from exc
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=409, detail='Output content could not be verified') from exc


@router.get('/{agent_id}/planning')
def read_planning(agent_id: str, actor=Depends(owner_session)):
    from hermes_constants import get_hermes_home
    from agent_native.planning_view import (
        PlanningConfigurationRequired, PlanningNotReady, read_planning as read,
    )
    from agent_native.plane_reads import PlaneReadError, PlaneScopeError
    with connect_closing(board='default') as conn:
        try:
            return read(conn, actor=actor, agent_id=agent_id,
                        home=get_hermes_home() / 'agent-native')
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
        except (PlanningNotReady, PlanningConfigurationRequired) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (PermissionError, PlaneScopeError) as exc:
            raise HTTPException(status_code=403, detail='Planning inspection is no longer authorized') from exc
        except PlaneReadError as exc:
            raise HTTPException(status_code=503, detail='Plane planning data is unavailable') from exc


@model_router.get('/default')
def read_model_default(actor=Depends(owner_session)):
    from agent_native.model_settings import get_default
    with connect_closing(board='default') as conn:
        return get_default(conn)


@model_router.put('/default')
def set_model_default(body: ChangeModel, actor=Depends(owner_session)):
    from agent_native.model_settings import change_default
    with connect_closing(board='default') as conn:
        try:
            return change_default(conn, actor=actor, expected_revision=body.expected_revision,
                                  choice=body.model_dump(exclude={'expected_revision'}))
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


@model_router.get('/options')
async def model_options(refresh: bool = False, actor=Depends(owner_session)):
    from hermes_cli.web_routers.models import get_model_options
    return await get_model_options(refresh=refresh, include_unconfigured=False, explicit_only=True)


@model_router.get('/reasoning')
def reasoning_options(provider: str, model: str, actor=Depends(owner_session)):
    from agent_native.model_runtime import get_reasoning_options
    try:
        return get_reasoning_options(provider, model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put('/{agent_id}/model')
def set_agent_model(agent_id: str, body: ChangeModel, actor=Depends(owner_session)):
    from agent_native.model_settings import change_selection
    with connect_closing(board='default') as conn:
        try:
            change_selection(conn, actor=actor, agent_id=agent_id,
                             expected_revision=body.expected_revision,
                             choice=body.model_dump(exclude={'expected_revision'}))
            return identity.get_root(conn, actor=actor, agent_id=agent_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


class ProgressSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    verbosity: str = Field(strict=True, min_length=1, max_length=16)
    expected_revision: int = Field(strict=True, ge=1)


@router.get('/{agent_id}/progress-settings')
def progress_settings(agent_id: str, actor=Depends(owner_session)):
    from agent_native.progress import get_settings
    with connect_closing(board='default') as conn:
        try:
            return get_settings(conn, agent_id)
        except KeyError as exc:
            raise HTTPException(404, 'Agent not found') from exc


@router.put('/{agent_id}/progress-settings')
def update_progress_settings(agent_id: str, body: ProgressSettings, actor=Depends(owner_session)):
    from agent_native.progress import change_settings
    with connect_closing(board='default') as conn:
        try:
            return change_settings(conn, actor=actor, agent_id=agent_id, **body.model_dump())
        except KeyError as exc:
            raise HTTPException(404, 'Agent not found') from exc
        except identity.ConflictError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


class WorkFeedbackBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(strict=True, ge=1)
    text: str = Field(min_length=1, max_length=4000)


@router.get('/{agent_id}/feedback')
def read_work_feedback(agent_id: str, actor=Depends(owner_session)):
    from agent_native.feedback import recent
    with connect_closing(board='default') as conn:
        try:
            return recent(conn, agent_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc


@router.post('/{agent_id}/feedback', status_code=201)
def submit_work_feedback(agent_id: str, body: WorkFeedbackBody, actor=Depends(owner_session)):
    from agent_native.feedback import submit
    with connect_closing(board='default') as conn:
        try:
            return submit(conn, actor=actor, agent_id=agent_id, **body.model_dump())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


class WorkAnswerBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(strict=True,ge=1)
    answer: str = Field(min_length=1,max_length=4000)


@router.get('/{agent_id}/questions')
def read_work_questions(agent_id: str, actor=Depends(owner_session)):
    from agent_native.questions import recent
    with connect_closing(board='default') as conn:
        try:
            return recent(conn,agent_id)
        except KeyError as exc:
            raise HTTPException(status_code=404,detail='Agent not found') from exc


@router.post('/{agent_id}/questions/{question_id}/answer')
def answer_work_question(agent_id: str, question_id: str, body: WorkAnswerBody, actor=Depends(owner_session)):
    from agent_native.questions import answer
    with connect_closing(board='default') as conn:
        try:
            return answer(conn,actor=actor,agent_id=agent_id,question_id=question_id,**body.model_dump())
        except KeyError as exc:
            raise HTTPException(status_code=404,detail='Question not found') from exc
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409,detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422,detail=str(exc)) from exc


class CadenceSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(strict=True, ge=1)
    interval_seconds: int = Field(strict=True, ge=1, le=2592000)
    enabled: bool = Field(strict=True)


@router.post('/{agent_id}/cadence')
def configure_cadence(agent_id: str, body: CadenceSettings, actor=Depends(owner_session)):
    from agent_native.cadence import configure
    with connect_closing(board='default') as conn:
        try:
            return configure(conn,actor=actor,agent_id=agent_id,**body.model_dump())
        except KeyError as exc:
            raise HTTPException(status_code=404,detail='Agent not found') from exc
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409,detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422,detail=str(exc)) from exc


@router.get('/{agent_id}/attempts')
def list_attempts(agent_id: str, actor=Depends(owner_session)):
    with connect_closing(board='default') as conn:
        identity.get_root(conn,actor=actor,agent_id=agent_id)
        return [dict(zip(('id','state','summary','created_at','finished_at','session_id'),r)) for r in conn.execute(
            'SELECT id,state,summary,created_at,finished_at,session_id FROM agent_native_work_runs WHERE agent_id=? ORDER BY rowid DESC LIMIT 20',(agent_id,))]
