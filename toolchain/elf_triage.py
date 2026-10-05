#!/usr/bin/env python3
"""Quick ELF triage for the pulled BlackBerry KEYone libraries/binaries."""
import sys, os
import lief

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "recon", "bin")

INTERESTING = (
    "bide", "pathtrust", "token", "auth", "secure", "tct", "vtnvfs", "nvuser",
    "blackberry", "bbry", "bbsig", "insecure", "unlock", "factory", "trustzone",
    "capability", "signature", "verity", "grsec", "pax", "selinux", "/dev/",
)


def interesting_strings(path, minlen=5):
    try:
        data = open(path, "rb").read()
    except OSError as e:
        return [f"<read error {e}>"]
    out = []
    cur = bytearray()
    for b in data:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= minlen:
                s = cur.decode("ascii", "replace")
                low = s.lower()
                if any(k in low for k in INTERESTING):
                    out.append(s)
            cur = bytearray()
    if len(cur) >= minlen:
        s = cur.decode("ascii", "replace")
        if any(k in s.lower() for k in INTERESTING):
            out.append(s)
    return out


def main():
    targets = sys.argv[1:] or sorted(os.listdir(BIN))
    for name in targets:
        path = os.path.join(BIN, name)
        if not os.path.isfile(path):
            continue
        print("=" * 72)
        print(f"FILE: {name}  ({os.path.getsize(path)} bytes)")
        try:
            b = lief.parse(path)
        except Exception as e:
            print(f"  [lief parse error: {e}]")
            b = None
        if b is not None:
            try:
                machine = b.header.machine_type
            except Exception:
                machine = "?"
            print(f"  type={b.header.file_type}  machine={machine}  entrypoint=0x{b.entrypoint:x}")
            # Exported dynamic symbols (FUNC, GLOBAL)
            funcs = []
            for sym in b.dynamic_symbols:
                try:
                    if sym.is_function and sym.visibility == lief.ELF.Symbol.VISIBILITY.DEFAULT:
                        funcs.append(sym.name)
                except Exception:
                    pass
            funcs = sorted({f for f in funcs if f})
            if funcs:
                print(f"  exported funcs ({len(funcs)}):")
                for f in funcs:
                    print(f"    {f}")
            libs = sorted({str(l) for l in b.libraries})
            if libs:
                print(f"  NEEDED: {', '.join(libs)}")
        print("  interesting strings:")
        seen = set()
        for s in interesting_strings(path):
            if s not in seen:
                seen.add(s)
                print(f"    {s}")
        print()


if __name__ == "__main__":
    main()
