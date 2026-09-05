================================================================================
SESSION 10A - PASSPORT PATH AUDIT: /dev/mem IS A DECOY; SDMMC_ANY CONSTANT DECODED
================================================================================
2026-09-05, Passport (MSM8974AA / WINDERMEREEMEA). This session intentionally did
NOT touch the daily-driver Passport's eMMC; it audited the remaining "no-desolder"
write paths and recorded the exact Oleksandr raw-command interface so we can stop
re-deriving it. The Classic (MSM8960, sacrificial) remains the test-mule for the
actual boot0-unlock (see 9a[5]).

--------------------------------------------------------------------------------
[1] PASSED: real uid-0 root reachability re-confirmed (nothing new, for the log)
--------------------------------------------------------------------------------
SSH->root via the btool/__root pathtrust chain is alive; the driver devctl
channel (CARD_REGISTER / CID / ext_csd read) is reachable under Disk_Drivers.

--------------------------------------------------------------------------------
[2] /dev/mem IS A DECOY - physical-memory patch path RULED OUT (NEW, defensible)
--------------------------------------------------------------------------------
Hypothesis: kernel's raw-memory char device /dev/mem (listed in /dev as
`brw------- 1 root nto 4294967295 ... /dev/mem`) could be used to read/write the
driver's *physical* frame and flip the 4 gate bytes / ".text" NOPs directly,
bypassing the /proc/<pid>/as ".text read-only" restriction.

Measurement program opened /dev/mem O_RDWR (SUCCEEDS as root, errno 0), then
pread() 4096 bytes at a spread of physical addresses across 0x00000000 ..
0xfe000000, and finally did the full 4GB scan at 4KB granularity:

  - Every 4KB page returns the SAME 0xdeadbeef canary (bytes `ef be ad de`
    repeating), regardless of address -- including regions that MUST be live RAM
    (running kernel/driver text) and MMIO that cannot be zero/pattern.
  - A full 0x0..0xffffffff scan read EVERY page without a single error
    (1,048,576 reads) yet found ZERO ELF headers (`\x7fELF`) and zero instances
    of the driver's known gate byte-window. Real RAM is 3GB and full of ELF
    images; finding none means the device returns fabricated uniform data.
  - A pwrite()+pread() round-trip at an arbitrary PA did NOT persist the written
    pattern (read-back differed from what was written).

CONCLUSION: /dev/mem on this build is a security shim (canary/zero-fill), NOT a
window into physical DRAM. It is a DEAD END for both reading true RAM and for
patching the driver's physical code/data. (Do not confuse this with the earlier
"deadbeef" in 7t/7u/7v -- those were researcher-chosen test values written to
driver .bss via /proc/as; THIS is the device itself serving deadbeef.)

Related negative re-confirmed this session: cross-process /proc/<pid>/as WRITE
returns errno 312 ("Server fault on msg pass") for the trusted driver, while a
process's own /proc/self/as write succeeds. So the kernel enforces a
trust-boundary on /proc-as writes (untrusted targets writable, trusted targets
read-only). Combined with (a) no /proc/<pid>/ctl node (no ptrace/procctl),
(b) driver binary lives in immutable /proc/boot ramfs, (c) /dev/mem decoy --
every userland ring-3 path to CODE-patch the driver is now positively ruled out.

