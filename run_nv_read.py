#!/usr/bin/env python3
import sys, os, paramiko
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

def run(cmd, t=40):
    i, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    print('$', cmd)
    if out: print(out.rstrip())
    if err: print('[stderr] ' + err.rstrip())

s = c.open_sftp()
s.put('/tmp/nv.py', '/tmp/pp/nv.py')
s.close()
run('echo "/tmp/pp/py3 /tmp/pp/nv.py" | /base/bin/__root', t=40)
c.close()