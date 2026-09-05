"""One-shot computer actions must resolve without an invisible modal."""
import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from hermes_cli.cli_modal_mixin import CLIModalMixin


@pytest.mark.parametrize('mode, expected', [('deny', 'deny'), ('approve', 'approve_once'), ('invalid', 'deny')])
def test_single_query_computer_approval_uses_explicit_policy(mode, expected):
    cli = CLIModalMixin()
    cli._single_query_mode = True
    cli._approval_lock = Mock()
    cli._approval_lock.__enter__ = Mock(side_effect=AssertionError('one-shot entered interactive modal'))
    cli._approval_lock.__exit__ = Mock(return_value=False)
    Path(os.environ['HERMES_HOME'], 'config.yaml').write_text(json.dumps({'approvals': {'single_query_mode': mode}}))
    assert cli._computer_use_approval_callback('key', {'keys': 'cmd+s', 'app': 'TextEdit'}, 'save fixture') == expected
