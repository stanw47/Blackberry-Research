# authboot / RTAS — the BlackBerry Android command gate

**Applies to:** Priv (MSM8992), KEYone (MSM8953), and by design the KEY2 lineage.
**Proven on:** Priv (`AAW068`), KEYone (`ABL766`) — decoded from the shipped
`emmc_appsboot.mbn` and the official autoloader's `authboot`/`pcauthtool`.

---

## What it is

TCL/BlackBerry Android devices replace stock fastboot with **`authboot`** — a
fork that requires **authorization from a BlackBerry service** before any
privileged bootloader operation. This is the single biggest reason these phones
cannot be bootloader-unlocked by software.

## The mechanism (decoded from LK `aboot`)

Every fastboot command is checked against a whitelist table:

```
authboot_check_command_permission(name)
  -> authboot_cmd_whitelist        (name, type, flag)
  -> authboot_check_permission(type)
       type 0  = ALWAYS allowed (getvar, reboot, …)
       type 1  = RTAS-authorized (flash:, erase:, oem set-product-mode)
       type 6  = RTAS-authorized oem set-factory-mode
       type 2..10 = RTAS-authorized (gptinfo, format, read, debug tokens, …)
  -> rtas2_cmd_authorization_check()
       if device has password -> auth_password()   (RTAS challenge/response)
       else                   -> auth_rtas_init() -> auth_rtas_has_permission()
  -> sends a message to the local bbauthtool daemon over a socket, waits for
     the authorization bitmap reply.
```

Key facts:
- **`oem unlock` is not in the whitelist at all** — it never succeeds unaided.
- **`flash`/`erase`/`set-factory-mode` all require the RTAS bitmap.**
- The **`devinfo`** unlock byte (`ANDROID-BOOT!` struct, offset `0x10`) is only
  writable via the on-device worker (`set_device_unlock` → `write_device_info`
  → RPMB) or EDL — no unauthenticated fastboot path reaches it.
- `pcauthtool` performs the RTAS challenge/response and needs **RIMNET
  credentials**; `authboot` needs a local **"BB Tool Auth" daemon**.

## Why it matters

On a **retail, locked** device there is **no software-only unlock**: the gate is
an external, BlackBerry-controlled authorization service. This is consistent
with the community record — the KEYone was never cracked; the KEY2 fell only
because it uses a **different (UEFI ABL) stack** with an unpatched Qualcomm bug
(CVE-2021-1931), not because authboot was defeated.

## Evidence

- Priv: [`Blackberry-Priv-Research/notes/priv-research-log.txt`](https://github.com/stanw47/Blackberry-Priv-Research) §3–4
- KEYone: `Blackberry-KeyOne-Research` notes (RTAS2 protocol, token bypass map,
  `nvverify` branch) + the live `authboot command permission denied` probes.
- Live (KEYone): `fastboot oem device-info` → `authboot command permission denied`.

## Related

- [lk-vs-abl.md](lk-vs-abl.md) — why KEY2 is different
- [bbss-boot-wp.md](bbss-boot-wp.md) — the other half of the lock
- [edl-firehose.md](edl-firehose.md) — the only bypass (needs physical entry)
