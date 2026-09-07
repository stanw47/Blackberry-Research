import os,struct,fcntl,sys

# DCMDs from dcmd_sim_mmcsd.h (values confirmed by r2/session8)
DCMD_WRITE_PROTECT = 0xc0201a11        # __DIOTF: struct in+out
DCMD_CARD_REGISTER= 0xc0181a14
DCMD_ERASE        = 0xc0201a13
# also the r2-confirmed ext_csd read dcmd
DCMD_READ_EXT     = 0x40011a46

# MMCSD_WRITE_PROTECT: action(u32) mode(u32) lba(u64) nlba(u64) rsvd2(u64)
def mk_wp(action, mode, lba, nlba):
    return struct.pack('<IIQQQ', action, mode, lba, nlba, 0)

def mk_card_reg(action, rtype, addr, length):
    return struct.pack('<IIIII', action, rtype, addr, length, 0)

def devctl(fd, dcmd, buf, in_ok=True):
    # QNX ioctl for DIOTF: single buffer both in+out.
    try:
        return fcntl.ioctl(fd, dcmd, buf, True)  # mutate buf
    except OSError as e:
        return e.errno

def main():
    path = sys.argv[1] if len(sys.argv)>1 else '/dev/emmc'
    try:
        fd = os.open(path, os.O_RDONLY) or os.open(path, os.O_RDONLY)
    except OSError as e:
        print("open", path, "ERR", e); return
    print("opened", path)

    # --- read EXT_CSD via CARD_REGISTER (type=EXT_CSD=2) ---
    # struct: action(0=READ) type(2) address length rsvd[2] then data[length]
    reg = bytearray(32 + 512)   # 20B header + 512B ext_csd
    struct.pack_into('<IIIII', reg, 0, 0, 2, 0, 512, 0)
    rc = devctl(fd, DCMD_CARD_REGISTER, reg)
    data = bytes(reg[20:])
    print("CARD_REGISTER EXT_CSD rc=", rc)
    print("  ext_csd[0xaa] BOOT_CONFIG_PROT =", hex(data[0xaa] if len(data)>0xaa else -1))
    print("  ext_csd[0xad] BOOT_WP          =", hex(data[0xad] if len(data)>0xad else -1))
    print("  ext_csd[0xb3] BOOT_WP_STATUS   =", hex(data[0xb3] if len(data)>0xb3 else -1))
    print("  ext_csd[0x1a8]PARTITION_ACCESS =", hex(data[0x1a8] if len(data)>0x1a8 else -1))
    print("  ext_csd[0x1a8+?] PARTITION_SETTING_COMPLETED =", hex(data[0x1ba] if len(data)>0x1ba else -1))
    print("  ext_csd first bytes:", data[:32].hex())

    # --- WRITE_PROTECT: ACTION=CLR(0), mode=0  on boot0 ---
    for (tag, action, mode, lba, nlba) in [
        ("CLR mode0 nlba=1",  0,0,0,1),
        ("CLR mode0 nlba=8192",0,0,0,8192),
        ("SET mode1 nlba=1",  1,1,0,1),
        ("CLR mode0 nlba=0xFFFF",0,0,0,0xFFFF),
    ]:
        buf = bytearray(mk_wp(action,mode,lba,nlba))
        rc = devctl(fd, DCMD_WRITE_PROTECT, buf)
        print(f"WRITE_PROTECT [{tag}] action={action} mode={mode} nlba={nlba} -> rc={rc}")
        os.close(fd)
        fd = os.open(path, os.O_RDONLY) or os.open(path, os.O_RDONLY)

    os.close(fd)

main()