"""Verify a consistent local Plane snapshot in disposable Docker resources.

Operator-only: reads local deployment configuration, briefly pauses writers,
retains a private backup, and removes only resources created for this restore.
Never launches the restored application or dispatcher. No Docker images pulled.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)
    h = Path.home() / '.local/share/agent-native/plane'
    env_file = h / 'plane.env'
    shutil.copyfile(env_file, out / 'plane.env')
    for name in ['compose.yaml', 'images.lock.json']:
        shutil.copyfile(ROOT / 'ops/plane' / name, out / name)
    cfg = json.loads((h / 'builder-api.json').read_text())
    context = json.loads((h / 'planning-context.json').read_text())
    project_id = str(uuid.UUID(context['project_id']))
    compose = ['docker', 'compose', '-p', 'agent-native-plane', '--env-file', str(env_file), '-f', str(ROOT / 'ops/plane/compose.yaml')]
    # Resolve and check images before pausing any service.
    images = json.loads((ROOT / 'ops/plane/images.lock.json').read_text())
    image = lambda name: next(x['id'] for x in images if x['reference'].startswith(name))
    postgres, backend, minio = image('postgres:'), image('makeplane/plane-backend:'), image('minio/minio')
    alpine = json.loads(run(['docker', 'image', 'inspect', 'alpine:latest']))[0]['Id']
    for value in [postgres, backend, minio, alpine]: run(['docker', 'image', 'inspect', value])
    tag = 'an-restore-' + uuid.uuid4().hex[:10]
    db, store = tag + '-db', tag + '-s3'
    db_volume, files_volume = tag + '-pgdata', tag + '-uploads'
    key = 'verification/' + tag + '.txt'
    body = ('agent-native restore verification ' + tag).encode()
    report = {'resources': {'db': db, 'store': store, 'network': tag, 'volumes': [db_volume, files_volume]}, 'canary_key': key, 'checks': [], 'cleanup': []}
    def save(): (out / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    def source_s3(action):
        code = "import os,boto3; c=boto3.client('s3',endpoint_url=os.environ['AWS_S3_ENDPOINT_URL'],aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],region_name='us-east-1'); " + action
        run(['docker','exec','agent-native-plane-api-1','python','-c',code])
    containers, volumes = [], []
    network_created = False
    paused = False
    canary_created = False
    try:
        s = requests.Session(); s.headers['X-API-Key'] = cfg['api_key']
        api = cfg['base_url']+'/api/v1/workspaces/agent-native/projects/'+project_id+'/work-items/?per_page=100'
        response = s.get(api, timeout=20); response.raise_for_status()
        data = response.json()
        assert not data['next_page_results'], 'Capture all pages before snapshot; current verifier expects one project page'
        expected_ids = sorted(x['id'] for x in data['results'])
        report['expected_item_ids'] = expected_ids
        source_s3(f"c.put_object(Bucket='uploads',Key={key!r},Body={body!r})")
        canary_created = True
        paused = True
        run(compose + ['stop','proxy','api','worker','beat-worker','live','plane-minio'])
        with (out/'database.dump').open('wb') as target:
            subprocess.run(['docker','exec','agent-native-plane-plane-db-1','sh','-c','PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-privileges'], stdout=target, stderr=subprocess.PIPE, check=True)
        run(['docker','run','--rm','--pull=never','--network','none','--mount','type=volume,src=agent-native-plane_uploads,dst=/source,readonly','--mount',f'type=bind,src={out},dst=/backup',alpine,'sh','-c','cd /source && tar czf /backup/uploads.tgz .'])
        (out / 'uploads.tgz').chmod(0o600)
        report['checks'].append('database and uploads captured with application writers and object store stopped')
        run(compose + ['up','-d']); paused = False
        save()
        run(['docker','network','create','--internal',tag]); network_created = True
        for volume in [db_volume, files_volume]:
            run(['docker','volume','create',volume]); volumes.append(volume)
        run(['docker','run','--rm','--pull=never','--network','none','--mount',f'type=volume,src={files_volume},dst=/restore','--mount',f'type=bind,src={out},dst=/backup,readonly',alpine,'sh','-c','cd /restore && tar xzf /backup/uploads.tgz'])
        run(['docker','run','-d','--pull=never','--name',db,'--network','none','--mount',f'type=volume,src={db_volume},dst=/var/lib/postgresql/data','-e','POSTGRES_USER=plane','-e','POSTGRES_DB=plane','-e','POSTGRES_HOST_AUTH_METHOD=trust',postgres]); containers.append(db)
        deadline = time.monotonic()+45
        while True:
            ready=subprocess.run(['docker','exec',db,'pg_isready','-U','plane'],capture_output=True)
            if ready.returncode == 0: break
            if time.monotonic()>deadline: raise RuntimeError('Isolated restore database not ready')
            time.sleep(1)
        with (out/'database.dump').open('rb') as source:
            subprocess.run(['docker','exec','-i',db,'pg_restore','-U','plane','-d','plane','--no-owner','--no-privileges','--exit-on-error'],stdin=source,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
        query = "SELECT id FROM issues WHERE project_id = '"+project_id+"' AND deleted_at IS NULL ORDER BY id;"
        actual_ids=run(['docker','exec',db,'psql','-U','plane','-d','plane','-At','-c',query],text=True).splitlines()
        assert actual_ids == expected_ids, 'Restored project work-item IDs differ'
        report['checks'].append(f'all {len(actual_ids)} live project item IDs restored unchanged')
        values={line.split('=',1)[0]:line.split('=',1)[1] for line in env_file.read_text().splitlines() if '=' in line and not line.startswith('#')}
        restore_env=out/'restore-minio.env'
        restore_env.write_text('MINIO_ROOT_USER='+values['AWS_ACCESS_KEY_ID']+'\nMINIO_ROOT_PASSWORD='+values['AWS_SECRET_ACCESS_KEY']+'\n')
        run(['docker','run','-d','--pull=never','--name',store,'--network',tag,'--env-file',str(restore_env),'--mount',f'type=volume,src={files_volume},dst=/export',minio,'server','/export']); containers.append(store)
        code=f"""import os,time,boto3,hashlib
