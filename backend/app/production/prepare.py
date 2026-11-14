"""Owner-only new secret files/Caddy config; no database or remote operation."""
import json
import os
from pathlib import Path
import secrets
from app.production.check import ROOT,caddy
from app.production.config import public_origin,SafeParser


def prepare(origin,directory):
    public_origin(origin)
    if os.name!='posix' or os.geteuid()!=0:raise ValueError('Linux root required for secret file ownership')
    if directory!=ROOT/'deploy/private' or directory.exists() or directory.is_symlink():raise ValueError('New fixed private directory required')
    # Never overwrite or remove a partial preparation. Stop on any failure.
    directory.mkdir(mode=0o700)
    values={name:secrets.token_urlsafe(48) for name in ('admin_db_password','runtime_db_password','migrator_db_password')}
    values['throttle_key']=secrets.token_hex(32)
    for name,value in values.items():
        path=directory/name
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o400)
        with os.fdopen(fd,'w',encoding='ascii') as stream:stream.write(value+'\n')
        os.chown(path,10001,10001)
    template=json.loads((ROOT/'deploy/caddy.template.json').read_text())
    with (directory/'caddy.json').open('x',encoding='utf-8') as stream:json.dump(caddy(origin,template),stream,indent=2)
    (directory/'caddy.json').chmod(0o444)


def main():
    p=SafeParser(description=__doc__);p.add_argument('--origin',required=True)
    p.add_argument('--confirm-new-secrets',action='store_true',required=True);args=p.parse_args()
    try:prepare(args.origin,ROOT/'deploy/private')
    except Exception:p.exit(1,'Preparation failed; preserve any partial files and stop. Private details suppressed.\n')
    print('Created private secret files and public Caddy configuration; no values printed.')


if __name__=='__main__':main()
