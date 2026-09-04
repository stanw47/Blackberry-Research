# Appendix F: Session Index

## Research Sessions (Chronological)

| Session | Date | Topic | Key Finding |
|---|---|---|---|
| 7b | Mar 2026 | Pathtrust snapshot | 6 LSM hooks mapped, enforcement=1 |
| 7c | Mar 2026 | BIDE audit | 7 detection gaps found, audit-only confirmed |
| 7d | Mar 2026 | BIDE detection strategy | VMA scanner, capset, mprotect sensors |
| 7e | Mar 2026 | BIDE audit conclusion | BIDE never blocks, only reports |
| 7f | Mar 2026 | Pathtrust snapshot | dm-verity auto-trust, /data not trusted |
| 7g | Mar 2026 | Live recon (3 outcomes) | SELinux enforcing, boot chain signing mapped |
| 7h | Mar 2026 | Audit conclusion | 6-layer defense stack confirmed |
| 7i | Mar 2026 | vtnvfsd RE | nvuser on-disk format, token sig bypass |
| 7j | Mar 2026 | Classic eMMC access | g_Disk_Drivers achieves raw eMMC read |
| 7k | Mar 2026 | bbss.insecure pinned | boot0@0x35a98, field8 u32, secure=0 |
| 7l | Mar 2026 | boot0 write-protect | B_PWR_WP_EN=0x04, temporary, clearable |
| 7m | Mar 2026 | mmcsdpub decoded | MMCSD publisher, PPS fields |
| 7n | Mar 2026 | Final Classic analysis | Software unlock path exhausted |
| 7o | Mar 2026 | Real uid-0 root | pathtrust whitelist trick → __root setuid |
| 7p | Mar 2026 | DCMD_MMCSD_WRITE_PROTECT | Devctl constants decoded |
| 7q | Mar 2026 | ext_csd boot WP | Power-on temporary, not permanent |
| 7r | Mar 2026 | /proc/as dump | .data writable, .text read-only |
| 7s | Mar 2026 | Oleksandr answer | Unmount + exclusive access needed |
| 7t | Mar 2026 | VFS skeleton | Filesystem hierarchy mapped |
| 7u | Mar 2026 | NVFS/vtnvfs unlinked | FUSE token filesystem RE |
| 7v | Mar 2026 | Driver WP inside mmc_switch | EIO from card, not driver gate |
| 7w | Mar 2026 | Connect ritual | SSH setup, paramiko patches |
| 7y | Mar 2026 | MAP_DEVICE common | procmgr_ability model, phys maps |
| 8a | Mar 2026 | Group wrapper dev/emmc | setgid mechanism, ~400 groups |
| 8b | Mar 2026 | WP grp patch | WP group patching attempt |
| 8c | Mar 2026 | R/W on eMMC driver .data | live ext_csd read, .data write confirmed |
| 8d | Mar 2026 | nlba % wp_grp fails | EINVAL before CMD6 |
| 8e | Apr 2026 | WP convergence | Route A confirmed dead end |
| 9 | Apr 2026 | WRITE_PROTECT re-test | EIO confirmed, card rejects CMD6 |
| 10 | Apr 2026 | getroot/btool/autoroot | Boot-time root mechanism decoded |
| 11a | Apr 2026 | Root dd + HW write-protect | boot0 read OK, write → EROFS |
| 11b | Apr 2026 | /proc/as test | Opened, started reading, hung |
| 11c | Apr 2026 | /proc/as ability gate | MEM_PHYS ability absent, EPERM |
| 11d | May 2026 | SSH userauth hang | sshd server-side bug, key fixed |

## Cross-Reference by Topic

### Boot Chain & Security
- 7b, 7c, 7d, 7e, 7f, 7g, 7h → Security mechanisms (Pathtrust, BIDE, SELinux, dm-verity)
- 7k, 7l, 7n → boot0, bbss.insecure, write-protect
- 10 → getroot, btool, autoroot, pathtrust whitelist

### eMMC Access
- 7j → g_Disk_Drivers, raw eMMC read
- 7m → mmcsdpub, MMCSD publisher
- 8a → Group wrappers, setgid mechanism

### Driver RE
- 7p → DCMD_MMCSD_WRITE_PROTECT decoded
- 7q → ext_csd boot WP analysis
- 7r → sdmmc-rim-msmsdcc driver RE
- 7v → Driver WP inside mmc_switch
- 8c → R/W on driver .data
- 8d, 8e, 9 → WP convergence (Route A dead end)

### Filesystem
- 7s → Oleksandr answer (unmount + exclusive)
- 7t → VFS skeleton
- 7u → NVFS/vtnvfs
- 7i → vtnvfsd RE

### /proc/as
- 7r → /proc/as dump (earlier boots)
- 11b → /proc/as test (regression)
- 11c, 11d → /proc/as ability gate

### SSH / Connection
- 7w → Connect ritual, paramiko patches
- 11d → SSH userauth hang

### Passport / Stage3
- 7n → stage3 decoded
- 7s → Passport MSM8974AA specifics

## Source Files

| File | Location | Purpose |
|---|---|---|
| `asroot_main.c` | `blackberry-research/tools/` | procmgr_ability escalation source |
| `procmgr.h` | `blackberry-research/tools/` | QNX procmgr ability definitions |
| `dcmd_sim_mmcsd.h` | `blackberry-research/resources/` | Devctl struct definitions |
| `probe_wp_correct.py` | `blackberry-research/` | WRITE_PROTECT devctl probe |
| `probe_as_memphys.py` | `blackberry-research/` | /proc/as MEM_PHYS probe |
| `passport_stage3/` | `blackberry-research/tools/` | PBL debug mode exploit (GPL) |
| `imggen/` | `blackberry-research/tools/` | Prototype bootloader generator (GPL) |
| `ramloadercommands.txt` | `blackberry-research/tools/` | RAM loader command reference |
| `priv-research-log.txt` | `blackberry-research/notes/` | Master research log (969 lines) |

## Artifacts

| Artifact | Location | Description |
|---|---|---|
| `boot0.img` | `blackberry-research/dumps/` | Classic boot0 dump (4MB) |
| `boot1.img` | `blackberry-research/dumps/` | Classic boot1 dump (4MB) |
| `nvram0.img` | `blackberry-research/dumps/` | Classic nvram0 dump (4.1MB) |
| `dmi0.img` | `blackberry-research/dumps/` | Classic dmi0 dump (1MB) |
| `__root.bin` | `blackberry-research/dumps/` | Pulled __root ELF (4488B) |
| `sdmmc-rim-msmsdcc` | `priv-research/sdmmc-driver/` | BlackBerry MMC driver binary |
| `g_Disk_Drivers` | `priv-research/` | setgid group wrapper binary |
