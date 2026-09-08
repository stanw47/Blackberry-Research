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
s = c.open_sftp()
src = '/tmp/opencode/py311/python3.11/extracted/python3_ntoarmv7-qnx-static/lib/python3.11'
dstbase = '/tmp/pp/site/lib/python3.11'
n, total = 0, 0
os.makedirs('/tmp/opencode/sent', exist_ok=True)
flist = []
for root, dirs, files in os.walk(src):
    rel = os.path.relpath(root, src)
    for f in files:
        flist.append((os.path.join(root, f), rel))
# mkdirs first
dirs = set(os.path.dirname(f) if f else '' for _, f in flist)
for r in sorted(dirs):
    p = os.path.join(dstbase, r).replace('/./', '/')
    try: s.mkdir(p)
    except Exception: pass
bad = []
for local, rel in flist:
    remote = os.path.join(dstbase, rel, os.path.basename(local))
    remote = remote.replace('/./', '/')
    try:
        s.put(local, remote)
        n += 1
    except Exception as e:
        bad.append((remote, str(e)))
    total += 1
    if n % 200 == 0:
        print('put %d/%d...' % (n, total))
print('DONE %d files; failed %d: %s' % (n, len(bad), bad[:5]))
s.close(); c.close()