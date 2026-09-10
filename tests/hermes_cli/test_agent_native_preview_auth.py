"""Preview launch authority is temporary, single-use and agent-scoped."""

import pytest

from agent_native import project_preview


def test_launch_ticket_becomes_agent_scoped_preview_session():
    ticket = project_preview.mint_launch('agent-one')
    session = project_preview.exchange_launch('agent-one', ticket)
    project_preview.authorize_session('agent-one', session)

    with pytest.raises(PermissionError):
        project_preview.exchange_launch('agent-one', ticket)
    with pytest.raises(PermissionError):
        project_preview.authorize_session('agent-two', session)


def test_cross_agent_exchange_consumes_stolen_launch_ticket():
    ticket = project_preview.mint_launch('agent-one')
    with pytest.raises(PermissionError):
        project_preview.exchange_launch('agent-two', ticket)
    with pytest.raises(PermissionError):
        project_preview.exchange_launch('agent-one', ticket)
