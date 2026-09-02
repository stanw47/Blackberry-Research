================================================================================
SESSION 7Y - MAP_DEVICE CAPABILITY: COMMON AMONG DRIVERS, NOT UNIQUE TO SCREEN
================================================================================
2026-09-02. Answers (empirically, on-device) whether the QNX `screen` process
holds a special physical-memory capability that the kgsl/MAP_PHYS escalation
workstream is missing, and whether that surface is unique to `screen`.

[0] METHOD (reproducible)
  As root (__root heredoc), dump each target's memory map and count the
  `Mapped Phys Memory @virt (phys)` entry type:
      pidin -p <pid> map 2>/dev/null > /tmp/map_<name>.txt
  A `Mapped Phys Memory (phys)` mapping with the `S` flag is a genuine physical
  map. On QNX this REQUIRES the process to hold the `PROCMGR_AID_MAP_DEVICE`
  capability (i.e. it can call MAP_PHYS); MAP_PHYS cannot succeed without it.
  (screen pid = 3596335, binary base/sbin/screen, uid/gid 311.)

[1] RESULTS - PHYS-MAPPING COUNT PER PROCESS (2026-09-02)
    screen            496      io-audio           17
    io-pkt            194      devb-sdmmc(1)      14
    qcore             222      devb-sdmmc(2)      11
    smmu_service      108      devc-serm           6
    powerman           53      io-hid              6
    navigator          45      keypad              6
    io-bb              30      bide                6
    camera2            22      stp_dispatcher      4
    videoCore           2      trustzone           3
    mm-renderer         2      usbmgr              2
    power_brain         2      rpmb                3
    spf                 2      fsecd               2
    adbd                0      cascades            0
    sysmond             0      procnto             0

[2] VERDICT
  MAP_DEVICE is the DEFAULT capability of every hardware/system daemon, not a
  screen-specific privilege. Any QNX process that owns a device node
  (devb-*, io-*, smmu, power, camera, display, net) is launched with it.
  Normal app sandboxes (adbd, cascades/native-ui, sysmon, context) have ZERO
  physical maps.
  - screen maps the MOST (496) because compositing legitimately opens many
    buffers, but this is breadth of its OWN allocations, not unrestricted
    physical visibility.
  - Each driver's maps are localized to its own MMIO: devb-sdmmc -> 0x12400000/
    0xff* SD controller; smmu_service -> 0x7500000..0x7e00000 (SMMU regs);
    camera2 -> camera regs; etc.
  - Therefore "compromise screen" is only a MARGINALLY-fatter target, and is
    NOT required for physical-memory R/W. Code-exec in ANY MAP_DEVICE process
    (devb-sdmmc pid 741404, io-pkt, qcore, smmu_service, ...) yields the same
    latent capability to attempt broader MAP_PHYS. The bottleneck is a
    code-exec / strong-memory-write bug, not the privilege holder.

[3] RELEVANCE TO THE OLEKSANDR/kgsl QUESTION
  - Asked: does the attack surface expand with screen privileges (can he reach
    physical memory / root via the screen process)?
  - Verified answer: owning screen grants a physical-map-capable process, so the
    gate is present — but it is the SAME gate every driver already has. screen
    does not grant access the other MAP_DEVICE processes lack. The expansion is
    only via the *kernel/GPU driver* (Adreno A225 / kgsl / openwfd / GSL) that
    screen drives, NOT via a screen-unique physical-memory capability.
  - Concretely the kgsl MAP_PHYS failure is an access-control/kernel check
    failure in his context; re-homing it to screen does not change whether any
    particular physical region is map-able, because MAP_PHYS permission is
    per-region/per-capability, and screen's own 496 maps are to display/GPU
    buffers, not to arbitrary kernel physical RAM.