--------------------------------------------------------------------------------
[3] OLEKSANDR'S RAW-MMC INTERFACE, DECODED + THE KEY INSIGHT (NEW, archival)
--------------------------------------------------------------------------------
The private sdmmc.zip (never published) is, verbatim from Oleksandr, "adding my
own handler to the driver ... I can execute any commands from CMD0 to CMD255".
His shared.h defines:

    typedef struct _sdmmc_raw_cmd {
        uint32_t cmd_idx;                     // MMC command index (0..255)
        union {
            struct {                          // for raw MMC commands
                uint32_t cmd_arg;             // argument
                uint32_t cmd_flags;           // SCF_CTYPE_* | SCF_RSP_*
                uint32_t data_dir;            // NONE/READ/WRITE
                uint32_t blocksize;           // bytes
                uint32_t blocks;              // count
                uint32_t timeout_ms;          // 0 = default
            } mmc;
            struct {                          // for internal functions
                uint32_t param1, param2, param3, param4;
                void *user_ptr;
            } func;
        } p;
        uint32_t rsp[4];                      // output response words
    } sdmmc_raw_cmd_t;                        // 44 bytes total (0x2C)

    #define DCMD_SDMMC_ANY  __DIOTF(_DCMD_CAM, _SIM_MMCSD + 1, sdmmc_raw_cmd_t)

    #define SDMMC_INTERNAL_FUNC_MASK 0x80000
    #define CMD_FUNC(n) ((n) & ~SDMMC_INTERNAL_FUNC_MASK)
      FUNC_SDIO_SYNCHRONIZE (0x01)
      FUNC_SDIO_SET_PARTITION (0x02)
      FUNC_MMC_INIT_DEVICE    (0x03)
      FUNC_CLEAR_WP           (0x04)
      => CLEAR_WP = 0x80000 | 0x04  is the dedicated "clear boot write-protect"
         entry point (issued via DCMD_SDMMC_ANY with cmd_idx=CLEAR_WP).

CONSTANT DERIVED (downstream of existing encoding in appendix-d):
    struct size = 44 = 0x2C
    DCMD_SDMMC_ANY = (0x2C<<16) | (0x0C<<8) | (3600+1) | 0xC0000000 = 0xC02C0E11
    (using _DCMD_CAM=0x0C, _SIM_MMCSD=3600). NOTE: the *observed on-device*
    write-protect/CID constants (0xC0201A11, 0x40101A44, 0xC0441A16 ...) use a
    `0x1A..` cmd-field, i.e. RIM's driver build appears to derive cmd numbers
    from a DIFFERENT _SIM_MMCSD base than the public QNX header. The important
    takeaway is independent of that base: DCMD_SDMMC_ANY is NOT present in the
    stock dispatch table (grep of the dispatch literals shows no 0x..0E11/0x..1A11
    raw-slot), so the stock driver returns ENOTTY for it.

KEY INSIGHT (the reason every "just craft the devctl" attempt stalls):
    The raw-command handler does NOT EXIST in the stock binary. It is not a
    matter of finding the right dcmd number or unlocking a flag -- the code that
    takes cmd_idx and issues an arbitrary MMC/SDCC command was ADDED by
    Oleksandr's patch and is simply absent here. Therefore no devctl constant,
    no matter how correctly formed, can drive a raw CMD6 on an unpatched driver.
    Re-adding it == patching .text == blocked per [2] (read-only via /proc/as,
    /dev/mem decoy, no ctl, immutable ramfs). FUNC_CLEAR_WP is the distilled
    equivalent of what we must REIMPLEMENT (see below).

