import ctypes, os, sys

DCMD_MMCSD_CARD_REGISTER = 0xC0181A14

class MMC_REG(ctypes.Structure):
    _fields_ = [
        ("action", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("address", ctypes.c_uint32),
        ("length", ctypes.c_uint32),
        ("rsvd", ctypes.c_uint32 * 2),
    ]

REG_SIZE = ctypes.sizeof(MMC_REG)  # 24

def read_extcsd(fd, addr, length):
    total = REG_SIZE + length
    buf = (ctypes.c_uint8 * total)()
    reg = MMC_REG.from_buffer(buf)
    reg.action = 0x00
    reg.type = 0x02
    reg.address = addr
    reg.length = length
    ret = ctypes.CDLL(None).devctl(fd, DCMD_MMCSD_CARD_REGISTER, buf, total, None, 0)
    if ret != 0:
        ctypes.set_errno(ret)
        return ret, None
    data = list(buf[REG_SIZE:REG_SIZE+length])
    return 0, data

def main():
    dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/emmc/boot0"
    fd = os.open(dev, os.O_RDWR)
    try:
        print("device:", dev)
        for name, addr in [
            ("BOOT_BUS_WIDTH", 0xB7), ("PARTITION_CONFIG", 0xB8),
            ("BOOT_CONFIG_PROT", 0xAA), ("BOOT_WP", 0xAD),
            ("BOOT_WP_STATUS", 0xB3), ("BOOT_INFO", 0xA2),
            ("USER_WP", 0xAB), ("ERASE_GRP_SIZE", 0x28),
            ("ERASE_GRP_MULT", 0x2A), ("WP_GRP_SIZE", 0x2A),
            ("HC_WP_GRP_SIZE", 0x2A), ("BOOT_SIZE_MULTI", 0x5A),
        ]:
            r, d = read_extcsd(fd, addr, 1)
            if r == 0 and d:
                print(f"  ext_csd[0x{addr:02X}] {name:20s} -> val=0x{d[0]:02X}")
            else:
                print(f"  ext_csd[0x{addr:02X}] {name:20s} -> devctl_r={r}")
        r, data = read_extcsd(fd, 0xA8, 0x20)
        if r == 0 and data:
            print("  raw[0xA8:0xC8] =", " ".join(f"{b:02x}" for b in data))
    finally:
        os.close(fd)

if __name__ == "__main__":
    main()