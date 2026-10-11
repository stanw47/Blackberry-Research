# Cross-device: Bootloader crack catalog & KEYone overlap map

Running catalog of documented bootloader "unlocks that shouldn't have happened",
grouped by mechanism, plus the BlackBerry model/kernel map and the overlap
analysis that points at the remaining KEYone directions.

Sources: public CVEs, conference talks, open-source tools (kibo, mtkclient,
xperable, checkm8, etc.), the wall-of-shame project, and our own device work
(hub device cards + per-device repos). KEY2 unlock specifics live in
`Blackberry-Key2_Research/docs/KEY2-unlock-mechanism.md` - not duplicated here.

---

## 1. Catalog by mechanism

### A. Signature-verification logic bugs

| # | Case | Platform | Mechanism |
|---|---|---|---|
| A1 | CVE-2014-4325 | Qualcomm LK `cmd_boot` | `fastboot boot` accepted arbitrary kernel image despite lock; defeated device-lock + kernel-signature checks (broad MSM). |
| A2 | CVE-2013-2598 | Qualcomm LK boot-image parser | Crafted load-destination header values let the image overwrite the signature-verification code in bootloader RAM. |
| A3 | **CVE-2021-1931** | Qualcomm **UEFI ABL** fastboot | Buffer overflow from unvalidated length in fastboot data path; ABL runs from RAM -> upload a patched copy of the running ABL. **SDM660 (KEY2/KEY2 LE), MSM8998/SDM845 (Sony Yoshino/Tama), Quest 1/2, most 64-bit SDMs (SDM765 not affected).** Fixed in edk2 `0727b7b0` / SoCVersion 2021-07-05. |
| A4 | GBL / `efisp` (2025-26) | SD 8 Elite / 8E Gen 5 | Boot chain skipped signature verification for the Generic Bootloader; `efisp` write -> arbitrary code -> unlock (Xiaomi 17 series, POCO F8 Ultra). Patched Feb/Mar 2026. |
| A5 | CVE-2025-20892 | Samsung bootloader | Protection-mechanism failure allowing fastboot command execution (SMR Jan-2025). |
| A6 | SSTIC 2017 (F. Basse) | Samsung download mode | Odin/download-mode bug -> arbitrary code with physical access; defeated lockscreen/reactivation lock. |
| A7 | PBL Sahara (2022, C. Wade) | Qualcomm PBL | USB update path let signing-key hashes in RAM be overwritten -> Secure Boot bypass; most 64-bit SDMs. |
| A8 | Custom AVB keys | Google + few OEMs | Not a bug: user AVB keys let a custom OS boot with a *locked* bootloader. |
| A9 | CVE-2015-8888 | Qualcomm LK `aboot.c` | Integer overflow in sparse-image header (block count x block size), Nexus 5; fixed 1321f34f. |
| A10 | Qualcomm fastboot cmd 0-day (Jan 2026) | Qualcomm edk2 ABL | Command-line processing flaw in edk2 fastboot; "vast majority of Qualcomm SoCs" per XDA thread; used for Xiaomi 17 (SD 8 Gen 5) / POCO F8 Ultra unlocks alongside GBL/efisp (A4); reported to Qualcomm. |

### B. Memory corruption in boot stacks

