# BB10 root ritual — `pathtrust` / `btool` / `__root`

**Applies to:** Classic, Passport, Q10 (all BB10 / QNX devices with the getroot
autoloader). This is the **only known real-root path on BB10** and it is
**software** (no hardware needed).

---

## The idea

BB10 has a **Pathtrust** LSM: an executable's setuid only works if the kernel
trusts its path. The getroot autoloader's root payload is **`btool`** — a shell
script that runs **as root at boot** via the autoroot mechanism (reachable
through the `/base/scripts/ota_info_pps.sh` symlink).

`btool` whitelists files with:

```
/proc/boot/pathtrust !<path>      # '!' = trust this *file*
```

The pre-rooted autoloader adds `!/accounts/devuser/rootdata/launcher_patcher`
and `!/base/bin/mod_nvram`. To get **interactive real root**, add:

```
/proc/boot/pathtrust !/base/bin/__root      # btool line 31
```

Then `__root` (a setuid-root ELF) becomes trusted → it spawns a **root ksh**.
This re-applies **every boot** because autoroot runs `btool` each boot.

## Why it's persistent-but-not

The trust is re-applied by `btool` at **every boot** (boot autoroot + switchzone),
so it is not stored persistently by itself — it depends on `btool` carrying the
line. Patch the on-device `btool` (world-writable in the Android container) with
the whitelist line, then a reboot re-trusts `__root`.

## Verification

```sh
echo 'id' | /base/bin/__root      # must print uid=0(root)
```

If it prints `Operation not permitted`, `btool` is missing the line (stock
reflash restored it) — re-apply the patched `btool` and reboot.

## Notes

- The root shell is a **QNX ksh** — only ksh builtins + trusted native binaries.
  `id`/`whoami` may not exist; use `typeset -p`, `echo $UID`, or a trusted
  `/base/bin/` tool.
- This is **not** a bootloader unlock: `boot0`/`boot1` remain hardware
  write-protected. See [bbss-boot-wp.md](bbss-boot-wp.md).

## Evidence

- Classic: `Blackberry-Classic-Research/notes/session7o-classic-real-root.md`
  (+ `session12-passport-root/classic/btool.patched`, line 31).
- Cross-checked against `bb10.root.sx` (Oleksandr) — identical mechanism.
