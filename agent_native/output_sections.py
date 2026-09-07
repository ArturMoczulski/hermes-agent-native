"""Read-only Outputs-section proposals from durable, host-attributed evidence.

The supported Plane API ignores If-Match. Never PATCH a read/merged description:
that would still race human edits. Pending proposals are not delivery receipts.
"""


def pending_sections(conn, run_id):
    keys = ('source_id', 'item_id', 'summary', 'text', 'comment_status', 'link_url', 'link_label')
    rows = conn.execute(
        "SELECT source_id,item_id,summary,text,status,link_url,link_label "
        "FROM agent_native_progress WHERE run_id=? "
        "AND (source_id LIKE 'output:%' OR source_id LIKE 'result:%' OR source_id LIKE 'terminal:%') "
        "ORDER BY created_at,source_id", (run_id,)).fetchall()
    grouped = {}
    for row in rows:
        entry = dict(zip(keys, row))
        grouped.setdefault(entry['item_id'], []).append(entry)
    sections = []
    for item_id, entries in grouped.items():
        if not any(e['source_id'].startswith(('output:', 'result:')) for e in entries):
            continue
        text = ['Outputs', 'Prepared references — not synchronized to the Plane description.']
        if not any(e['source_id'].startswith('output:') for e in entries):
            text.append('No saved files are listed in this section.')
        for entry in entries:
            text.append(entry['text'])
            if entry['link_url']:
                text.append(entry['link_label'] + ': ' + entry['link_url'])
        sections.append({'item_id': item_id, 'status': 'pending',
                         'reason': 'conditional_write_unavailable',
                         'entries': entries, 'text': '\n\n'.join(text)})
    return sections