| # | Case | Platform | Mechanism |
|---|---|---|---|
| B1 | MediaTek BROM "Kamakiri" (2019) | MTK BootROM | Stale USB TX buffer bytes + unbounded `wIndex` index into `if_info[].if_class_specific_hdlr` -> function-pointer hijack. Fire TV Stick 4K first; now mtkclient/Penumbra (kamakiri2/amonet/hashimoto). |
| B2 | fusee gelee (CVE-2018-6242) | NVIDIA Tegra X1 | RCM USB buffer overflow; unpatchable on early Switch units. |
| B3 | checkm8 (CVE-2019-8900) | Apple SecureROM | DFU use-after-free; unpatchable, A5-A11 (+ iPad 6/7, iPod 7); tethered; basis of checkra1n/palera1n. |
| B4 | usbliter8 (2026) | Apple A12/A13/S5 | BootROM exploit; requires RP2350 MCU. |
| B5 | "Carbonara" | Motorola MTK DA1 | DA memory corruption -> arbitrary code -> unlock (most pre-2024 Motorola MTK). |
| B6 | CVE-2022-38694 / 38691 / 38692 | Unisoc | Secure-boot bypass; modified + re-signed splloader/uboot; dm-verity disable via trustos. |
| B7 | Samsung SW REV bypass (A32, 2026) | MTK Samsung | Patch preloader + LK anti-rollback functions via mtkclient -> downgrade A13->A11 -> Odin unlock. |
| B8 | CVE-2018-9364 + `laf` era | LG download mode | "Special command" allowed partition modification (secure-boot bypass); earlier era: overwrite `laf` with fastboot-capable loader (L70/G4/V10). |
| B9 | EDLUnlock | Xiaomi MSM89xx | EDL-mode exploit path -> unlock (Mi A1 era). |
| B10 | Xiaomi EDL/Firehose engineering-ABL route | Xiaomi SDM8xx | Signed engineering ABL + EDL programmer -> downgrade to unlockable state (non-Kioxia UFS). |
| B11 | V35 engineering bootloader | LG G7/V35/V40 | Flashed a signed *engineering* ABL from a sibling model -> `fastboot oem unlock` works. Cross-model artifact reuse. |
| B12 | CVE-2017-8273 | Qualcomm LK fastboot | Buffer overflow in fastboot `boot` command path when verified boot is disabled (length > boot image buffer); all CAF 2017. |
| B13 | CVE-2018-5854 | Qualcomm LK fastboot | Stack-based buffer overflow in fastboot; all CAF Android/MSM releases (Code Aurora Jun 2018 bulletin). Same family as B12 - the recurring LK fastboot overflow class. |
| B14 | CVE-2017-15828 | Qualcomm LK keystore | Integer overflow accessing the LK keystore -> buffer overflow (fixed 86ea9e5d). |
| B15 | amonet (2019) | Fire HD 8 2018 (karnak) | Chain: MTK BootROM exploit + a LittleKernel bootloader exploit (xyzz); LK-side overflow -> unlock/downgrade. |
| B16 | CVE-2025-36907 | Qualcomm ABL | Heap buffer overflow via USB fastboot -> local EoP *after* unlock (user interaction); post-1931 ABL class keeps producing bugs. |

### C. Crypto & token flaws

| # | Case | Platform | Mechanism |
|---|---|---|---|
| C1 | PS3 ECDSA nonce reuse | Sony PS3 | Constant ECDSA `k` -> private key recovery -> self-signed `lv0`/metldr -> CFW. The canonical crypto crack. |
| C2 | Huawei unlock codes | Huawei/Honor | Code algorithm from IMEI+Luhn; after 2018 server shutdown: bruteforce (SkyEmi lineage) and paid readers (DC-Unlocker/HCU); testpoint modes + PotatoNV (Kirin 620-960). |
| C3 | US/Canada unlock tokens | Samsung | Paid token services (DID-derived); One UI 3.1 bootloader (Mar 2021) bypassed the token check outright until Apr 2023. |
| C4 | Pixel unlock token accident | Google | OTAConfigNoZeroTouchPrebuilt issued unlock tokens for Verizon-locked Pixel 1s for a few days -> permanent unlock. |
| C5 | Intel Boot Guard key leak | MSI (Binarly 2023) | Boot Guard *private* signing key shipped inside firmware images. |
| C6 | Leaked signed artifacts | Many OEMs | Samsung ENG boot images (Odin-flashable, no signature checks), Nokia engineering files, Xiaomi eng ABL, **BlackBerry Priv/Passport engineering-device bootloader**. |
| C7 | Motorola unlock-data format | Motorola CID | `fastboot oem get_unlock_data` returns `1A23457698214365`-style prefix + hex payload; `debug_token` virtual partition inside CID; server-side signing only, no public keygen. |

### D. Rollback / downgrade tricks

| # | Case | Platform | Mechanism |
|---|---|---|---|
| D1 | Motorola downgrade-to-unlock | Motorola (old) | Flash older bootloader with the unlock bug, unlock, upgrade. |
| D2 | Xiaomi engineering-ABL downgrade | Xiaomi | See B10. |
| D3 | One UI 3.1 token bypass | Samsung | Hold the old bootloader; never update (free unlock window). |
| D4 | Samsung binary-version equal downgrade | Samsung | Only same-revision downgrades; workaround = B7. |