c=boto3.client('s3',endpoint_url='http://{store}:9000',aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],region_name='us-east-1')
for n in range(20):
 try:
  data=c.get_object(Bucket='uploads',Key={key!r})['Body'].read();break
 except Exception:
  if n==19:raise
  time.sleep(1)
assert hashlib.sha256(data).hexdigest()=={hashlib.sha256(body).hexdigest()!r}
"""
        run(['docker','run','--rm','--pull=never','--network',tag,'--env-file',str(env_file),'--entrypoint','python',backend,'-c',code])
        report['checks'].append('restored object bytes match canary SHA256 through the S3 API')
        for artifact in ['database.dump','uploads.tgz']:
            report.setdefault('sha256',{})[artifact]=hashlib.sha256((out/artifact).read_bytes()).hexdigest()
        # Reconnect through the original service, without starting any restored workers.
        deadline=time.monotonic()+45
        while True:
            try:
                response=s.get(api,timeout=3)
                if response.status_code==200:break
            except requests.RequestException:pass
            if time.monotonic()>deadline:raise RuntimeError('Original Plane API did not recover')
            time.sleep(1)
        assert sorted(x['id'] for x in response.json()['results'])==expected_ids
        report['checks'].append('original Builder API reconnects with the same project item IDs')
        report['result']='passed'
    except Exception as exc:
        # Do not include subprocess arguments or output, which may contain secrets.
        report['result'] = 'failed'
        report['error_type'] = type(exc).__name__
        raise
    finally:
        if paused:
            try: run(compose+['up','-d']); report['cleanup'].append('original services restarted')
            except Exception: report['cleanup'].append('ERROR: restart original Plane services manually')
        for container in reversed(containers):
            try:run(['docker','rm','-f',container]);report['cleanup'].append('removed '+container)
            except Exception:report['cleanup'].append('ERROR removing '+container)
        for volume in volumes:
            try:run(['docker','volume','rm',volume]);report['cleanup'].append('removed '+volume)
            except Exception:report['cleanup'].append('ERROR removing '+volume)
        if network_created:
            try:run(['docker','network','rm',tag]);report['cleanup'].append('removed '+tag)
            except Exception:report['cleanup'].append('ERROR removing '+tag)
        if canary_created:
            try:source_s3(f"c.delete_object(Bucket='uploads',Key={key!r})");report['cleanup'].append('removed source verification canary')
            except Exception:report['cleanup'].append('ERROR removing source canary; exact key recorded above')
        save()
        print(json.dumps(report,indent=2))
    if any(x.startswith('ERROR') for x in report['cleanup']):raise SystemExit('Cleanup incomplete; see private report')


if __name__=='__main__':main()
