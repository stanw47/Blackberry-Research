import os
for d in ['/dev/emmc/boot0','/dev/emmc/boot1','/dev/emmc/os0']:
    size=None
    try:
        fd=os.open(d, os.O_RDONLY)
        data=os.read(fd, 16)
        try: size=os.lseek(fd,0,os.SEEK_END)
        except OSError as e: size='ERR'+str(e)
        os.close(fd)
        print(d, 'R ONLY size=', size, 'head16=', data.hex())
    except OSError as e:
        print(d, 'RO ERR', e)
    try:
        fd=os.open(d, os.O_RDWR)
        data=os.read(fd, 16)
        try: size=os.lseek(fd,0,os.SEEK_END)
        except OSError as e: size='ERR'+str(e)
        # try a write of existing data back (no change)
        os.lseek(fd,0,0)
        n=os.write(fd, data)
        os.close(fd)
        print(d, 'RW OK size=', size, 'head16=', data.hex(), 'wrote', n)
    except OSError as e:
        print(d, 'RW ERR', e)
