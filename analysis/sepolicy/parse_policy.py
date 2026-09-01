#!/usr/bin/env python3
import struct

data = open('/tmp/opencode/sepolicy_aaw068','rb').read()
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
    ebitmap()   # types
    ebitmap()   # negset
    u32()       # flags

def mls_level():
    u32(); ebitmap()

def mls_range():
    items = u32()
    for _ in range(items):
        u32()      # sens
    ebitmap()      # level[0].cat
    if items > 1:
        ebitmap()  # level[1].cat

CEXPR_NAMES = 5
def read_cons(ncons, allowxtarget):
    for _ in range(ncons):
        u32()  # permissions
        nexpr = u32()
        for _ in range(nexpr):
            et = u32(); attr = u32(); op = u32()
            if et == CEXPR_NAMES:
                ebitmap()   # names
                type_set()  # types + negset + flags

magic = u32(); slen = u32(); s = rd(slen)
version = u32(); config = u32(); sym_num = u32(); ocon_num = u32()
print(f"magic=0x{magic:08x} version={version} config={config} sym_num={sym_num} ocon_num={ocon_num}")
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
    name = rd(l).decode()
    ebitmap(); ebitmap()
print(f"after roles off={off}")

# types (3)
nprim = u32(); nel = u32()
for _ in range(nel):
    l = u32(); val = u32(); prop = u32(); bounds = u32()
    name = rd(l).decode()
    types[val] = name
    types_by_name[name] = val
print(f"after types off={off} types={len(types)}")

# users (4)
nprim = u32(); nel = u32()
for _ in range(nel):
    l = u32(); val = u32(); bounds = u32()
    name = rd(l).decode()
    ebitmap()
    mls_range(); mls_level()
print(f"after users off={off}")

# bools (5)
nprim = u32(); nel = u32()
for _ in range(nel):
    val = u32(); state = u32(); l = u32(); name = rd(l).decode()
print(f"after bools off={off}")

# levels (6)
nprim = u32(); nel = u32()
for _ in range(nel):
    l = u32(); isalias = u32(); name = rd(l).decode()
    mls_level()
print(f"after levels off={off}")

# cats (7)
nprim = u32(); nel = u32()
for _ in range(nel):
    l = u32(); val = u32(); isalias = u32(); name = rd(l).decode()
print(f"after cats off={off}")

# avtab
AVTAB_ALLOWED = 0x0001
AVTAB_OP = 0x7700
avnel = u32()
print(f"avtab nodes={avnel} at off={off}")
allow_rules = []
for i in range(avnel):
    src = u16(); tgt = u16(); cls = u16(); spec = u16()
    if spec & AVTAB_OP:
        u8(); rd(32)
    else:
        perm = u32()
    if spec == AVTAB_ALLOWED:
        allow_rules.append((src, tgt, cls, perm))
print(f"after avtab off={off} total={len(data)} allow_rules={len(allow_rules)}")

ts_idx = types_by_name.get('token_service_socket')
print(f"token_service_socket type index = {ts_idx}")
sock_file_cls = None
for v,(n,p,c) in classes.items():
    if n == 'sock_file': sock_file_cls = v
print(f"sock_file class index = {sock_file_cls}")

def find_perm(cls_idx, name):
    cname, perms, comkey = classes[cls_idx]
    for pv, pn in perms.items():
        if pn == name: return pv
    if comkey:
        cval, cperms = commons[comkey]
        for pv, pn in cperms.items():
            if pn == name: return pv
    return None

write_perm = find_perm(sock_file_cls, 'write')
print(f"write perm bit = {write_perm}")

print("\n=== domains with any allow on token_service_socket:sock_file ===")
found = set()
for (src, tgt, cls, perm) in allow_rules:
    if tgt == ts_idx and cls == sock_file_cls:
        found.add((src, perm))
for src, perm in sorted(found):
    print(f"  {types.get(src,'?')} (idx {src}) perm=0x{perm:x}")

if write_perm is not None:
    print("\n=== domains with 'write' bit ===")
    for src, perm in sorted(found):
        if (perm >> write_perm) & 1:
            print(f"  WRITE: {types.get(src,'?')} (idx {src})")
