import os
# try open /proc/<pid>/as for sdmmc 2330666 and own-family under this process
for pid in ['2330666','253961']:
    for how in ['O_RDONLY','O_RDWR']:
        try:
            fd=os.open('/proc/'+pid+'/as', os.O_RDONLY if how=='O_RDONLY' else os.O_RDWR)
            try:
                d=os.read(fd,4); print(pid, how, "OPEN read4", d.hex() if d else 'empty')
            except OSError as e:
                print(pid, how, "OPEN but read ERR", e)
            os.close(fd)
        except OSError as e:
            print(pid, how, "ERR", e)
