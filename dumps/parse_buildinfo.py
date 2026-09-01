import struct
_BUILD_INFO_FORMAT = "<II4sI64s16s16s12sIIIIIIIIIIIIIIIIIIIIII40s1024s"
def parse(blob):
    b = struct.unpack(_BUILD_INFO_FORMAT, blob[:struct.calcsize(_BUILD_INFO_FORMAT)])
    return {
      'version': '.'.join(str(x) for x in b[2]),
      'size': b[1],
      'hwid': hex(b[3]),
      'builder': b[5].decode('latin1').split('\0')[0],
      'date': b[6].decode('latin1').split('\0')[0] + ' ' + b[7].decode('latin1').split('\0')[0],
      'secure_field8': b[8],
      'secure': (b[8] == 0),
      'rev_table_offset': b[18] - b[15]*4 - b[13]*2,
      'rev_table_size': b[13]*2,
      'mct_offset': b[18] - b[15]*4,
      'mct_size': b[15]*4,
      'processor_id': b[20],
      'usbloader_id': b[24],
    }
for fn in ["nvram0.img", "boot0.img", "boot1.img", "dmi0.img"]:
    data = open(fn, "rb").read()
    idx = data.find(b"RIM BlackBerry Device")
    if idx < 0:
        print(f"{fn}: 'RIM BlackBerry Device' NOT found")
        continue
    print(f"=== {fn}: found at offset 0x{idx:x} ===")
    off = idx - 0x10
    try:
        info = parse(data[off:off+0x4fc])
        for k,v in info.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print("  parse error:", e)
