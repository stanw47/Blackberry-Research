import os
p="/dev/slog"
try:
    fd=os.open(p, os.O_RDONLY)
    chunks=[]
    while True:
        b=os.read(fd, 4096)
        if not b: break
        chunks.append(b)
    data=b"".join(chunks).decode(errors="replace")
    import re
    for line in data.splitlines():
        if "ssh" in line.lower() or "sshd" in line.lower() or "auth" in line.lower():
            print(line[:200])
    if not any(("ssh" in l.lower()) for l in data.splitlines()):
        print("(no sshd/slog lines found; raw tail below)")
        print(data[-1500:])
    os.close(fd)
except Exception as e:
    print("slog read err:", repr(e))