### E. Testpoint / EDL / factory / debug modes

| # | Case | Platform | Mechanism |
|---|---|---|---|
| E1 | EDL + Firehose (Aleph 2018) | Qualcomm | EDL accepts signed loaders; per-device programmer leaks + the unlock section of that research turned EDL into a universal unlock path on many devices. |
| E2 | `debug_token` virtual partition | Motorola CID | Debug/flash capability token inside the CID partition (`mot_sec`). |
| E3 | CROM service / factory binaries | Samsung | China-variant CROM app unlocked officially; factory binaries via UART/JTAG. |
| E4 | HTC htcdev + S-OFF generations | HTC | moonshine/firewater/rumrunner/SunShine: S-OFF via hboot bugs + TrustZone exploits (beaups/jcase). |
| E5 | Google DFU / RCM / EDL | many | Debug/emergency modes outlive devices; the entry point for most bootrom-class cracks. |

### F. Hardware attacks

| # | Case | Platform | Mechanism |
|---|---|---|---|
| F1 | **Priv/Passport eMMC + engineering BL** | BlackBerry (RIM) | Desolder eMMC, flash engineering-device bootloader with a flasher (balika011 guide). Only known BlackBerry bootloader unlock path. |
| F2 | JTAG / RGH | Xbox 360 | SMC debug (JTAG hack) and reset-glitch (RGH) to skip boot signature checks; Xbox One voltage glitching reported 2021+. |
| F3 | limera1n / 24Kpwn / alloc8 / Pwnage | Apple (old) | BootROM USB exploits: A4, iPod touch 2, iPhone 3GS, iPhone 2G/3G. |
| F4 | blackbird / hardbird | Apple SEP | SEP firmware exploits (A8-A10 / A7) enabling downgrades (turdus merula). |
| F5 | glitching / EMFI / laser / chip-off | generic | Fault the signature check, read SPI/eMMC directly, or extract keys side-channel. |

### G. OS-root -> bootloader / TrustZone

