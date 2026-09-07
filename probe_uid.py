import os, sys
print("uid real/eff:", os.getuid(), os.geteuid())
print("gid real/eff:", os.getgid(), os.getegid())
# try opening a /proc/as to test root capability
for p in ["/proc/boot/as", "/proc/1/as"]:
    try:
        fd = os.open(p, os.O_RDWR)
        print("OPEN OK", p, "fd", fd)
        os.close(fd)
    except Exception as e:
        print("OPEN FAIL", p, repr(e))
# Try open boot0 rw (should work as Disk_Drivers)
try:
    fd = os.open("/dev/emmc/boot0", os.O_RDWR)
    print("boot0 rw open OK fd", fd)
    os.close(fd)
except Exception as e:
    print("boot0 open fail", repr(e))