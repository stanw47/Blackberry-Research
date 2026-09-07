import ctypes, os, sys

DCMD_MMCSD_WRITE_PROTECT = 0xC0201A11  # 32-byte struct

class WP(ctypes.Structure):
    _fields_ = [
        ("action", ctypes.c_uint32),
        ("mode", ctypes.c_uint32),
        ("lba", ctypes.c_uint64),
        ("nlba", ctypes.c_uint64),
        ("rsvd2", ctypes.c_uint64),
    ]

def main():
    dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/emmc/boot0"
    fd = os.open(dev, os.O_RDWR)
    try:
        print("device:", dev)
        for tag, action, mode, nlba in [
            ("CLR pwr mode=1 nlba=1", 0, 1, 1),
            ("CLR pwr mode=1 nlba=8192", 0, 1, 8192),
            ("SET pwr mode=1 nlba=1", 1, 1, 1),
            ("CLR nlba=0xFFFF", 0, 1, 0xFFFF),
        ]:
            wp = WP(); wp.action=action; wp.mode=mode; wp.lba=0; wp.nlba=nlba
            r = ctypes.CDLL(None).devctl(fd, DCMD_MMCSD_WRITE_PROTECT, ctypes.byref(wp), ctypes.sizeof(wp), None, 0)
            print(f"  WP {tag:28s} -> devctl_r={r}")
    finally:
        os.close(fd)

if __name__ == "__main__":
    main()