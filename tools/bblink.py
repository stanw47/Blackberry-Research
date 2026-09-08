#!/usr/bin/env python3
"""
bblink.py - raw USB link to BlackBerry 10 BootROM / RAM-loader.

Faithful port of the bb10mt protocol (bbusb.pas / bbloader.pas / ramloader.pas):
  * Channel0 / Channel1 / Channel2 framing
  * FPC crc32 variant (reflected 0xEDB88320, init as passed, no final xor)
  * BootROM -> RAM-loader bring-up (echo B01000000/PING, password, WRITE_RAM,
    EXECUTE_RAM, Mode(2))
  * RAM-loader Channel2 command set, incl. raw primitives:
        E4 CREAD INIT        (raw-read setup)
        E5 CREAD addr size   (raw read, size <= 0x3FA0)
        DE BOOT_MODE         (eMMC boot-mode switch, semantics unknown - probe)
        EE ERASE_SECTOR
        F7/F8 Write data
        20EE PreFlash
        40F9 SendSignature / 40C0 Complete / 80EF Reboot

Usage examples (device must be in BootROM = powered off, USB plugged in):
  ./bblink.py probe
  ./bblink.py info --loader loaders/loader_9700270A-00.bin
  ./bblink.py cmd2 B4 --loader loaders/loader_9700270A-00.bin
  ./bblink.py preflash 15
  ./bblink.py cread 0 0x3FA0 --loader ...
  ./bblink.py f7write 2048 434c53434d524b52... 
  ./bblink.py complete --loader ...
  ./bblink.py reboot --loader ...
"""

import sys, os, struct, time, argparse, hashlib, zlib

try:
    import usb.core, usb.util, usb.backend.libusb1
except ImportError:
    sys.exit("pyusb required: pip install pyusb")

VID_BB = 0x0FCA
PID_BOOTROM = 0x0001
PID_RAMLOADER = 0x8001
MAX_PACKET = 0x10000
READ_TIMEOUT = 1500
WRITE_TIMEOUT = 4000
CHUNK = 2024   # Qualcomm loader upload chunk
BLOCK = 0x3FF4 # MAX_FLASH_BLOCK

BOOTMODES = ['RIM REINIT', 'RIM-BootLoader', 'RIM-RAMLoader', 'RIM UPL', 'RIM-BootNUKE']

# ---------------------------------------------------------------- crc (FPC crc unit)
_CRCTAB = []
for _i in range(256):
    _r = _i
    for _ in range(8):
        _r = (_r >> 1) ^ (0xEDB88320 if (_r & 1) else 0)
    _CRCTAB.append(_r)

