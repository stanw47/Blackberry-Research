import ctypes, os, sys

DCMD_MMCSD_VUC_CMD = 0xC0441A16  # 68-byte struct (raw MMC cmd passthrough)

class VUC(ctypes.Structure):
    _fields_ = [
        ("result", ctypes.c_int),
        ("opcode", ctypes.c_uint16),
        ("rsvd2", ctypes.c_uint16),
        ("flags", ctypes.c_uint32),
        ("arg", ctypes.c_uint32),
        ("resp", ctypes.c_uint32 * 4),
        ("blk_sz", ctypes.c_uint32),
        ("data_ptr", ctypes.c_uint64),  # paddr_t
        ("buf_off", ctypes.c_uint32),
        ("data_len", ctypes.c_uint32),
        ("timeout", ctypes.c_uint32),
        ("postdelay_us", ctypes.c_uint32),
        ("rsvd_c", ctypes.c_uint32 * 2),
    ]

def main():
    dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/emmc/boot0"
    fd = os.open(dev, os.O_RDWR)
    try:
        print("device:", dev)
        # Try CMD13 (SEND_STATUS) - a harmless read-only raw command.
        # If the driver supports VUC, ret==0 and resp is populated.
        v = VUC()
        v.opcode = 13          # CMD13
        v.arg = 0
        v.flags = 0x00001500   # R1 response
        v.timeout = 5000
        r = ctypes.CDLL(None).devctl(fd, DCMD_MMCSD_VUC_CMD, ctypes.byref(v), ctypes.sizeof(v), None, 0)
        print(f"  VUC CMD13 -> devctl_r={r} result={v.result} resp={[hex(x) for x in v.resp]}")
        # Try CMD6 read of ext_csd[173] would need data buffer; skip for now.
    finally:
        os.close(fd)

if __name__ == "__main__":
    main()