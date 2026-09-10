"""Owner dashboard operations for agent-native identity, work and inspection.

Only the existing dashboard owner session is accepted. Scoped automation tokens
cannot promote themselves to OWNER through request data or general middleware.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from agent_native import identity
from hermes_cli.kanban_db_connect import connect_closing


def owner_session(request: Request):
    from hermes_cli.web_server import _require_token
    _require_token(request)
    agent_id = request.path_params.get('agent_id')
    replacement_retry = request.url.path.endswith('/replace')
    if agent_id and request.method not in ('GET', 'HEAD', 'DELETE') and not replacement_retry:
        with connect_closing(board='default') as conn:
            try:
                identity.require_active(conn, agent_id)
            except identity.ConflictError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
    return identity.OWNER


router = APIRouter(prefix='/api/agent-native/agents')
preview_router = APIRouter(prefix='/agent-preview')
model_router = APIRouter(prefix='/api/agent-native/models')
first_builder_router = APIRouter(prefix='/api/agent-native/first-builder')


@first_builder_router.get('')
def read_first_builder(actor=Depends(owner_session)):
    from agent_native import first_builder
    with connect_closing(board='default') as conn:
        try:
            registration = first_builder.read(conn, actor=actor)
            return {'registration': registration,
                    'agent': identity.get_root(conn, actor=actor, agent_id=registration['agent_id'])}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='First Builder is not prepared') from exc


@first_builder_router.post('/prepare', status_code=201)
def prepare_first_builder(actor=Depends(owner_session)):
    from pathlib import Path
    from agent_native import first_builder
    from hermes_constants import get_hermes_home
    repository = Path(__file__).resolve().parents[2]
    with connect_closing(board='default') as conn:
        try:
            agent = first_builder.prepare(
                conn, actor=actor, home=get_hermes_home() / 'agent-native',
                repository=repository, instruction_source=repository / 'first-builder',
            )
            return {'registration': first_builder.read(conn, actor=actor), 'agent': agent}
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


class WorkLimits(BaseModel):
    model_config = ConfigDict(extra='forbid')
    timeout_seconds: int = Field(strict=True, ge=1, le=3600)
    max_iterations: int = Field(strict=True, ge=1, le=100)


class FirstBuilderAction(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    agent_id: str = Field(min_length=1, max_length=128)


class FirstBuilderTest(FirstBuilderAction):
    evidence: str = Field(min_length=1, max_length=4000)


@first_builder_router.post('/confirm-test')
def confirm_first_builder_test(body: FirstBuilderTest, actor=Depends(owner_session)):
    from agent_native import first_builder
    with connect_closing(board='default') as conn:
        try:
            first_builder.confirm_owner_test(conn, actor=actor, **body.model_dump())
            registration = first_builder.read(conn, actor=actor)
            return {'registration': registration,
                    'agent': identity.get_root(conn, actor=actor, agent_id=registration['agent_id'])}
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@first_builder_router.post('/launch')
def launch_first_builder(body: FirstBuilderAction, actor=Depends(owner_session)):
    from agent_native import first_builder
    with connect_closing(board='default') as conn:
        try:
            first_builder.launch(conn, actor=actor, **body.model_dump())
            registration = first_builder.read(conn, actor=actor)
            return {'registration': registration,
                    'agent': identity.get_root(conn, actor=actor, agent_id=registration['agent_id'])}
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


class ProjectWorkspaceGrant(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_revision: int = Field(strict=True, ge=1)
    root: str = Field(min_length=1, max_length=4096)


@router.post('/{agent_id}/workspace', status_code=201)
def grant_project_workspace(agent_id: str, body: ProjectWorkspaceGrant, actor=Depends(owner_session)):
    from agent_native import project_workspace
    with connect_closing(board='default') as conn:
        try:
            return project_workspace.grant(conn, actor=actor, agent_id=agent_id, **body.model_dump())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get('/{agent_id}/preview/')
@router.get('/{agent_id}/preview/{asset_path:path}')
def read_project_preview(agent_id: str, asset_path: str = 'index.html', actor=Depends(owner_session)):
    from fastapi.responses import FileResponse
    from agent_native import project_preview
    with connect_closing(board='default') as conn:
        try:
            identity.get_root(conn, actor=actor, agent_id=agent_id)
            return FileResponse(project_preview.asset(conn, agent_id, asset_path))
        except (KeyError, PermissionError, ValueError) as exc:
            raise HTTPException(status_code=404, detail='Preview asset not found') from exc


@router.post('/{agent_id}/preview-launch')
def create_project_preview_launch(request: Request, agent_id: str, actor=Depends(owner_session)):
    from agent_native import project_preview
    with connect_closing(board='default') as conn:
        try:
            identity.get_root(conn, actor=actor, agent_id=agent_id)
            project_preview.read(conn, agent_id)
            ticket = project_preview.mint_launch(agent_id)
            host = request.url.hostname
            if host not in ('127.0.0.1', 'localhost'):
                raise PermissionError('A separate configured preview origin is required')
            preview_host = 'localhost' if host == '127.0.0.1' else '127.0.0.1'
            port = f':{request.url.port}' if request.url.port else ''
            return {'url': f'{request.url.scheme}://{preview_host}{port}/agent-preview/{agent_id}/launch?ticket={ticket}'}
        except (KeyError, PermissionError) as exc:
            raise HTTPException(status_code=404, detail='Project preview not found') from exc


@preview_router.get('/{agent_id}/launch')
def exchange_project_preview_launch(request: Request, agent_id: str, ticket: str):
    from fastapi.responses import RedirectResponse
    from agent_native import project_preview
    try:
        session = project_preview.exchange_launch(agent_id, ticket)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail='Preview launch is invalid or expired') from exc
    port = f':{request.url.port}' if request.url.port else ''
    clean_url = f'{request.url.scheme}://{request.url.hostname}{port}/agent-preview/{agent_id}/'
    response = RedirectResponse(clean_url, status_code=303)
    response.set_cookie('agent_preview_session', session, max_age=3600, httponly=True,
                        samesite='lax', path=f'/agent-preview/{agent_id}')
    return response


@preview_router.get('/{agent_id}/')
@preview_router.get('/{agent_id}/{asset_path:path}')
def read_launched_project_preview(request: Request, agent_id: str, asset_path: str = 'index.html'):
    from fastapi.responses import FileResponse
    from agent_native import project_preview
    try:
        project_preview.authorize_session(agent_id, request.cookies.get('agent_preview_session', ''))
        with connect_closing(board='default') as conn:
            response = FileResponse(project_preview.asset(conn, agent_id, asset_path))
            response.headers['Referrer-Policy'] = 'no-referrer'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
            return response
    except (KeyError, PermissionError, ValueError) as exc:
        raise HTTPException(status_code=404, detail='Preview asset not found') from exc


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
    autonomy_level: int = Field(default=3, strict=True, ge=1, le=5)
    parent_id: str | None = Field(default=None, min_length=1, max_length=128)


class ReplaceAgent(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=20000)
    reason: str = Field(min_length=1, max_length=4000)
    handoff: str = Field(min_length=1, max_length=8000)


class ChangePurpose(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_revision: int = Field(strict=True, ge=1)
    purpose: str = Field(min_length=1, max_length=20000)


@router.get('')
def list_agents(lifecycle: Literal['active', 'retired'] = 'active', actor=Depends(owner_session)):
    with connect_closing(board='default') as conn:
        return identity.list_roots(conn, actor=actor, lifecycle=lifecycle)


@router.post('', status_code=201)
def create_agent(body: CreateAgent, actor=Depends(owner_session)):
    with connect_closing(board='default') as conn:
        try:
            return identity.create_root(conn, actor=actor, **body.model_dump(exclude_unset=True))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Parent agent not found') from exc
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post('/{agent_id}/replace', status_code=201)
def replace_agent(agent_id: str, body: ReplaceAgent, actor=Depends(owner_session)):
    from agent_native.replacement import replace
    with connect_closing(board='default') as conn:
        try:
            return replace(
                conn, actor=actor, predecessor_id=agent_id,
                **body.model_dump(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
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


@router.patch('/{agent_id}/purpose')
def change_agent_purpose(agent_id: str, body: ChangePurpose, actor=Depends(owner_session)):
    with connect_closing(board='default') as conn:
        try:
            return identity.revise_soul(
                conn, actor=actor, agent_id=agent_id,
                expected_revision=body.expected_revision, purpose=body.purpose,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


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


class RetryWork(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(strict=True, ge=1)
    expected_run_id: str = Field(min_length=1, max_length=128)


class ResultDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: str = Field(min_length=1, max_length=128)
    decision: str = Field(min_length=1, max_length=32, strict=True)
    expected_criteria_revision: str = Field(min_length=1, max_length=128, strict=True)
    note: str | None = Field(default=None, max_length=4000)


@router.post('/{agent_id}/results/{result_id}/decision')
def decide_result(agent_id: str, result_id: str, body: ResultDecision, actor=Depends(owner_session)):
    from agent_native.acceptance import decide
    with connect_closing(board='default') as conn:
        try:
            decide(conn, actor=actor, agent_id=agent_id, result_id=result_id, **body.model_dump())
            return identity.get_root(conn, actor=actor, agent_id=agent_id)
        except KeyError as exc:
            raise HTTPException(404, 'Result not found') from exc
        except identity.ConflictError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


@router.post('/{agent_id}/work/retry')
def retry_work(agent_id: str, body: RetryWork, actor=Depends(owner_session)):
    from agent_native.work_retry import retry_failed
    with connect_closing(board='default') as conn:
        try:
            recovery = retry_failed(conn, actor=actor, agent_id=agent_id, **body.model_dump())
            return {'recovery_run_id': recovery['id'],
                    'agent': identity.get_root(conn, actor=actor, agent_id=agent_id)}
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
            subtree_pause = request_pause(conn, actor=actor, agent_id=agent_id)
            agent = identity.get_root(conn, actor=actor, agent_id=agent_id)
            agent['subtree_pause'] = subtree_pause
            return agent
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
        except identity.ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/{agent_id}/work/resume')
def resume_work(agent_id: str, actor=Depends(owner_session)):
    from agent_native.work_state import request_resume
    with connect_closing(board='default') as conn:
        try:
            subtree_resume = request_resume(conn, actor=actor, agent_id=agent_id)
            agent = identity.get_root(conn, actor=actor, agent_id=agent_id)
            agent['subtree_resume'] = subtree_resume
            return agent
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
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


@router.get('/{agent_id}/media/{artifact_id}')
def read_media(agent_id: str, artifact_id: str, download: bool = False,
               actor=Depends(owner_session)):
    from fastapi.responses import FileResponse
    from hermes_constants import get_hermes_home
    from agent_native.agent_home import paths
    from agent_native.media_store import read
    with connect_closing(board='default') as conn:
        try:
            identity.get_root(conn, actor=actor, agent_id=agent_id)
            workspace = paths(get_hermes_home() / 'agent-native' / 'agents', agent_id).legacy_workspace
            metadata, path = read(conn, agent_id, artifact_id, workspace=workspace)
            return FileResponse(path, media_type=metadata['mime_type'], filename=metadata['filename'],
                                content_disposition_type='attachment' if download else 'inline',
                                headers={'Cache-Control':'private, immutable'})
        except (KeyError, LookupError) as exc:
            raise HTTPException(status_code=404, detail='Media output not found') from exc
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=409, detail='Media output could not be verified') from exc


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


class AutonomySettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    level: int = Field(strict=True, ge=1, le=5)
    require_owner_review: bool = Field(strict=True)
    expected_revision: int = Field(strict=True, ge=1)

class AssignmentReviewSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    run_id: str = Field(min_length=1,max_length=128)
    required: bool = Field(strict=True)
    expected_revision: int = Field(strict=True,ge=0)

@router.put('/{agent_id}/assignment-review')
def update_assignment_review(agent_id:str,body:AssignmentReviewSettings,actor=Depends(owner_session)):
    from agent_native.assignment_review import configure_current
    with connect_closing(board='default') as conn:
        try:
            configure_current(conn,actor=actor,agent_id=agent_id,**body.model_dump())
            return identity.get_root(conn,actor=actor,agent_id=agent_id)
        except KeyError as exc: raise HTTPException(404,'Agent or run not found') from exc
        except identity.ConflictError as exc: raise HTTPException(409,str(exc)) from exc
        except ValueError as exc: raise HTTPException(422,str(exc)) from exc


@router.get('/{agent_id}/autonomy')
def autonomy_settings(agent_id: str, actor=Depends(owner_session)):
    from agent_native.autonomy import get_settings
    with connect_closing(board='default') as conn:
        try:
            return get_settings(conn, agent_id)
        except KeyError as exc:
            raise HTTPException(404, 'Agent not found') from exc


@router.put('/{agent_id}/autonomy')
def update_autonomy_settings(agent_id: str, body: AutonomySettings, actor=Depends(owner_session)):
    from agent_native.autonomy import change_settings
    with connect_closing(board='default') as conn:
        try:
            change_settings(conn, actor=actor, agent_id=agent_id, **body.model_dump())
            return identity.get_root(conn, actor=actor, agent_id=agent_id)
        except KeyError as exc:
            raise HTTPException(404, 'Agent not found') from exc
        except identity.ConflictError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


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
    intent: Literal['feedback', 'revision_request'] = 'feedback'
    output_id: str | None = None
    output_version: int | None = Field(default=None, ge=1)


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


class ProgressConcernSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    failure_threshold: int = Field(strict=True, ge=2, le=10)


class ResumeProgressConcern(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(strict=True, ge=1)
    request_id: str = Field(min_length=1, max_length=128)


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


@router.post('/{agent_id}/progress-concerns/settings')
def configure_progress_concerns(agent_id: str, body: ProgressConcernSettings,
                                actor=Depends(owner_session)):
    from agent_native.progress_concerns import configure
    with connect_closing(board='default') as conn:
        try:
            return configure(conn,actor=actor,agent_id=agent_id,**body.model_dump())
        except KeyError as exc:
            raise HTTPException(status_code=404,detail='Agent not found') from exc
        except ValueError as exc:
            raise HTTPException(status_code=422,detail=str(exc)) from exc


@router.post('/{agent_id}/progress-concerns/{concern_id}/resume')
def resume_progress_concern(agent_id: str, concern_id: str,
                            body: ResumeProgressConcern, actor=Depends(owner_session)):
    from agent_native.progress_concerns import resume
    with connect_closing(board='default') as conn:
        try:
            resume(conn,actor=actor,agent_id=agent_id,concern_id=concern_id,
                   **body.model_dump())
            return identity.get_root(conn,actor=actor,agent_id=agent_id)
        except KeyError as exc:
            raise HTTPException(status_code=404,detail='Progress concern not found') from exc
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


@router.delete('/{agent_id}')
def remove_agent(agent_id: str, actor=Depends(owner_session)):
    with connect_closing(board='default') as conn:
        try:
            return identity.remove_root(conn, actor=actor, agent_id=agent_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='Agent not found') from exc
