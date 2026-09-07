import os,struct,fcntl
# ext_csd byte 0xa8 (DCMD_MMCSD 0x40011a46) read from live driver via /dev/emmc
DCMD_READ_EXT=0x40011a46
fd=os.open('/dev/emmc', os.O_RDWR)
buf=bytearray(0x40+16)
# per session8a: target@0x0a, lun@0x0b, ext_csd byte read returns at buf+0x30? do raw
try:
    r=fcntl.ioctl(fd, DCMD_READ_EXT, buf, True)
    print("ext_csd read rc", r)
    data=bytes(buf)
    print("buf tail:", data[-16:].hex())
except OSError as e:
    print("ERR", e)
os.close(fd)
