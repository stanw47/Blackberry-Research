# QNX `vtnvfs` / `/nvram` token storage

**Applies to:** Classic, Passport (BB10), and the Android BlackBerrys (Priv,
KEYone) — all use a Virtual Token NVRAM FS.

---

## What it is

BlackBerry's **`vtnvfs`** (Virtual Token NVRAM FS) mounts per-token FUSE
filesystems under `/nvram`:

```
/nvram/nvuser    rw   tokens (hlos_unsigned.tkn, hlos_signature.tkn, …)
/nvram/perm      rw   permissions / mfg tokens
/nvram/blog      rw   logs
/nvram/boardid   ro
/nvram/prdid     ro
```

- SELinux labels: `vtnvfs_*_file`; `user_id/group_id=2900`.
- `vtnvfsd` serves it; recognizes `*.tkn` token files.

## Why it matters

On BB10/Priv, the **`hlos_unsigned.tkn`** token (state `development`) makes the
bootloader **skip image verification** — the "debug token" bypass. So the token
store is a root-privilege target.

**But** on shipped units the write paths are all gated:
- `TokenService` binder write needs `WRITE_TOKENS` (signature permission).
- The factory `STP`/`bbauth` path needs `inproductionflag=true` (false on retail,
  one-way).
- Direct `/nvram/nvuser` write is SELinux-blocked for `shell`.

## On the KEYone

The same stack is present (`vtnvfsd`, `bb_tokenserviced`, `stp_server`,
`mfg_*`), with `/nvram/{nvuser,perm,blog,boardid,prdid}` mounted — but
`ro.boot.inproductionflag=false` and `stp_server` not running, so the token-signing
path is **dead**, exactly as on the Priv.

## Evidence

- Priv: `notes/priv-research-log.txt` §5–6, §9, §13–14.
- KEYone: live `/nvram` mounts + `mfgUtil` "Device not running in production".
- Classic/Passport: `notes/session7i-vtnvfsd-emmc-isp.md`, `session7y-map-device-common.md`.
