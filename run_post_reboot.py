#!/usr/bin/env python3
import os, sys, paramiko
import paramiko.transport as P
_orig = paramiko.transport.Transport.__init__
def _new(self, *a, **kw):
    kw.setdefault('server_sig_algs', False)
    return _orig(self, *a, **kw)
paramiko.transport.Transport.__init__ = _new
key = paramiko.RSAKey.from_private_key_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'id_rsa'))
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(hostname='169.254.0.1', port=22, username='devuser', pkey=key,
          disabled_algorithms={'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']},
          timeout=30, auth_timeout=120, banner_timeout=30,
          allow_agent=False, look_for_keys=False)
def run(cmd, t=60):
    i, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode(errors='replace'); err = e.read().decode(errors='replace')
    if out.strip(): print('$', cmd, '\n', out.rstrip())
    if err.strip(): print('[err]', err.rstrip())
run('mkdir -p /tmp/pp')
s = c.open_sftp()
s.put('/tmp/opencode/py311/python3.11/extracted/python3_ntoarmv7-qnx-static/tools/python3/python3.11', '/tmp/pp/py3')
src = '/tmp/opencode/py311/python3.11/extracted/python3_ntoarmv7-qnx-static/lib/python3.11'
dstbase = '/tmp/pp/site/lib/python3.11'
flist = []
for root, dirs, files in os.walk(src):
    rel = os.path.relpath(root, src)
    for f in files:
        flist.append((os.path.join(root, f), rel))
ds = set(os.path.dirname(f) for _, f in flist)
for d in sorted(ds):
    try: s.mkdir(os.path.join(dstbase, d).replace('/./','/'))
    except Exception: pass
n = 0
for local, rel in flist:
    remote = os.path.join(dstbase, rel, os.path.basename(local)).replace('/./','/')
    s.put(local, remote); n += 1
s.close()
run('chmod 755 /tmp/pp/py3')
run("echo '/proc/boot/pathtrust /tmp/pp' | /base/bin/__root", t=15)
run("echo 'PYTHONHOME=/tmp/pp/site PYTHONPATH=/tmp/pp/site/lib/python3.11 /tmp/pp/py3 -c \"import os; print(\"PY OK\", os.name)\"' | /base/bin/__root", t=40)
s = c.open_sftp(); s.put('/tmp/nvwrite.py','/tmp/pp/nvwrite.py'); s.close()
run("echo 'PYTHONHOME=/tmp/pp/site PYTHONPATH=/tmp/pp/site/lib/python3.11 /tmp/pp/py3 /tmp/pp/nvwrite.py' | /base/bin/__root", t=120)
c.close()