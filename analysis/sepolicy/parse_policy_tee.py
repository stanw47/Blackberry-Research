#!/usr/bin/env python3
import struct, sys

data = open(sys.argv[1] if len(sys.argv) > 1 else '/home/stanw47/priv-research/sepolicy/sepolicy_aaw068.bin','rb').read()
off = 0
def rd(n):
    global off
    b = data[off:off+n]; off += n
    assert len(b) == n, f"truncated at {off} (file {len(data)})"
    return b
def u32(): return struct.unpack('<I', rd(4))[0]
def u16(): return struct.unpack('<H', rd(2))[0]
def u64(): return struct.unpack('<Q', rd(8))[0]
def u8(): return rd(1)[0]

def ebitmap():
    mapunit = u32(); highbit = u32(); count = u32()
    for _ in range(count):
        u32(); u64()

def type_set():
    ebitmap(); ebitmap(); u32()

def mls_level():
    u32(); ebitmap()

def mls_range():
    items = u32()
    for _ in range(items):
        u32()
    ebitmap()
    if items > 1:
        ebitmap()

CEXPR_NAMES = 5
def read_cons(ncons, allowxtarget):
    for _ in range(ncons):
        u32()
        nexpr = u32()
        for _ in range(nexpr):
            et = u32(); attr = u32(); op = u32()
            if et == CEXPR_NAMES:
                ebitmap(); type_set()

magic = u32(); slen = u32(); s = rd(slen)
version = u32(); config = u32(); sym_num = u32(); ocon_num = u32()
if version >= 22: ebitmap()
if version >= 23: ebitmap()

types = {}; types_by_name = {}; classes = {}; commons = {}

# commons (0)
nprim = u32(); nel = u32()
for _ in range(nel):
    l = u32(); val = u32(); pnprim = u32(); pnel = u32()
    name = rd(l).decode()
    perms = {}
    for _ in range(pnel):
        pl = u32(); pv = u32(); pn = rd(pl).decode()
        perms[pv] = pn
    commons[name] = (val, perms)

# classes (1)
nprim = u32(); nel = u32()
for _ in range(nel):
    l = u32(); l2 = u32(); val = u32(); pnprim = u32(); pnel = u32(); ncons = u32()
    name = rd(l).decode()
    comkey = rd(l2).decode() if l2 else None
    perms = {}
    for _ in range(pnel):
        pl = u32(); pv = u32(); pn = rd(pl).decode()
        perms[pv] = pn
    read_cons(ncons, 0)
    nc = u32(); read_cons(nc, 1)
    u32(); u32(); u32()
    u32()
    classes[val] = (name, perms, comkey)

# roles (2)
nprim = u32(); nel = u32()
for _ in range(nel):
    l = u32(); val = u32(); bounds = u32()
    rd(l); ebitmap(); ebitmap()

# types (3)
nprim = u32(); nel = u32()
for _ in range(nel):
    l = u32(); val = u32(); prop = u32(); bounds = u32()
    name = rd(l).decode()
    types[val] = name
    types_by_name[name] = val

# users (4)
nprim = u32(); nel = u32()
for _ in range(nel):
    l = u32(); val = u32(); bounds = u32()
    rd(l); ebitmap(); mls_range(); mls_level()

# bools (5)
nprim = u32(); nel = u32()
for _ in range(nel):
    u32(); u32(); l = u32(); rd(l)

# levels (6)
nprim = u32(); nel = u32()
for _ in range(nel):
    l = u32(); u32(); rd(l); mls_level()

# cats (7)
nprim = u32(); nel = u32()
for _ in range(nel):
    l = u32(); u32(); u32(); rd(l)

# avtab
AVTAB_ALLOWED = 0x0001
AVTAB_OP = 0x7700
avnel = u32()
allow_rules = []
for i in range(avnel):
    src = u16(); tgt = u16(); cls = u16(); spec = u16()
    if spec & AVTAB_OP:
        u8(); rd(32)
    else:
        perm = u32()
    if spec == AVTAB_ALLOWED:
        allow_rules.append((src, tgt, cls, perm))

print(f"policy: version={version} types={len(types)} classes={len(classes)} allow={len(allow_rules)}")

def find_class(name):
    for v,(n,p,c) in classes.items():
        if n == name: return v
    return None

def class_perms(cls_idx):
    cname, perms, comkey = classes[cls_idx]
    allp = {}
    if comkey:
        cval, cperms = commons[comkey]
        allp.update(cperms)
    allp.update(perms)
    return allp

chr_file = find_class('chr_file')
print(f"chr_file class idx = {chr_file}")
chr_perms = class_perms(chr_file)  # {bit: name}

# interesting target types for qseecom access
for tname in ['tee_device','tee_exec','tee','qseecom_device','drmrpc_socket']:
    idx = types_by_name.get(tname)
    print(f"type {tname} -> {idx}")

def dump_access(tgt_name, cls_idx, label):
    tgt = types_by_name.get(tgt_name)
    if tgt is None or cls_idx is None:
        print(f"[{label}] target/class missing")
        return {}
    found = {}
    for (src, t, cls, perm) in allow_rules:
        if t == tgt and cls == cls_idx:
            found[src] = found.get(src, 0) | perm
    print(f"\n=== [{label}] {tgt_name}:{classes[cls_idx][0]} — domains ({len(found)}) ===")
    for src in sorted(found):
        perm = found[src]
        bits = []
        for b,name in chr_perms.items():
            if (perm >> b) & 1:
                bits.append(name)
        print(f"  {types.get(src,'?'):30s} idx={src:4d} perms={'|'.join(bits) if bits else '0x%x'%perm}")
    return found

tee_dev = dump_access('tee_device', chr_file, 'QSEECOM DEVICE')
dump_access('tee_exec', find_class('file'), 'TEE EXEC (file)')
dump_access('tee', find_class('file'), 'TEE TYPE (file)')

# summary: domains with 'open' bit on tee_device:chr_file
open_bit = None
for b,name in chr_perms.items():
    if name == 'open': open_bit = b
print(f"\nchr_file 'open' perm bit = {open_bit}")
if open_bit is not None:
    print("\n=== DOMAINS THAT CAN OPEN /dev/qseecom (tee_device:chr_file open) ===")
    opens = sorted(src for src,perm in tee_dev.items() if (perm >> open_bit) & 1)
    for src in opens:
        print(f"  {types.get(src,'?')}")
    print(f"total: {len(opens)}")
