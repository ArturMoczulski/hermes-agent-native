"""Admission classification; uncertain notices remain unknown and are never resent."""
from agent_native.identity import OWNER, ConflictError
from agent_native.plane_write_journal import MutationJournal
from agent_native.plane_writes import _paragraph


def unresolved_terminal_notices(conn, agent_id):
    """Return narrowly proven terminal-status notices, rejecting other uncertainty.

    A lost informational terminal comment does not make completed task effects
    uncertain. This does not restart failed work: owner retry still gates that.
    All protected records remain unchanged for later evidence reconciliation.
    """
    journal = MutationJournal(conn)
    allowed = []
    rows = conn.execute('SELECT operation_id,source_id,run_id,item_id,summary,text,status,link_url,link_label '
                        "FROM agent_native_progress WHERE agent_id=? AND status IN ('pending','unknown')",(agent_id,)).fetchall()
    for opid,source,run_id,item,summary,text,status,url,label in rows:
        try:
            run = conn.execute('SELECT state,soul_revision,binding_id FROM agent_native_work_runs WHERE id=? AND agent_id=?',(run_id,agent_id)).fetchone()
            terminal_state = run[0] if run else None
            expected_summary = 'Attempt '+str(terminal_state)
            expected_text = (f'Agent: {agent_id}\nAttempt: {run_id}\nWork item: {item}\n{expected_summary}\n'
                'This is the bounded attempt status, not acceptance of the assignment or completion of the agent purpose. Review saved evidence and any unresolved delivery before continuing.')
            if (source != 'terminal:'+run_id or not run or terminal_state not in ('failed','limit_reached')
                    or summary != expected_summary or text != expected_text or url is not None or label is not None):
                raise ValueError
            if status == 'pending' and terminal_state == 'limit_reached':
                if (conn.execute('SELECT 1 FROM agent_native_plane_mutations WHERE operation_id=?',(opid,)).fetchone()
                        or conn.execute('SELECT 1 FROM agent_native_work_effects WHERE operation_id=?',(opid,)).fetchone()):
                    raise ValueError
                allowed.append(opid)
                continue
            if status != 'unknown':
                raise ValueError
            receipt = journal.get(opid,actor=OWNER)
            saved = journal.preparation(opid,actor=OWNER)
            expected_payload = {'comment_html':_paragraph(f'Agent {agent_id} (framework planning)')+_paragraph(text),
                                'access':'INTERNAL','external_source':'agent-native','external_id':opid}
            if (receipt['agent_id'] != agent_id or receipt['operation'] != 'comment.create'
                    or receipt['status'] != 'unknown' or receipt['soul_revision'] != run[1]
                    or receipt['binding_id'] != run[2] or not saved['attempted']
                    or saved['arguments'] != {'item_id':item,'text':text}
                    or saved['prepared'] != {'method':'POST','suffix':f'work-items/{item}/comments/',
                        'payload':expected_payload,'expected':201,'kind':'comment','resource_id':item}
                    or conn.execute('SELECT 1 FROM agent_native_work_effects WHERE operation_id=?',(opid,)).fetchone()):
                raise ValueError
            allowed.append(opid)
        except (KeyError, ValueError, TypeError):
            raise ConflictError('Resolve pending or unknown Plane delivery before continuing work') from None
    mutations = conn.execute("SELECT operation_id FROM agent_native_plane_mutations WHERE agent_id=? AND status IN ('pending','unknown')",(agent_id,)).fetchall()
    if any(opid not in allowed for (opid,) in mutations):
        raise ConflictError('Resolve pending or unknown Plane delivery before continuing work')
    return allowed


def record_notices(conn, run_id, notices):
    from agent_native.work_state import event
    for opid in notices:
        event(conn,run_id,'work.notification_unresolved',
              'Prior terminal-status comment remains unconfirmed: '+opid+'. It will not be resent; task effects are settled.')
