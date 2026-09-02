import paramiko
import paramiko.transport as P
_orig = paramiko.transport.Transport.__init__
def _new(self, *a, **kw):
    kw.setdefault('server_sig_algs', False)
    return _orig(self, *a, **kw)
paramiko.transport.Transport.__init__ = _new
key = paramiko.RSAKey.from_private_key_file("/tmp/pp/id_rsa")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(hostname="169.254.0.1", port=22, username="devuser", pkey=key,
          disabled_algorithms={'pubkeys':['rsa-sha2-512','rsa-sha2-256']}, timeout=20, allow_agent=False, look_for_keys=False)
script = r"""echo ROOT
echo "=== kgsl nodes ==="
ls -la /dev/kgsl* 2>&1
echo "=== world-accessible /dev nodes ==="
ls -la /dev/ 2>/dev/null | grep -E '^.(rwx|...).*(r..r..r..|r..r..---|......rwx|r..rw..rw)' | head -80
echo "=== all /dev count ==="
ls -1 /dev/ 2>/dev/null | wc -l
echo DONE
exit
"""
stdin,stdout,stderr = c.exec_command("/base/bin/__root", timeout=30)
stdin.write(script); stdin.flush(); stdin.channel.shutdown_write()
print(stdout.read().decode(errors='replace'))
print("ERR", stderr.read().decode(errors='replace'))
c.close()
