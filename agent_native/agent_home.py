"""Authoritative paths for one operator-managed agent home."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentHome:
    home: Path
    protected: Path
    memory: Path
    skills: Path
    legacy_workspace: Path
    practices: Path
    project: Path
    outputs: Path
    runtime: Path


def paths(storage_root, agent_id):
    home = Path(storage_root).resolve() / agent_id
    return AgentHome(
        home=home,
        protected=home / 'profile',
        memory=home / 'profile' / 'memories',
        skills=home / 'profile' / 'skills',
        legacy_workspace=home / 'workspace',
        practices=home / 'practices',
        project=home / 'projects' / 'main',
        outputs=home / 'outputs',
        runtime=home / 'runtime' / 'attempts',
    )


def ensure_mutable_areas(layout):
    """Create missing non-protected areas without moving existing agent data."""
    for directory in (layout.practices, layout.project, layout.outputs, layout.runtime):
        current = layout.home
        for part in directory.relative_to(layout.home).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(f'Unsafe agent-home symlink: {current}')
            current.mkdir(mode=0o700, exist_ok=True)


def public_layout(layout):
    return {
        'home': str(layout.home),
        'profile': str(layout.protected),
        'workspace': str(layout.legacy_workspace),
        'memory': str(layout.memory),
        'skills': str(layout.skills),
        'practices': str(layout.practices),
        'project': str(layout.project),
        'outputs': str(layout.outputs),
        'runtime': str(layout.runtime),
    }
