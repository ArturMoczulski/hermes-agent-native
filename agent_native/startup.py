"""Durable, host-only root setup; readiness never implies model admission.

Each external phase is serialized with the existing local OS operation lock.
An attempted phase survives process loss. Recovery may inspect its original
resources but may not send another uncertain create. No credentials or host paths
are returned in status. Files, database and configuration stay outside workers.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat

from agent_native.identity import OWNER, ConflictError, _now, _require_owner, get_root
from agent_native.plane_operation_lock import operation_lock
from agent_native.provisioning import provision_root
from hermes_cli.kanban_db_connect import write_txn

_FIELDS = ('activation_id', 'status', 'phase', 'attempted', 'files_ready', 'plane_origin',
           'plane_user_id', 'workspace_slug', 'workspace_id', 'project_id',
           'discovery_item_id', 'message', 'updated_at')


def _row(conn, agent_id):
    result = conn.execute('SELECT ' + ', '.join(_FIELDS) + ' FROM agent_native_setup WHERE agent_id = ?',
                          (agent_id,)).fetchone()
    return dict(zip(_FIELDS, result)) if result else None


def read_setup(conn, agent_id):
    row = _row(conn, agent_id)
    if row is None:
        return None
    result = {k: v for k, v in row.items() if k not in ('attempted', 'plane_user_id')}
    result['files_ready'] = bool(result['files_ready'])
    result['events'] = [dict(zip(('sequence', 'status', 'phase', 'message', 'created_at'), event))
                        for event in conn.execute(
                            'SELECT sequence, status, phase, message, created_at FROM agent_native_setup_events '
                            'WHERE activation_id = ? ORDER BY sequence DESC LIMIT 30', (row['activation_id'],))][::-1]
    return result


def _event(conn, agent_id):
    conn.execute('INSERT INTO agent_native_setup_events '
                 '(activation_id, status, phase, message, created_at) '
                 'SELECT activation_id, status, phase, message, updated_at '
                 'FROM agent_native_setup WHERE agent_id = ?', (agent_id,))


def queue_setup(conn, agent_id):
    """Part of the creation transaction only; never backfill on a read."""
    conn.execute('INSERT INTO agent_native_setup '
                 '(activation_id, agent_id, status, phase, message, updated_at) '
                 "SELECT id, agent_id, 'queued', 'files', 'Waiting to prepare agent workspace.', ? "
                 'FROM agent_native_initial_activations WHERE agent_id = ?', (_now(), agent_id))
    _event(conn, agent_id)


def _update(conn, agent_id, **changes):
    if not changes or not set(changes) <= set(_FIELDS) - {'activation_id', 'updated_at'}:
        raise ValueError('Invalid setup transition')
    changes['updated_at'] = _now()
    with write_txn(conn):
        # Owner revision is terminal for this intent. A late HTTP receipt can
        # retain resource IDs, but can never restore readiness for the old soul.
        current = _row(conn, agent_id)
        if current and current['status'] == 'superseded':
            changes['status'] = 'superseded'
            changes['message'] = 'Purpose changed. This setup request cannot start work.'
        conn.execute('UPDATE agent_native_setup SET ' + ', '.join(f'{key} = ?' for key in changes)
                     + ' WHERE agent_id = ?', (*changes.values(), agent_id))
        _event(conn, agent_id)


def retry_setup(conn, *, actor, agent_id):
    _require_owner(actor)
    root = get_root(conn, actor=actor, agent_id=agent_id)
    if root['setup'] is None:
        raise ConflictError('No setup request exists for this agent')
    with operation_lock(conn, root['startup']['id']):
        if not _current(conn, agent_id):
            raise ConflictError('The purpose changed; this setup request is superseded')
        state = _row(conn, agent_id)
        if state['status'] in ('blocked', 'failed', 'unresolved'):
            _update(conn, agent_id, status='queued', message='Setup retry requested; existing resources will be checked.')
    return get_root(conn, actor=actor, agent_id=agent_id)


def _current(conn, agent_id):
    root = get_root(conn, actor=OWNER, agent_id=agent_id)
    if root['startup'] is None or root['startup']['soul_revision'] != root['soul_revision']:
        _update(conn, agent_id, status='superseded', message='Purpose changed. This setup request cannot start work.')
        return False
    return True


class SetupInterrupted(Exception):
    pass


class ConfigurationRequired(ValueError):
    pass


def load_plane_configuration(home):
    """Read an explicitly configured protected host account, never ambient secrets."""
    path = Path(home) / 'plane-setup.json'
    try:
        directory = path.parent.lstat()
        if (not stat.S_ISDIR(directory.st_mode) or directory.st_mode & 0o077
                or directory.st_uid != os.geteuid()):
            raise ValueError('Private directory required')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd) as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
                    or info.st_uid != os.geteuid() or info.st_nlink != 1 or info.st_size > 16384):
                raise ValueError('Private file required')
            config = json.load(stream)
        if (not isinstance(config, dict)
                or set(config) != {'base_url', 'email', 'password', 'api_key', 'expected_user_id'}
                or any(not isinstance(v, str) or not v.strip() for v in config.values())):
            raise ValueError('Invalid config')
        from agent_native.plane_reads import _origin
        from agent_native.plane_access import _uuid
        config['base_url'] = _origin(config['base_url'])
        config['expected_user_id'] = _uuid(config['expected_user_id'])
        return config
    except (OSError, ValueError, TypeError):
        raise ConfigurationRequired('Plane setup required. Configure the protected host connection, then retry setup.') from None


@contextmanager
def _open_configured(config):
    from agent_native.plane_setup import PlaneSetup
    with PlaneSetup(**config) as plane:
        yield plane


def prepare(conn, *, actor, agent_id, home, open_plane=None, plane_identity=None, stopped=lambda: False):
    """Process one intent; dependencies may be supplied only by trusted host code."""
    _require_owner(actor)
    root = get_root(conn, actor=actor, agent_id=agent_id)
    if root['setup'] is None:
        return
    with operation_lock(conn, root['startup']['id']):
        if not _current(conn, agent_id) or _row(conn, agent_id)['status'] not in ('queued', 'preparing'):
            return
        _update(conn, agent_id, status='preparing', message='Preparing private workspace and planning home.')
        try:
            provision_root(conn, actor=actor, agent_id=agent_id, storage_root=Path(home) / 'agents')
            if _row(conn, agent_id)['phase'] == 'files':
                _update(conn, agent_id, files_ready=1, phase='workspace', attempted=0,
                        message='Private files ready. Preparing Plane workspace.')
            if open_plane is None:
                config = load_plane_configuration(home)
                plane_identity = (config['base_url'], config['expected_user_id'])
                open_plane = lambda: _open_configured(config)
            origin, user_id = plane_identity
            state = _row(conn, agent_id)
            if state['plane_origin'] is not None and (state['plane_origin'], state['plane_user_id']) != plane_identity:
                raise ConfigurationRequired('Plane connection changed. Restore the original host connection to reconcile setup.')
            with open_plane() as plane:
                if state['plane_origin'] is None:
                    _update(conn, agent_id, plane_origin=origin, plane_user_id=user_id,
                            message='Authenticated Plane connection recorded for this setup request.')
                write_count = [0]
                def before_write():
                    if stopped() or not _current(conn, agent_id):
                        raise SetupInterrupted()
                    write_count[0] += 1
                plane.before_write = before_write
                _planning(conn, root, plane, stopped, write_count)
        except SetupInterrupted:
            return  # Retain the original checkpoint; recovery inspects an attempted phase.
        except ConfigurationRequired as exc:
            _update(conn, agent_id, status='blocked', message=str(exc))
        except Exception:
            # Network failures are classified at the phase boundary below. Never
            # serialize arbitrary exceptions (credentials, URLs or tool text).
            state = _row(conn, agent_id)
            _update(conn, agent_id, status='unresolved' if state['attempted'] else 'failed',
                    message='Setup could not be completed. Check the host connection and retry; uncertain creates will only be inspected.')


def _planning(conn, root, plane, stopped, write_count):
    from agent_native.plane_setup import SetupError
    agent_id = root['id']
    phases = ('workspace', 'project', 'discovery')
    for phase in phases:
        if stopped() or not _current(conn, agent_id):
            return
        state = _row(conn, agent_id)
        completed = phases.index(phase) < (phases.index(state['phase']) if state['phase'] in phases else 3)
        previous_attempt = bool(state['attempted'])
        allow_create = not completed and not previous_attempt
        if not completed:
            _update(conn, agent_id, attempted=1, message=f'Checking Plane {phase}.')
        writes_before_phase = write_count[0]
        try:
            if phase == 'workspace':
                result = plane.ensure_workspace(agent_id=agent_id, name=root['name'], allow_create=allow_create)
                fields = {'workspace_id': result['id'], 'workspace_slug': result['slug']}
                next_phase = 'project'
            elif phase == 'project':
                result = plane.ensure_project(agent_id=agent_id, workspace_slug=state['workspace_slug'], allow_create=allow_create)
                fields = {'project_id': result['id']}
                next_phase = 'discovery'
            else:
                result = plane.ensure_discovery(agent_id=agent_id, activation_id=root['startup']['id'],
                                                purpose=root['purpose'], workspace_slug=state['workspace_slug'],
                                                project_id=state['project_id'], allow_create=allow_create)
                fields = {'discovery_item_id': result['id']}
                next_phase = 'ready'
            if completed:
                if any(state[key] != value for key, value in fields.items()):
                    raise SetupError('Previously confirmed Plane resources changed. Manual reconciliation is required.', uncertain=True)
            else:
                _update(conn, agent_id, **fields, phase=next_phase, attempted=0,
                        message=f'Plane {phase} confirmed.')
        except SetupInterrupted:
            if not completed and not previous_attempt and write_count[0] == writes_before_phase:
                _update(conn, agent_id, attempted=0)
            raise
        except SetupError as exc:
            uncertain = previous_attempt or exc.uncertain or completed
            _update(conn, agent_id, status='unresolved' if uncertain else 'failed',
                    attempted=int(previous_attempt or (exc.uncertain and not completed)), message=str(exc))
            return
    if not stopped() and _current(conn, agent_id):
        _update(conn, agent_id, status='ready', message='Private workspace, Plane project and first discovery task are ready. Execution has not started.')