--------------------------------------------------------------------------------
[4] POLICY: WHICH IDEA IS VALID, AND WHAT TO DO IF NOT (the user's open asks)
--------------------------------------------------------------------------------
( a ) "force-clear eMMC during a flash so it boots recovery" -- NOT VALID as
      stated. On BB10/QNX the bootloader verifies IFS integrity ITSELF (proved
      empirically in 9b: 1-byte IFS change -> blinking-RED refusal, fully
      recoverable by reflash). There is no global "signature flag" you can clear
      post-flash to make an arbitrary image boot (the Priv's aboot debug-token /
      bbss.insecure path is a DIFFERENT mechanism, tied to firmware/signed NV,
      and doesn't exist verbatim for the QNX boot flow). Force-wiping eMMC wins
      you a red-blink device you then reflash -- not a booting custom OS.
( b ) "rebuild an autoloader with my images inside" -- NOT VALID for the
      boot0/bootloader stage. Sachesi/bb10mt/DBBT/cap.exe rebuild .signed QCFM
      (OS.ufs/rcfs/radio) and the rooted cap.exe only neutralizes the SOFTWARE
      signature check (3-byte diff, 9b[5]); none of that re-signs the
      boot0/SBL1/aboot chain, which is verified by the PBL at a lower layer we
      cannot forge (no BB private key). Building a custom autoloader DOES work
      for the *user/OS* partition (michioxd/autoroot), i.e. root-and-customize,
      but NOT for swapping the bootloader to run LineageOS.
( c ) "Sachesi to alter + repack + reflash signed files" -- VALID for user/OS
      partition modification (setup-bypass, pre-root) -- settled, done long ago.
      NOT a bootloader-unlock primitive for the same reason as (b).
( d ) "run Android on the Passport (daily driver)" via no-desolder software --
      NOT ACHIEVABLE with current knowledge. Every ring-3 primitive is ruled out
      in [2]; the only known-good unlock is Balika's hardware route (desolder
      eMMC -> imggen boot0/user -> ext_csd[179]=0x08 -> fastboot/flash recovery
      -> adb sideload lineage-18.1). That voids the device and is explicitly not
      "no gluing". Decision driver: keep Passport stock as daily driver.
( e ) "sacrifice the Classic to prove the technique end-to-end" -- VALID AND THE
      RECOMMENDED PATH. Classic is MSM8960 (Z30-class; Oleksandr: raw read "works
      fine" there), already rooted, raw eMMC read proven, driver .data proven
      writable, device expendable. Its SoC/emmc boot flow matches bb-usbdl and the
      ext_csd layout is identical to Passport's, so a successful in-session
      B_PWR_WP_EN clear transfers technique-wise. Classic has no Android port, BUT
      proving "clear WP -> write bbss.insecure/prototype BL -> fastboot" here
      de-risks the Passport.

--------------------------------------------------------------------------------
[5] WHAT TO TRY NEXT (ranked; all Classic-side, none touch eMMC until vetted)
--------------------------------------------------------------------------------
 1. Reimplement the raw-MMC channel ourselves (equivalent of Oleksandr's patch)
    WITHOUT .text patching, via the ONE writable hook class available:
    session8c lever (B) -- locate the resmgr dispatch_t in the driver HEAP at
    runtime (readable via /proc/<pid>/as), and LOWER-RISK (C) -- redirect a
    single devctl-reached indirect call in a static .data function-pointer table
    to a .data-resident Thumb thunk that calls existing mmc_switch(hba,1,3,0xAD,0)
    then returns. This converts the proven .data-writable primitive into a
    driver-level "send CMD6 SWITCH ext_csd[173]=0" primitive.
 2. Then issue DCMD_MMCSD_WRITE_PROTECT (action CLR=0) OR the thunk directly, to
    clear B_PWR_WP_EN in-session; boot0 becomes R/W; proceed with 9a[3]/7q plan
    (write prototype BL + bbss.insecure flag from imggen).
 3. If (1)/(2) cannot yield a stable, deterministic call site, accept that
    re-adding the raw handler genuinely requires .text write and pivot to the
    hardware route for the final Android flash -- while keeping the Classic to
    exhaust the RAMLoader-side idea (ramloader.txt: F7/F8 WRITE + F9 40 SIGNATURE_TRAILER
    + C0 40 COMPLETE) as a last no-solder software avenue before any desolder.

ARTIFACTS (this session, Temp\opencode\ on host):
  build/probe15.c, probe15_new   (full-4GB /dev/mem canary scan)
  build/probe16.c, probe16_new   (/dev/mem spread-pread + write/no-persist test)
  query*.sh, fetch_pmap.py       (device inventory / driver pmap capture)
  nops.bin (4x BF00) copied from device rootdata for reference
================================================================================
