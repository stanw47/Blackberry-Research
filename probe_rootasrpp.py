import os
print("euid", os.geteuid(), "uid", os.getuid())
# try opening /proc/1/as
try:
    fd=os.open("/proc/1/as", os.O_RDWR)
    print("PROC_1_AS OPEN OK fd", fd)
    print("size?", os.lseek(fd,0,os.SEEK_END))
    os.close(fd)
except Exception as e:
    print("open /proc/1/as fail:", repr(e))
# find sdmmc pid by scanning /proc
for pid in os.listdir("/proc"):
    try:
        cmd=open("/proc/%s/cmdline"%(pid,"rb") if False else "/proc/%s/cmdline"%pid,"rb").read().decode(errors='replace')
        if "sdmmc" in cmd or "msmsdcc" in cmd:
            print("FOUND sdmmc pid", pid, repr(cmd))
    except Exception:
        pass