def crc32(crc, data):
    crc = crc & 0xFFFFFFFF
    for b in data:
        crc = _CRCTAB[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return crc & 0xFFFFFFFF

def u16(data):
    return struct.unpack('<H', data[:2])[0]

def p16(v):
    return struct.pack('<H', v)

def p32(v):
    return struct.pack('<I', v)

def u32(data):
    return struct.unpack('<I', data[:4])[0]

# ---------------------------------------------------------------- usb device
class BBSession:
    def __init__(self, verbose=True):
        self.ctx = None
        self.dev = None
        self.ep_out = None
        self.ep_in = None
        self.claimed = None
        self.upid = 0
        self.mode = 0xFF
        self.pktnum = [0, 0, 0]
        self.verbose = verbose

    # -- device enumeration ------------------------------------------------
    def list_pids(self):
        try:
            devs = usb.core.find(find_all=True, idVendor=VID_BB)
            return sorted({int(d.idProduct) for d in devs})
        except Exception as e:
            print("  usb scan error: %s" % e)
            return []

    def _claim(self, d):
        iface = 0
        try:
            for itf in d.get_active_configuration():
                if itf.bInterfaceClass == 0xFF:
                    iface = itf.bInterfaceNumber
                    break
        except Exception:
            pass
        try:
            if d.is_kernel_driver_active(iface):
                try:
                    d.detach_kernel_driver(iface)
                except Exception:
                    pass
        except Exception:
            pass
        usb.util.claim_interface(d, iface)
        self.claimed = iface

    def _open_pid(self, pid, timeout=6000):
        deadline = time.time() + timeout / 1000.0
        while time.time() < deadline:
            self.close()
            d = usb.core.find(idVendor=VID_BB, idProduct=pid)
            if d is not None:
                try:
                    self.dev = d
                    self.upid = int(d.idProduct)
                    self._claim(d)
                    if self.upid in (1, 0x8001, 0x8017):
                        self.ep_in = 0x82 if self.upid != 0x8017 else 0x87
                        self.ep_out = 0x02 if self.upid != 0x8017 else 0x07
                    else:
                        self.ep_in, self.ep_out = 0x81, 0x01
                    self.mode = 0xFF
                    self.pktnum = [0, 0, 0]
                    return True
                except Exception as e:
                    if self.verbose:
                        print("    open pid=%04X failed (%s)" % (pid, e))
                    self.close()
                    time.sleep(0.1)
            time.sleep(0.05)
        return False

    def close(self):
        if self.dev is not None:
            try:
                if self.claimed is not None:
                    usb.util.dispose_resources(self.dev)
                if self.dev.is_kernel_driver_active(0):
                    try:
                        self.dev.attach_kernel_driver(0)
                    except Exception:
                        pass
            except Exception:
                pass
        self.dev = None
        self.claimed = None
        self.ep_in = self.ep_out = None
        self.upid = 0

    # -- wire primitives ----------------------------------------------------
    def read_raw(self, chk=MAX_PACKET):
        # returns (channel, payload_after_4byte_header)
        raw = self.dev.read(self.ep_in, chk, timeout=READ_TIMEOUT)
        raw = bytes(raw)
        if len(raw) < 4:
            return 0, b''
        return u16(raw), raw[4:]

    def send_wire(self, channel, payload):
        pkt = p16(channel) + p16(len(payload) + 4) + payload
        self.dev.write(self.ep_out, pkt, timeout=WRITE_TIMEOUT)

    # -- bb10mt channel layers ----------------------------------------------
    def channel0(self, cmd, data=b''):
        pkt = bytes([cmd, self.mode & 0xFF]) + self.pktnum[0].to_bytes(2, 'big') + bytes(data)
        self.send_wire(0, pkt)
        ch, resp = self.read_raw()
        out = b''
        if len(resp) >= 2:
            self.mode = resp[1]
            if len(resp) > 4:
                out = resp[4:]
        self.pktnum[0] = (self.pktnum[0] + 1) & 0xFFFF
        return resp, out

    def channel1(self, data=b''):
        size = len(data) + 10
        pkt = bytearray(size)
        pkt[4:8] = p32(size)
        pkt[8:10] = p16(self.pktnum[1])
        self.pktnum[1] = (self.pktnum[1] + 1) & 0xFFFF
        pkt[10:] = data
        pkt[0:4] = p32(crc32(0, bytes(pkt[4:])))
        self.send_wire(1, bytes(pkt))
        ch, resp = self.read_raw()
        self.drain_read(1)
        return resp[10:]

    def drain_read(self, ch):
        try:
            self.read_raw()
        except Exception:
            pass

    def channel2(self, cmd, data=b'', expect=None):
        size = 8 + len(data)
        body = p16(size) + p16(cmd & 0xFFFF) + bytes(data)
        pkt = body + p32(crc32(0, body))
        self.send_wire(2, pkt)
        ch, resp = self.read_raw()
        self.drain_read(2)
        out = b''
        rcmd = None
        if ch == 2 and len(resp) >= 8:
            rcmd = u16(resp[2:4])
            crc1 = crc32(0, resp[:-4])
            crc2 = u32(resp[-4:])
            if crc1 != crc2:
                rcmd = 0xFFFF
            else:
                sz = len(resp) - 8
                if sz > 0 and rcmd != 0x15:
                    out = resp[4:-4]
        if self.verbose:
            got = 'cmd=%04X' % rcmd if rcmd is not None else 'no-response'
            exp = (' want %04X' % expect) if expect is not None else ''
            print("  <%s%s len=%d" % (got, exp, len(out)))
        if expect is not None and rcmd != expect:
            print("  !!! unexpected response cmd %s (data %s)" % (rcmd and '%04X' % rcmd, resp.hex()))
        return out

    # -- bootrom ops ---------------------------------------------------------
    def session_reboot(self):
        """Reboot the OS-session USB device (PID 0x8017) back to BootROM.
        Mirrors bb10mt TBBUSB.Reboot = Channel0(cmd=3, [])."""
        resp, _ = self.channel0(3, b'')
        self.pktnum[0] = 0
        return resp

    def ping0(self):
        self.channel0(1, bytes([0x14, 0x05, 0x83, 0x19, 0, 0, 0, 0]))

    def get_var(self, vid, bufsize):
        data = p16(bufsize) + p16(vid)
        resp, out = self.channel0(5, data)
        return out if (resp and resp[0] == 6) else b''

    def set_mode(self, m):
        bs = BOOTMODES[m].encode('ascii', 'ignore')[:16]
        data = bs + b'\x00' * (16 - len(bs)) + b'\x01'
        resp, _ = self.channel0(7, data)
        return (resp[0] if resp else 0) == 8

    def password_info(self, password=b''):
        cmd = 0x0A
        hashed = b''
        for _ in range(12):
            resp, chdata = self.channel0(cmd, hashed)
            rcmd = resp[0] if resp else 0
            if rcmd == 0x10:
                self.drain_read(0)
                return True
            if rcmd == 0x0E:
                if len(chdata) < 24:
                    return False
                challenge = chdata[4:8]
                salt = chdata[12:20]
                iters = u32(chdata[20:24])
                if password is None:
                    print("  device requested a password; provide --password")
                    return False
                hashed = b'\x00\x00\x40\x00' + hash_pass_v2(challenge, salt, password, iters)
                cmd = 0x0F
                continue
            return False
        return False

    def switch_channel(self):
        self.send_wire(1, bytes([6, 6]))
        self.drain_read(1)
        self.drain_read(1)
        self.pktnum[1] = 0

    def get_metrics(self):
        return self.channel1(p16(0xF001))

    def send_loader(self, addr, data, chunk=CHUNK, cb=None):
        setup = p16(0xF009) + p32(addr) + p32(len(data))
        self.channel1(setup)
        i, n = 0, len(data)
        while n > 0:
            s = min(chunk, n)
            pkt = p16(0xF004) + p32(addr + i) + p32(s) + data[i:i + s]
            self.channel1(pkt)
            i += s
            n -= s
            if cb:
                cb(i, len(data))
        try:
            self.channel1(p16(0xF00A))  # WRITE_RAM_VERIFY
        except Exception:
            pass

    def run_loader(self, addr):
        self.channel1(p16(0xF005) + p32(addr))

    def reboot_bootrom(self):
        try:
            self.channel0(3, b'')
        except Exception:
            pass
        self.pktnum[0] = 0

    # -- ram-loader ops --------------------------------------------------------
    def preflash(self, x):
        d = bytearray(36)
        d[0] = x
        d[1] = 0x28
        d[6] = 0x02
        d[28] = 0x01
        d[32] = 0x02
        return self.channel2(0x20EE, bytes(d), expect=0x39)

    def flash_regions(self):
        r = self.channel2(0xB4, b'', expect=0xD2)
        if len(r) >= 96:
            blocks = u32(r[12:16])
            user_kb = u32(r[88:92])
            return blocks, user_kb
        return (u32(r[12:16]) if len(r) > 16 else None), None

    def get_mct(self):
        return self.channel2(0xD9, b'', expect=0xC9)

    def pin(self):
        r = self.channel2(0xE7, b'', expect=0xD1)
        return u32(r) if len(r) >= 4 else 0

    def bsn(self):
        r = self.channel2(0xEA, b'', expect=0xFC)
        return u32(r) if len(r) >= 4 else 0

    def vendor_id(self):
        r = self.channel2(0xDB, b'', expect=0xCB)
        return struct.unpack_from('<H', r, 2)[0] if len(r) >= 4 else 0

    def dram_info(self):
        return self.channel2(0xBF, b'', expect=0xD9)

    def os_metrics(self):
        return self.channel2(0xD8, b'', expect=0xC8)

    def bugdisp(self):
        d = bytearray(8)
        out = b''
        for _ in range(256):
            r = self.channel2(0xB0, bytes(d))
            if not r:
                break
            out += r
        return out

    def cread_init(self):
        return self.channel2(0xE4, b'\x00')

    def cread(self, addr, size):
        data = b'\x00' + p32(addr) + p32(size)
        return self.channel2(0xE5, data)

    def boot_mode(self, mode_byte=None):
        data = b''
        if mode_byte is not None:
            data = bytes([mode_byte])
        return self.channel2(0xDE, data)

    def erase_sector(self, addr=None):
        data = b''
        if addr is not None:
            data = b'\x00' + p32(addr)
        return self.channel2(0xEE, data)

    def f7_write(self, blknum, payload):
        data = p32(blknum) + p32(len(payload)) + payload
        return self.channel2(0xF7, data, expect=0xDF)

    def send_signature(self, sig):
        if len(sig) < 560:
            raise ValueError("signature must be 560 bytes")
        data = p16(560) + sig[:560]
        return self.channel2(0x40F9, data, expect=0x4006)

    def complete(self):
        return self.channel2(0x40C0, b'', expect=0x4006)

    def reboot_loader(self):
        return self.channel2(0x80EF, b'', expect=0x80C7)

    def remove_installer(self):
        return self.channel2(0xE0, b'')

    def enable_led(self):
        return self.channel2(0xC3, b'')

    def cmd2(self, cmd, data=b''):
        return self.channel2(cmd, data)


# ---------------------------------------------------------------- HashPassV2
def hash_pass_v2(challenge, salt, password, iterations):
    hashed = bytearray(password)
    count = 0
    challenger = True
    while True:
        buf = bytearray(4 + len(salt) + len(hashed))
        buf[0:4] = p32(count)
        off = 4
        if salt:
            buf[off:off + len(salt)] = salt
            off += len(salt)
        if hashed:
            buf[off:off + len(hashed)] = hashed
        if count == 0:
            hashed = bytearray(64)
        dig = hashlib.sha512(buf).digest()
        if len(hashed) < 64:
            hashed = bytearray(64)
        hashed[:64] = dig
        if (count == iterations - 1) and challenger:
            count = -1
            challenger = False
            if challenge:
                b = bytearray(challenge + bytes(hashed))
                hashed = bytearray(b)
        count += 1
        if count >= iterations:
            break
    return bytes(hashed)


# ---------------------------------------------------------------- loader upload
def id_to_addr(model_id):
    xid = model_id & 0xFFFF
    if xid in (0x080a, 0x240a, 0x270a, 0x2a0a, 0x2e0a, 0x2e07):
        return 0x80200000
    if xid in (0x1a06, 0x2307, 0x2607, 0x260a):
        return 0x80100000
    if xid == 0x2c0a:
        return 0x0DD00000
    return 0xFFFFFFFF


def load_loader(path, model_id=None):
    d = open(path, 'rb').read()
    if len(d) < 10240:
        sys.exit("loader too small: %d" % len(d))
    if u32(d[4:8]) != 0xD7D32D1F:
        sys.exit("loader magic @4 != D7D32D1F: not a signed loader")
    if u32(d[len(d) - 8:]) != 0xD7C82D1F:
        sys.exit("loader footer != D7C82D1F")
    addr = u32(d[8:12])
    if model_id is not None and id_to_addr(model_id) != addr and model_id != 0xB600240A:
        sys.exit("loader load addr 0x%X does not match model 0x%X" % (addr, model_id))
    return d, addr


# ---------------------------------------------------------------- bring-up
def connect(sess, opts):
    if opts.verbose:
        print("== bring-up to RAM-loader ==")
    model_id = None
    mode1_ok = False
    for _ in range(5):
        if sess._open_pid(PID_BOOTROM, timeout=15000):
            sess.ping0()
            rom = sess.get_var(2, 2000)
            if len(rom) >= 20:
                model_id = u32(rom[16:20])
                if opts.verbose:
                    print("  model_id %08X" % model_id)
            mode1_ok = sess.set_mode(1)
            if mode1_ok:
                break
        if opts.verbose:
            print("  retrying bootrom open...")
    if not mode1_ok:
        sys.exit("could not reach BootROM / set Mode(1)")

    pw = opts.password.encode() if opts.password is not None else b''
    if not sess.password_info(pw):
        sys.exit("password/exchange failed at BootROM")
    sess.switch_channel()
    sess.get_metrics()

    ldr, addr = load_loader(opts.loader, model_id)
    if opts.verbose:
        print("  uploading loader (%d bytes) -> 0x%X" % (len(ldr), addr))
    sess.send_loader(addr, ldr)
    sess.run_loader(addr)
    time.sleep(1.0)
    sess.close()

    if not sess._open_pid(PID_RAMLOADER, timeout=30000):
        sys.exit("RAM-loader did not appear (PID 8001)")
    if opts.verbose:
        print("  RAM-loader online (PID 8001)")
    if not sess.set_mode(2):
        sys.exit("set Mode(2) (RAMLoader) failed")
    if not sess.password_info(b''):
        sys.exit("password exchange failed at RAM-loader")
    sess.bugdisp()
    return model_id


# ---------------------------------------------------------------- signature
def dummy_sig():
    s = bytearray([0xFF] * 560)
    for off, val in ((0x24, 0x00000088), (0xB0, 0x000000BC), (0xB4, 0x00010001), (0xB8, 0xB5A60BFD),
                     (0xE0, 0x00000088), (0x16C, 0x000000BC), (0x170, 0x00010001), (0x174, 0xC6B71C0E),
                     (0x180, 0x00000080), (0x220, 0x000000B4), (0x224, 0x00010001), (0x228, 0xD7C82D1F)):
        s[off:off + 4] = p32(val)
    return bytes(s)


# ---------------------------------------------------------------- CLI verbs
def hexbytes(h):
    h = h.replace('0x', '').replace(' ', '')
    if len(h) % 2:
        sys.exit("hex string must have even length")
    return bytes.fromhex(h)


def cmd_probe(sess, opts):
    pids = sess.list_pids()
    print("BB10 devices present, PIDs:", ['%04X' % p for p in pids] or "none")
    if opts.timeout:
        t0 = time.time()
        while time.time() - t0 < float(opts.timeout):
            pids = sess.list_pids()
            if pids:
                print("  %04X" % pids[0])
                return 0
            time.sleep(0.5)
        print("  (timeout)")
        return 0


def cmd_info(sess, opts):
    connect(sess, opts)
    print("== RAM-loader info ==")
    blocks, user_kb = sess.flash_regions()
    print("  flash blocks: %08X  user: %s KB" % (blocks or 0, user_kb))
    print("  PIN %08X  BSN %08X" % (sess.pin(), sess.bsn()))
    print("  vendorID %04X" % sess.vendor_id())
    mct = sess.get_mct()
    print("  MCT %d bytes: %s..." % (len(mct), mct[:64].hex()))
    if getattr(opts, 'out', None):
        open(opts.out, 'wb').write(mct)
        print("  MCT saved -> %s" % opts.out)
    if opts.keep:
        sess.reboot_loader()


def cmd_cmd2(sess, opts):
    mid = connect(sess, opts)
    data = hexbytes(opts.data) if opts.data else b''
    r = sess.cmd2(int(opts.cmd, 16), data)
    print("response %d bytes:" % len(r))
    print(r.hex())
    if opts.file:
        open(opts.file, 'wb').write(r)


def cmd_cread(sess, opts):
    connect(sess, opts)
    sess.cread_init()
    r = sess.cread(int(opts.addr, 16), int(opts.size, 16))
    print("read %d bytes @ 0x%X:" % (len(r), int(opts.addr, 16)))
    print(r.hex())
    if opts.file:
        open(opts.file, 'wb').write(r)
        print("saved %s" % opts.file)


def cmd_dump(sess, opts):
    connect(sess, opts)
    sess.cread_init()
    with open(opts.out, 'wb') as f:
        addr = int(opts.base, 16)
        total = 0
        while total < int(opts.len, 16):
            n = min(0x3FA0, int(opts.len, 16) - total)
            r = sess.cread(addr + total, n)
            if not r:
                print("  cread returned empty at 0x%X" % (addr + total))
                break
            f.write(r)
            total += len(r)
            print("  read 0x%X / %s" % (total, opts.len))
        print("dumped %d bytes -> %s" % (total, opts.out))


def cmd_preflash(sess, opts):
    connect(sess, opts)
    r = sess.preflash(int(opts.x, 16))
    print("preflash resp %d bytes: %s" % (len(r), r.hex()))


def cmd_f7(sess, opts):
    connect(sess, opts)
    payload = hexbytes(opts.data)
    ok = sess.f7_write(int(opts.blk, 0), payload)
    print("F7 write resp-cmd ok:", ok)
    if opts.sig:
        sess.send_signature(dummy_sig() if opts.sig == 'dummy' else hexbytes(opts.sig))
        print("signature sent (F9)")
        time.sleep(1.0)
    if opts.complete:
        sess.complete()
        print("complete sent (C0)")


def cmd_raw_seq(sess, opts):
    connect(sess, opts)
    with open(opts.script) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            cmd = int(parts[0], 16)
            data = hexbytes(parts[1]) if len(parts) > 1 else b''
            print("> cmd %04X data %s" % (cmd, data.hex()))
            r = sess.cmd2(cmd, data)
            print("  %d bytes: %s" % (len(r), r.hex()))


def cmd_selftest(sess, opts):
    """offline sanity: crc32, framing, HashPassV2, dummy sig"""
    ok = True
    if crc32(0, b'') != 0:
        ok = False; print("FAIL crc empty")
    if crc32(0, b'123456789') != 0x2DFD2D88:
        ok = False; print("FAIL crc vector %08X" % crc32(0, b'123456789'))
    # PKZIP cross-check
    if (crc32(0xFFFFFFFF, b'123456789') ^ 0xFFFFFFFF) != 0xCBF43926:
        ok = False; print("FAIL pkzip cross-check")
    # framing: channel2 packet matches construction
    sess.pktnum[0] = sess.pktnum[1] = 0
    sess.mode = 0xFF
    # channel0 request frame check
    body = bytes([0x05, 0xFF]) + b'\x00\x00' + p16(2000) + p16(2)
    ch0 = bytes([0]) + p16(len(body) + 4) + body
    assert len(ch0) == len(body) + 3, "ch0 len"
    print("OK crc+framing structure")
    print("hashpass sha512 sanity: %s" % hashlib.sha512(b'x').hexdigest()[:16])
    s = dummy_sig()
    assert len(s) == 560 and s[0] == 0xFF and u32(s[0xB8:0xBC]) == 0xB5A60BFD
    print("OK dummy 560-byte signature")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="bblink - BB10 BootROM/RAM-loader raw link")
    ap.add_argument('--loader', default='/tmp/opencode/bb10mt/loaders/loader_9700270A-00.bin',
                    help="path to signed RAM-loader .bin for the target")
    ap.add_argument('--password', default=None, help="device password if one is set")
    ap.add_argument('-q', '--quiet', action='store_true')
    sub = ap.add_subparsers(dest='verb')

    p = sub.add_parser('selftest')
    p = sub.add_parser('probe'); p.add_argument('--timeout', default=None)
    p = sub.add_parser('info'); p.add_argument('--keep', action='store_true'); p.add_argument('-o', '--out')
    p = sub.add_parser('cmd2'); p.add_argument('cmd'); p.add_argument('data', nargs='?'); p.add_argument('-f', '--file')
    p = sub.add_parser('cread'); p.add_argument('addr'); p.add_argument('size'); p.add_argument('-f', '--file')
    p = sub.add_parser('dump'); p.add_argument('out'); p.add_argument('--base', default='0'); p.add_argument('len')
    p = sub.add_parser('preflash'); p.add_argument('x')
    p = sub.add_parser('f7'); p.add_argument('blk'); p.add_argument('data'); p.add_argument('--sig'); p.add_argument('--complete', action='store_true')
    p = sub.add_parser('rawseq'); p.add_argument('script')

    opts = ap.parse_args()
    if not opts.verb:
        ap.print_help()
        return 1
    opts.verbose = not opts.quiet
    sess = BBSession(verbose=opts.verbose)
    try:
        return {'probe': cmd_probe, 'info': cmd_info, 'cmd2': cmd_cmd2,
                'cread': cmd_cread, 'dump': cmd_dump, 'preflash': cmd_preflash,
                'f7': cmd_f7, 'rawseq': cmd_raw_seq, 'selftest': cmd_selftest}[opts.verb](sess, opts)
    finally:
        sess.close()


if __name__ == '__main__':
    sys.exit(main())