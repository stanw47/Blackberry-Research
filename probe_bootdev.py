import os
for d in ['/dev/emmc','/dev/boot0','/dev/boot1']:
    try:
        fd=os.open(d, os.O_RDWR)
        data=os.read(fd, 8)
        print(d, "OPEN R/W, read8:", data.hex())
        os.close(fd)
    except OSError as e:
        try:
            fd=os.open(d, os.O_RDONLY)
            data=os.read(fd, 8)
            print(d, "OPEN R/O, read8:", data.hex())
            os.close(fd)
        except OSError as e2:
            print(d, "ERR R/O:", e2)
