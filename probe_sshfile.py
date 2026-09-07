import os
path = "/etc/ssh/authorized_keys2"
dpath = "/etc/ssh"
print("file stat:", os.stat(path))
print("dir stat:", os.stat(dpath))
print("mkdir test:", end=" ")
try:
    # try touching a new file in /etc/ssh to see dir writability
    with open(dpath+"/._t", "at") as f:
        f.write("x")
    print("dir WRITABLE by us, wrote test file")
    os.remove(dpath+"/._t")
except Exception as e:
    print("dir NOT writable:", repr(e))
print("rename-over file test:", end=" ")
src = "/accounts/1000/shared/misc/berrycore/id_rsa.pub"
try:
    os.rename(src, path)  # needs write on dir
    print("RENAME OK -> replaced authorized_keys2!")
    os.chmod(path, 0o600)
except Exception as e:
    print("rename failed:", repr(e))
# try direct write regardless
try:
    fd = os.open(path, os.O_RDWR)
    os.write(fd, open("/accounts/1000/shared/misc/berrycore/id_rsa.pub","rb").read())
    os.close(fd)
    print("DIRECT O_RDWR WRITE OK")
except Exception as e:
    print("direct o_rdwr write failed:", repr(e))