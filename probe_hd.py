import os,fcntl
hf=''
# read first 16 bytes + try get size via lseek to try offsets
for n in range(8):
    d='/dev/hd%d'%n
    try:
        fd=os.open(d, os.O_RDWR)
        data=os.read(fd, 16)
        # try seek to end to find size
        try:
            sz=os.lseek(fd, 0, os.SEEK_END)
        except OSError as e:
            sz='ERR'+str(e)
        os.close(fd)
        print(d, 'rdevOK size=', sz, 'head16=', data.hex())
    except OSError as e:
        print(d, 'ERR', e)
