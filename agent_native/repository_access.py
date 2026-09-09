"""Resolve the one explicit repository grant applicable to a managed agent."""


def active_repository(conn, agent_id):
    from agent_native.first_builder import active_repository as first_builder_repository
    from agent_native.project_workspace import active_repository as project_repository
    try:
        return first_builder_repository(conn, agent_id)
    except PermissionError:
        return project_repository(conn, agent_id)