| # | Case | Platform | Mechanism |
|---|---|---|---|
| G1 | HTC S-OFF via TrustZone exploit | HTC (SunShine) | Root exploit -> set S-OFF flag permanently. |
| G2 | root-then-flash (`dd aboot`) | many | If only *booting* is verified, root lets you rewrite the bootloader partitions (Samsung blocks via auto-relock). |
| G3 | enso | PS Vita | Kernel exploit -> patch `boot_config` persistently. |
| G4 | BootMii as boot2 | Nintendo Wii | boot1/boot2 verification weakness -> replacement boot2. |
| G5 | WPInternals | Windows Phone | Lumia UEFI Secure Boot policy bypass (test-signed/flashable EFIESP). |
| G6 | **Dan Rosenberg 2013 (CVE-2013-3051)** | Motorola MSM8960 | Kernel root -> crafted SMC 0x9/0x2 calls exploiting a TZ kernel arbitrary-write -> QFuse blow -> bootloader unlocked (Razr HD/M/Atrix HD). **The archetype of our KEYone plan: kernel root -> TZ -> persistent unlock state.** |
| G7 | bits-please "Unlocking the Motorola Bootloader" (2016) | Moto X 2nd Gen | TZ kernel code exec (CVE-2015-6639 class) -> lift restrictions on `tzbsp_qfprom_write_row` -> blow the unlock QFuse directly from a TrustZone exploit. |
| G8 | ALEPH-2017024 (2017) | Google Nexus 6 (shamu) | Root (CVE-2016-10277) + block-device writes -> invalidate the `sp` partition entry (HMAC'd by TEE) -> a **re-locked** bootloader reverts to unlocked. |
| G9 | Quadrooter (2016) | Qualcomm (all, incl. DTEK50/DTEK60) | 4-kernel-bug chain (CVE-2016-2503 ashmem, **CVE-2016-2504 KGSL UAF**, CVE-2016-2059, CVE-2016-5340); **DTEK50/DTEK60 shipped vulnerable** (reviews confirmed). Same KGSL driver family as the KEYone lane. |

### H. Shims & unlock-state forgery

| # | Case | Platform | Mechanism |
|---|---|---|---|
| H1 | kaeru + tanuki (2026) | MTK Motorola | Exploit installs a bootloader shim faking unlock state; passes Play Integrity; `fastboot oem bldr [on/off]`. |
| H2 | unlock-state spoofers | generic | Flip the OS-visible unlock flag without a real unlock (short-lived). |

---

## 2. BlackBerry model map (who made what)

| Device | Maker | SoC | Kernel (stock) | Bootloader | Known crack |
|---|---|---|---|---|---|
| BBOS 8700/9000s | RIM | ARM9/ARM11 | BBOS | proprietary | JavaLoader dumps; no unlock concept |
| Z10 / Q10 / Z30 / Classic / Passport (BB10) | RIM/BlackBerry | OMAP4470 / MSM8960 family | QNX | proprietary | Oleksandr modded-autoloader **root** (software); Passport: hardware eMMC + engineering BL (F1) |
| Priv (STV100-*) | RIM/BlackBerry | MSM8992 | 3.10.x | **LK + authboot (Mux protocol)** | F1 only (eMMC + engineering bootloader); session5: canary = SCM random w/ deterministic LCG fallback; nv_sig-response stack overflow present but canary-gated |
| DTEK50 (STH100-*) | TCL (Alcatel Idol 4S rebrand) | MSM8952 | 3.10.x | LK + authboot | none public; shipped Quadrooter-vulnerable (kernel lane) |
| DTEK60 (BBA100-*) | TCL (TCL 950 rebrand) | MSM8996 | 3.10/3.18 | LK + authboot | none public |
| **KEYone (BBB100-*)** | **TCL (global); Optiemus (India)** | **MSM8953** | **3.18.31-perf-gf38c8fb** | **LK + authboot (pcauthtool protocol)** | none; engineering units exist (unlocked BL); LK CVEs audited, not exposed (`lk-vs-abl.md`); KGSL kernel lane active (`notes/58`+)
| Motion (BBD100-*) | TCL | MSM8953 | 3.18.x | LK + authboot | none public |
| KEY2 (BBF100-*) | TCL | SDM660 | 4.4.78 -> Lineage 4.4.302 | **UEFI ABL** (ACQ160/ACI448) | **CVE-2021-1931 (kibo / Windows tool) -> FACTORY unlock + LineageOS 22.2**; XDA 2026 guide: flash ACQ160 TWICE (botched A/B), remove Google accounts first |
| KEY2 LE (BBE100-*) | TCL | SDM636 | 4.4.x | UEFI ABL (ACT575) | CVE-2021-1931 (LE path) |
| Evolve / Evolve X | Optiemus (India) | SD450/636 class | 4.x | LK/ABL mix | status unknown |

Key architectural fact: the Android-BlackBerry line splits at the SoC
generation - **LK (`emmc_appsboot.mbn`) on Priv/DTEK/KEYone/Motion, UEFI ABL
(`abl.elf`) on KEY2/LE** (`lk-vs-abl.md`). CVE-2021-1931 is ABL-only.

---

## 3. Kernel map + related CVEs

| Device | Kernel | Source | Root-relevant CVE families to mine |
|---|---|---|---|
| Priv | 3.10.x (msm-3.10) | BB published | KGSL old (CVE-2014-4322/4323 class), QSEE/TZ trustlet CVEs (Beniamini: CVE-2015-6639, CVE-2016-2431/2432/2433) |
| DTEK50/60 | 3.10/3.18 | BB published | same families |
| **KEYone** | **3.18.31 (msm-3.18)** | **ABY299 tree (this repo)** | **KGSL: CVE-2021-1905 (active lane), CVE-2019-10567, CVE-2020-11179, CVE-2023-33107 (blocked)**; TZ/QSEE trilogy; ashmem/pronto races |
| Motion | 3.18.x | BB published | same as KEYone |
| KEY2 / LE | 4.4.78+ (msm-4.4) | no clean GPL tree public | KGSL family; binder CVE-2019-2215 (4.4/4.9/4.14) |

Related CVEs outside the kernel that matter for the bootloader lane:

- **CVE-2021-1931** (ABL fastboot overflow) - KEY2 only; not KEYone (LK).
- **CVE-2013-2598 / CVE-2014-0973** (LK image parser/verify) - audited in
  BlackBerry LK builds; not exposed (`lk-vs-abl.md`).
- **QSEE/TZ trustlets** (CVE-2015-6639, CVE-2016-2431/2432/2433): TZ code exec
  -> keymaster/RPMB access; relevant because **BlackBerry stores bootmode in
  RPMB** (`notes/53`).
- **RPMB attacks** (replay/relay research; RPMB key from QFPROM): the bootmode
  record is the unlock state on BlackBerry; a TZ-capable primitive that writes
  RPMB records directly would sidestep authboot.
- **Qualcomm anti-rollback (ARB)**: SBL1 refuses older aboot (observed:
  AAN355 aboot refused on KEYone, `notes/51`) - any downgrade path needs
  same-or-newer ARB.

---

## 4. Overlap analysis -> targeted directions for the KEYone

What the catalog + our own work jointly say:

1. **FACTORY mode is the unlock state** (KEY2 proof: `switch_bootmode(1,0)`
   writes mode 1 to RPMB; `MODE: PRODUCT -> FACTORY`; stock OS then refuses to
   boot, requiring a modified boot image). Our `notes/53` found the same on
   KEYone: factory mode is the MFI gateway, stored in RPMB, but
   `oem set-factory-mode` is authboot-denied. The KEY2 needed RAM patching of
   the bootloader to call `switch_bootmode`; on the KEYone the equivalent
   write is behind **BTAS/RTAS-gated TZ services** (`authboot-rtas.md`).
   => The kernel-root lane (KGSL UAF, `notes/58`) is the way to reach those TZ
   services (mfgUtil/bcc/tctd) without a bootloader bug.
2. **Wipe defusal is mandatory** (KEY2: BbryWipeLib defused, or the
   factory transition wipes userdata). KEYone equivalent is `securewipe`
   (`BbryWipeLib` sibling) - our notes show it is *un-gated* and wipes the
   boot/recovery sig records. Any factory-mode transition must account for it.
3. **Authboot is not a wall for RAM-resident code** (KEY2 also had authboot;
   the overflow ran before/around the permission gate). On KEYone the
   equivalent would need an LK bug of the A1/A2 class - audited, not present.
   Keep enumerating LK fastboot/parser CVEs against ABL766 build tags
   (AAK399 -> ABL766) as a low-probability track.
4. **Engineering-device bootloader is the proven BlackBerry hardware path**
   (Priv/Passport F1). KEYone engineering units with unlocked bootloaders
   exist (XDA TWRP thread). If an engineering aboot/preloader image can be
   obtained, eMMC-level flashing on a retail KEYone is the same play - and
   ARB only rejects *older* versions, so a same-generation engineering build
   should flash.
5. **Sibling-artifact mining** (B11 pattern): DTEK50 = Alcatel Idol 4S,
   DTEK60 = TCL 950, KEYone = TCL design, Motion = same MSM8953 platform.
   Sibling LK/authboot builds (TCL/Alcatel/BB Merah Putih/Optiemus variants,
   Motion builds) are worth diffing for weaker gates or leaked engineering
   images.
6. **EDL** (`edl-firehose.md`): signed MSM8953 programmer exists in the
   KEYone autoloader; EDL adds raw partition access (persist/boot0/boot1)
   that fastboot authboot denies. Value depends on reaching EDL without
   testpoints and on the programmer's partition whitelist.

Ranked shortlist:

1. Finish KGSL UAF -> kernel root (`notes/58`) -> drive TZ services for
   RPMB bootmode FACTORY + wipe defusal. **Status 2026-10-11 night: the
   primitive "GPU write into a reclaimed page" is now reliable (19/23
   dangling rounds, alias buf #0; pressure-drain recipe) - the escalation
   step (reclaim as KGSL pagetable/ringbuffer, forge PTEs -> arbitrary phys)
   is the active frontier.**
2. Obtain/diff engineering-unit bootloader images (KEYone, Motion, sibling
   TCL builds); eMMC path if needed (Priv/Passport precedent).
3. Keep enumerating LK-era CVEs (fastboot command handling, partition
   parsers) against ABL766 with the existing instruction-level diff tooling.
4. EDL reachability + programmer whitelist check.
5. **Priv canary test** (new): drive the Priv's Mux auth channel
   (`cross-device/authboot-mux-protocol.md`, session 6 dispatcher decode)
   to a live canary-ladder on the nv_sig overflow; if the Priv's TZ RNG
   service is absent, the fallback LCG canary is deterministic -> first
   LK-generation bootloader unlock. Technique transfers to the KEYone only
   if a KEYone canary leak appears (its canary is TZ-random).

---

## 6. Extension: PBL / Sahara (bootrom) thread

The PBL (Primary Bootloader, in SoC ROM) exposes the Sahara/Firehose protocol
in EDL mode. Two public vulnerability generations:

- **2022 (C. Wade, QPSS "Breaking Mobile Bootloaders")**: during Sahara's
  chunked Loader upload, the PBL's stored **public-key hash (used to verify
  images) could be overwritten with pointers** -> Secure Boot bypass. "Most
  64-bit Snapdragon chips tested were vulnerable, SDM765 was not." The slides
  note "most low-level bootloaders don't support any patching, and will remain
  vulnerable" - i.e. shipped devices stay exposed. No CVE assigned; requires
  low-level PBL knowledge and EDL entry.
- **2026 (CVE-2026-25262, May 2026 bulletin)**: "Write-what-where Condition in
  Primary Bootloader - memory corruption while processing a crafted ELF file
  in the Primary Bootloader" (Boot, local, critical; SM8450-era research).
  Shows the class keeps recurring in new PBL generations.

MSM8953 applicability: the 2022 bug's scope is "most 64-bit Snapdragons" -
MSM8953 (2016) predates the fix and is a candidate, but **confirmation
requires a PBL dump**, which needs EDL (or glitching). Combined with the hub's
EDL findings (`edl-firehose.md`): the KEYone's EDL is **hardware-entry only**
(software EDL disabled), and a **signed MSM8953 firehose programmer exists**
(extracted from the ABL766 autoloader). So the full chain
`testpoints -> EDL -> PBL key-overwrite -> unsigned loader -> patched
bootloader` is plausible but gated by physical access. Recorded as the
highest-ceiling path if hardware access ever becomes available.

## 7. Extension: LK CVE enumeration (against ABL766)

Known Little Kernel (`emmc_appsboot.mbn`) CVEs to check against the KEYone
build tags (AAK399 -> AAL093 -> AAN355 -> ABL766):

| CVE | Class | Notes |
|---|---|---|
| CVE-2013-2598 | boot-image load-destination overwrite of sig-check code | audited; not exposed in BB builds (`lk-vs-abl.md`) |
| CVE-2014-0973 | `image_verify` stack overflow via crafted boot image | audited; not exposed |
| CVE-2014-4325 | `cmd_boot` fastboot bypass (boot arbitrary kernel) | authboot-gated on BB builds |
| CVE-2016-3850 | integer overflow in `aboot.c` header parsing (Nexus 5/5X/6P/7) - fixed in LK `030371d4` | BB builds carry the guard strings (our notes/50-52); 2018 diffs = refinement |

Also in the same family: the community "patched aboot" technique (flash an
aboot image with fastboot/oem-unlock enabled) - works only where SBL does not
verify aboot; **not applicable to KEYone** (SBL1 verifies aboot, and ARB
rejects older versions - observed, `notes/51`).

Recurring source to mine: Qualcomm monthly bulletins, "Boot" technology-area
entries (e.g. CVE-2023-33017 UEFI ListVars overflow; CVE-2026-25262 PBL;
CVE-2021-1931 ABL). MSM8953 alone has ~355 recorded CVEs (cvefeed), four
CISA-actively-exploited - worth a periodic sweep for kernel/firmware
primitives.

## 8. Extension: what the KEY2 patches map to on KEYone

| KEY2 (kibo patch) | What it defeats | KEYone equivalent (from our notes) |
|---|---|---|
| `switch_bootmode(1,0)` trigger | writes bootmode 1 (FACTORY) to RPMB | bootmode is RPMB-backed on KEYone too; `oem set-factory-mode` is authboot/BTAS-denied (`notes/53`) |
| `BbryWipeLib` defuse | factory-transition factory-wipe | `securewipe` (`BbryWipeLib` sibling) - un-gated, wipes boot/recovery sig records (observed live) |
| `BbryKeys` disable | BB key/attestation check | authboot token keys (`notes/49`) |
| "Flashing unlock is not allowed" patch | OEM unlock policy check | authboot whitelist + `flash` denials (all builds) |
| RTAS skip | RTAS/BTAS authorization | `getvarp` / `oem securewipe` / `debugtokens` BTAS gates (`authboot-rtas.md`) |
| Boot counter `0xffff` | factory-mode expiry | bootmode record expiry (RPMB) |

Conclusion: the KEY2 unlock is a RAM-patch of the *same architectural
components* we have already mapped on the KEYone - the difference is only that
the KEY2 had a bootloader memory-corruption bug (CVE-2021-1931) to run the
patches, while the KEYone must reach the same components through TZ services
after a kernel root, or through hardware (engineering bootloader / EDL).

## 9. Extension: MSM8953 TZ / QSEE CVE cluster (post-2018 gap)

KEYone patch level is **2018-12-05** (ABL766). SD625 is listed as affected on
several TZ-class CVEs published *after* that date, i.e. likely unpatched on
this device:

| CVE | Area | Description | Published |
|---|---|---|---|
| CVE-2017-18302 | TZ / QSEE | crafted HLOS client modifies a structure passed to a QSEE app between TOCTOU -> **arbitrary writes to TZ kernel memory** (SD 625 affected) | 2018-09 (patched by 2018-12?) |
| CVE-2017-18292 | TZ / Widevine | non-secure app can restart TZ via repeated Widevine app API calls | 2018-10 |
| CVE-2017-18124 | Secure boot | uint8-ptr addition overflow during secure boot | 2018-10 |
| CVE-2018-13910 | TZ | out-of-bounds access in TZ (invalid index checked against DDR); SD 625 affected | **2019-06** -> unpatched on 2018-12 device |
| CVE-2019-2274 | TZ / Core | improper access control for RPU write access from secure processor | **2019-12** -> unpatched |

Why it matters: BlackBerry stores bootmode (unlock state) in **RPMB**, written
through TZ/keymaster services. A TZ memory-corruption or access-control
primitive on the pre-2019 TZ firmware could write the RPMB bootmode record or
the wipe-defusal state directly - the same end state the KEY2 reached via
bootloader RAM patching. Check the shipped `tz.mbn` version in the ABL766
autoloader against the patch dates, then mine 2019-2021 Qualcomm "TZ Secure
OS" / "Boot" bulletin entries for MSM8953.

Sources to sweep: Qualcomm monthly bulletins (technology areas "Boot",
"TZ Secure OS", "Core"), Android security bulletins' Qualcomm closed-source
sections (2018-09 through 2021), and CVE databases filtered by MSM8953.

---

## 10. Bootloader stack-canary genealogy (what makes B-class bugs hard)

Most B-class (memory-corruption) bootloader exploits assume *no* stack
protection. Qualcomm's LK added stack protector support over time; the
BlackBerry LK builds ship it on. Measured facts from our builds:

| Generation | Build | Canary source | Determinism |
|---|---|---|---|
| KEYone ABL766 (2018) | LK ARM32 | `get_canary()` -> TZ SCM random ("scm_call for random failed !!!"); global guard cached once at boot | **Random per boot** (live oracle: low16 fixed 0x0054 by luck, high16 random) |
| Priv AAW068 (2016) | LK ARM32 | Same design: `init_canary()` -> SCM svc-0xa (two variants selected by a secure-canary probe flag); LCG fallback | SCM random, **but fallback LCG (`state*0x3039+0x11`) has NO seed write in the image -> BSS-zero start -> deterministic (0x11, 0x3284A, ...) if the 2016 TZ lacks the RNG service** (unverified live) |
| Stock CAF LK 2013-2015 | LK ARM32 | Often built WITHOUT stack protector at all (pre-2016 CAF branches) | n/a -> B1/B12/B13-class bugs fully exploitable |

Implications for the KEYone/Priv/Motion:
- The KEYone canary is TZ-random; the nv_sig overflow (`notes/60`) is
  canary-walled unless a canary leak primitive appears.
- The Priv canary is random **if and only if its TZ answers the SCM RNG
  call**; a live ladder probe on the Priv (fastboot PID 0fca:8030, Mux
  protocol) settles this. A deterministic Priv canary turns the
  Priv's nv_sig overflow (section 11) into a full ROP unlock.
- LG/older LK B8-era devices (G4/V10 laf) predate the hardened builds.

## 11. BlackBerry authboot attack surface (nv_sig + Mux + pcauthtool)

BlackBerry's LK builds add an authboot/RTAS layer (channel: `AUTHBOOT`,
`NVSIG`, `DBGSIG`, `DDT`, `STP` - one keyed blob per channel per carrier
variant) that gates fastboot commands and boot-image verification.

