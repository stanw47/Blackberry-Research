# Appendix E: Security Policy Analysis

## Full 6-Layer Defense Stack

```
┌─────────────────────────────────────────────────────────┐
│ 1. Boot Chain Signing (ECDSA P-256)                     │
│    PBL → SBL1 → TZ → aboot → boot.img → dm-verity      │
├─────────────────────────────────────────────────────────┤
│ 2. GRSEC/PaX (in-tree kernel hardening)                 │
│    PAX_REFCOUNT, SIGKILL on violations, UDEREF          │
├─────────────────────────────────────────────────────────┤
│ 3. SELinux (mandatory access control)                   │
│    Enforcing mode, u:r:shell:s0 for devuser             │
├─────────────────────────────────────────────────────────┤
│ 4. Pathtrust (filesystem trust LSM)                     │
│    ENFORCES exec/mmap/module/firmware from trusted only  │
├─────────────────────────────────────────────────────────┤
│ 5. BIDE (integrity detection + TZ bridge)               │
│    Audit-only, 7 mapped detection gaps                  │
├─────────────────────────────────────────────────────────┤
│ 6. dm-verity (block integrity)                          │
│    /system + /oem, auto-trusts for Pathtrust            │
└─────────────────────────────────────────────────────────┘
```

## Pathtrust Enforcement Map

### LSM Hooks

| Hook | Function | Blocks |
|---|---|---|
| `sb_mount` | `pathtrust_sb_mount` | Mount from untrusted source |
| `sb_kern_mount` | `pathtrust_sb_kern_mount` | Kern mount from untrusted |
| `bprm_set_creds` | `pathtrust_bprm_set_creds` | Exec from non-trusted FS |
| `mmap_file` | `pathtrust_mmap_file` | mmap PROT_EXEC from non-trusted |
| `kernel_fw_from_file` | `pathtrust_kernel_fw_from_file` | Firmware load from non-trusted |
| `kernel_module_from_file` | `pathtrust_kernel_module_from_file` | Module load from non-trusted |

### Enforcement Toggle

- `pathtrust_enforce = 1` (compiled in)
- `/sys/kernel/security/pathtrust/enforce` write path **COMPILED OUT**
- No runtime toggle possible

### Subject Conditions

| Condition | Check |
|---|---|
| `is_root(cred)` | euid==0 OR egid==0 |
| `has_banned_caps()` | ANY of: CHOWN, DAC_OVERRIDE, DAC_READ_SEARCH, FOWNER, MAC_ADMIN, MAC_OVERRIDE, MKNOD, SETGID, SETUID, SYS_ADMIN, SYS_MODULE, SYS_PTRACE, SYS_RAWIO |
| `is_forbidden_sid()` | SELinux sid in pathtrust forbidden list |

### Trusted Filesystems

| Filesystem | Trusted? | Reason |
|---|---|---|
| `/` (rootfs) | YES | Mount option |
| `/system` (dm-0) | YES | dm-verity auto-trust |
| `/oem` (dm-1) | YES | dm-verity auto-trust |
| `/base` (rcfs) | Via whitelist | `!/base/bin/__root` etc. |
| `/data` (dm-2) | NO | Not dm-verity, not whitelisted |
| `/efs` | NO | Not trusted |
| `/radio` | Via whitelist | `!/base/bin/mod_nvram` |
| External SD | NO | Not trusted |

## BIDE Sensor Mapping

| Hook | Sensor | Trigger |
|---|---|---|
| `task_create` | no-op | — |
| `task_free` | auth_remove_pid | process exit |
| `task_fix_setuid` | SN_ESCALATED_UID/GID | setuid/setgid syscall |
| `sb_mount` | SN_NOSUID, SN_NODEV | MS_NOSUID/MS_NODEV removed |
| `mmap_file` | SN_LOW_MMAP_ADDR | mmap_min_addr < DEFAULT |
| `capset` | SN_CAPSET | cap not already 'allowed' |
| `bprm_set_creds` | SN_ROOT_PROCESS_DETECTOR | new root proc |
| `file_mprotect` | SN_MPROTECT | CROSS-process only |
| `kernel_module_*` | **COMPILED OUT** | Never fires |

## BIDE Detection Gaps

| Gap | Detail |
|---|---|
| G1 | `file_mprotect` skips self-mprotect (VM_SHARED or same mm) |
| G2 | `task_fix_setuid` only fires on syscall path, not kernel cred overwrite |
| G3 | `capset` uses 32-bit `int` for 64-bit `kernel_cap_t` — caps 32-63 invisible |
| G4 | `sb_mount` only flags mounts that REMOVE nosuid/nodev |
| G5 | All sensors gated by snapshot — blind before JBIDE takes snapshot |
| G6 | VMA scanner only scans ROOT processes |
| G7 | Module hashing compiled out (`#ifdef AVEN_44469_FIXED`) |

## BIDE Snapshot Mechanism

```
JBIDE boots → BIDE_IOCTL_TAKE_SNAPSHOT
  → tz_init_kernel() → tz_gen_keypair
  → vma_scan_task(current) → baseline JBIDE memory
  → atomic_inc(taken)
  → caps_clean_list(0)
  → vma_scan_processes() → full scan
```

If `tz_init_kernel()` fails → `taken` stays 0 → BIDE permanently blind.

## SELinux Policy Highlights

| Domain | Allowed Binder Targets |
|---|---|
| shell | keystore, surfaceflinger |
| untrusted_app | keystore, dataminer |
| system_app | fidodaemon |
| platform_app | fidodaemon |
| servicemanager | fidodaemon |

Shell has NO binder rule to: fidodaemon, drmserver, mediaserver, qseeproxy.

## GRSEC/PaX Features

| Feature | Status | Impact |
|---|---|---|
| `PAX_REFCOUNT` | Compiled in | Atomic refcount overflow protection |
| `PAX_RANDKSTACK` | Compiled in | Random kernel stack offset |
| `PAX_RANDUSTACK` | Compiled in | Random user stack offset |
| `PAX_MEMORY_SANITIZE` | Compiled in | Freed memory zeroed |
| `PAX_MEMORY_STACKLEAK` | Compiled in | Stack data cleared on return |
| `PAX_MEMORY_UDEREF` | Compiled in | User/kernel pointer separation |
| SIGKILL on violations | Compiled in | All PaX violations → SIGKILL |

## QSEECOM Attack Surface

### 24 QSEECOM-Capable Domains

system_server, mfg_security, mfg_nvram, tee, drmserver, keystore,
wfdservice, mcStarter, seempd, tbaseLoader, secotad, qseeproxy, init,
qfp-daemon, mediaserver, seemp_health_daemon, gatekeeperd, mdtpdaemon,
vtnvfsd, surfaceflinger, fidodaemon, vold, mfg_widevine, mfg_customization.

### Shell-Reachble + QSEECOM-Capable

Only: `keystore`, `surfaceflinger`.

### Keystore Attack Surface

- Binary: aarch64, 125KB, Android 6.0.1 (Mar-2018 BB build)
- `BnKeystoreService::onTransact` @ `0x91dc` (5412B switch)
- FORTIFY'd: `asprintf` (not sprintf), `__memcpy_chk` present
- Remaining surface: integer-arithmetic / count-overflow in blob and KeystoreArg parse paths

## Stealth Recipe (Avoids All Sensors)

1. Kernel write primitive → direct cred overwrite (skip setuid syscall)
2. Raw-block token write (skip file LSM / setenforce)
3. Do NOT mprotect OTHER processes
4. Do NOT mount without nosuid/nodev
5. Do NOT call setenforce(0)
6. Do NOT panic
