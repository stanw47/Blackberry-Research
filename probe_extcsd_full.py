import ctypes, os, sys
DCMD_MMCSD_CARD_REGISTER = 0xC0181A14
class MMC_REG(ctypes.Structure):
    _fields_ = [("action",ctypes.c_uint32),("type",ctypes.c_uint32),
                ("address",ctypes.c_uint32),("length",ctypes.c_uint32),
                ("rsvd",ctypes.c_uint32*2)]
REG_SIZE = ctypes.sizeof(MMC_REG)
def read_extcsd(fd, addr, length):
    total = REG_SIZE + length
    buf = (ctypes.c_uint8*total)()
    reg = MMC_REG.from_buffer(buf)
    reg.action = 0x00; reg.type = 0x02; reg.address = addr; reg.length = length
    ret = ctypes.CDLL(None).devctl(fd, DCMD_MMCSD_CARD_REGISTER, buf, total, None, 0)
    if ret != 0:
        ctypes.set_errno(ret); return ret, None
    return 0, list(buf[REG_SIZE:REG_SIZE+length])
def main():
    dev = sys.argv[1] if len(sys.argv)>1 else "/dev/emmc/boot1"
    fd = os.open(dev, os.O_RDWR)
    r, d = read_extcsd(fd, 0, 512)
    if r != 0:
        print("full read failed:", r); os.close(fd); return
    print("device:", dev, "full read ok, len", len(d))
    fields = [
        ("EXT_CSD_REV",0x200),("SEC_COUNT_lo",0x208),("ERASE_GRP_SIZE",0x1C),
        ("HC_ERASE_GRP_SIZE",0x23),("BOOT_SIZE_MULTI",0x5A),("MAX_ENH_SIZE_MULTI",0x5E),
        ("PARTITION_SWITCH_TIME",0xB7),("OUT_OF_INTERRUPT_TIME",0xB0),
        ("B_BOOT_INFO",0xA2),("BOOT_CONFIG_PROT",0xB2),("BOOT_WP",0xAD),
        ("BOOT_WP_STATUS",0xB4),("USER_WP",0xAB),("PARTITION_CONFIG",0xB3),
        ("BOOT_BUS_WIDTH",0xB1),("ERASED_MEM_CONT",0xB6),("SECTOR_SIZE",0x2B),
        ("SECTOR_COUNT_lo",0xB8),("ENH_START_ADDR",0xB0),("SEC_BAD_BLK_MGMNT",0xB3),
        ("FFU_STATUS",0x201),("FFU_ARG",0x202),
    ]
    for name, off in fields:
        print(f"  [{off:02X}] {name}" + (f" -> 0x{d[off]:02X}" if off < len(d) else " (oob)"))
    print("  raw[0xA0:0xC0] =", " ".join(f"{b:02x}" for b in d[0xA0:0xC0]))
    print("  raw[0x00:0x40] =", " ".join(f"{b:02x}" for b in d[0x00:0x40]))
    os.close(fd)
if __name__ == "__main__":
    main()