Two wire generations:

- **Mux protocol (Priv AAW068, DTEK era)**: `bbry/app/bbmux/mux.c` - USB
  channel mux with a Control Channel, channel registration/open, password
  challenge w/ attempt counting, encryption negotiation
  ("Host encryption version %d.%d not supported"), and RTAS ops dispatched
  by tool authorization (`rtas_init_tool_authorization`,
  `mux_msg_handler`). No 0xbba78701 cookie (that constant does not exist in
  the Priv image).
- **pcauthtool protocol (KEYone ABL766+)**: fixed cookie `0xbba78701`,
  code-dispatched frames (0x2000 handshake / 0x2003 password / 0x2005
  nv_sig response; 0x1000-0x1016 session codes), reversed from the leaked
  Priv-era `pcauthtool.exe` (`notes/59-60`). The auth interface is a
  separate USB interface (0FCA:8040 intf 1 on KEYone fastboot).

The shared weak point - the **nv_sig challenge-response verifier** - is a
stack overflow in both generations:

| Device | Function | Bug |
|---|---|---|
| KEYone ABL766 | `rtas_verify_nv_sig_response` @0x8f658f30 | `memcpy(sp+0x4c, blob+5, sl)` with unchecked ASN.1 length `sl=blob[4]` (blob `30 81 L 02 sl <data> 02 r4 <r4data>`); canary at buffer+0x88; saved PC at +0xb0. Live-proven canary oracle (`notes/60`). |
| Priv AAW068 | @0xf953e68 ("RTAS verify NV sig response") | Same ASN.1 parse, but with partial checks: total len u16 r6 (<=258 enforced via [2]==r6-3), payload byte sb<=253 checked only against r6 (`r6 >= sb+5`); stack buf 68 B, canary at +0x88, saved LR reachable with sb in 181..253. **Canary-gated unless the section-10 deterministic-fallback applies.** |

Exploitation endgame is identical in both: ROP -> `set_device_unlock` /
devinfo is_unlocked write + `write_device_info` (TZ/RPMB persist) + reboot,
with wipe defusal (`securewipe` / `BbryWipeLib` siblings are un-gated but
must not fire during the unlock transition).

---

## 5. References

- KEY2 unlock dissection: `Blackberry-Key2_Research/docs/KEY2-unlock-mechanism.md`
  (CVE-2021-1931, patch table, RPMB FACTORY persistence).
- KEY2 tool RE: `Blackberry-Key2_Research/docs/KEY2-unlock-tool-re.md`.
- Hub: `lk-vs-abl.md`, `authboot-rtas.md`, `edl-firehose.md`,
  `bbss-boot-wp.md`, `bb10-root-pathtrust.md`.
- Public: Qualcomm July 2021 bulletin (CVE-2021-1931); Wade, "Breaking Mobile
  Bootloaders" (QPSS 2022) and the SDM660 blog post; edk2 commit
  `0727b7b0d4cafb091397b76f75a3a4f66852a361`; j4nn/xperable; darknight1050
  Quest unlocker; BotchedRPR/kibo; wall-of-shame project.
