# Passport — Android prototype (`oslo`)

| Field | Value |
|---|---|
| Model | BlackBerry Passport (retail-demo prototype), `oslo` / `oslorow` |
| SoC | MSM8974PRO-AA |
| OS | native Android 5.1 (LMY47D), build AAA787 (Apr 5 2015), `androidboot.imagetype=sfi` |
| Kernel | 3.4.0-grsec-g0ea3e38 |
| Secure state | `bbss_wp_type=power-on`, `bbss_insecure=false`, dm-verity active |
| Bootloader | locked / authboot-gated |
| Root | rooted in the `vold` domain (non-persistent, page-cache only) |
| Repo | https://github.com/stanw47/Blackberry-Passport-Research (private) |

**Headline:** production-signed Android prototype (identical PKI to retail
`boot0`); Dirty COW (CVE-2016-5195) via `PTRACE_POKEDATA` → root in `vold`
(full generic `block_device` read/write) → full boot-chain + kernel/ramdisk dump.

**Status:** alive; read-only historical specimen. **No autoloader exists — do
not wipe, flash, or unlock.**

**Details:** secondary device in the Passport repo — see
`notes/session22`–`session26` and `recon/passport-boot-dumps/`.
