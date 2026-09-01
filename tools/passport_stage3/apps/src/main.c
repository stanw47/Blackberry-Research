#include <stdint.h>
#include <string.h>

void *memzero(void * ptr, size_t num);

#define RPM_APPS_STATUS_MAGIC (*(volatile uint32_t *) 0xFC100008)

#define pbl_err_data_init() ((void (*)()) 0xFC01B46C)()
#define pbl_misc_data_init() ((void (*)()) 0xFC015E48)()
#define pbl_init_tmr() ((void (*)()) 0xFC017C48)()
#define pbl_sbl_shared_data_init() ((void (*)()) 0xFC017F9C)()
#define pbl_tmr_get_timestamp() ((uint32_t (*)()) 0xFC01B2BC)()
#define pbl_record_timestamp(val) ((void (*)(uint32_t)) 0xFC01495C)(val)
#define pbl_recoverable_error_handler(file, line, err) ((void (*)(const char *, int, int)) 0xFC015E70)(file, line, err)

#define sub_FC020D10() ((void (*)()) 0xFC020D10)()

#define dword_FE800000 ((uint32_t *) 0xFE800000)
#define dword_FE804000 ((uint32_t *) 0xFE804000)

#define pbl_configure_l3_page_table(idx, start, size, flags) ((uint32_t (*)(uint32_t, uint32_t, uint32_t, uint32_t)) 0xFC017AE0)(idx, start, size, flags)
#define mmu_update(idx) ((void (*)(uint32_t)) 0xFC0103F4)(idx)
#define mmu_configure_and_enable() ((void (*)()) 0xFC010714)()
#define sub_FC0105E4(a1, a2, a3, a4) ((void (*)(uint32_t, uint32_t, uint32_t, uint32_t)) 0xFC0105E4)(a1, a2, a3, a4)
#define mmu_enable_instruction_cache() ((void (*)()) 0xFC010370)()

#define pbl_sdcc_init(state, idx) ((int (*)(struct pbl_state_type *, uint32_t)) 0xFC016768)(state, idx)
#define pbl_flash_sdcc_parse_gpt(sdc, start, buf, len) ((struct gpt_header *(*)(struct pbl_flash_sdc_type *, uint32_t, struct gpt_entry *, uint32_t)) 0xFC01DAEC)(sdc, start, buf, len)
#define pbl_flash_sdcc_populate_flash_struct(state, sbl1_found, type) ((int (*)(struct pbl_state_type *, int, int)) 0xFC016664)(state, sbl1_found, type)

#define g_flash ((struct pbl_flash_type *) 0xF80022D4)
#define g_state ((struct pbl_state_type *) 0xFC106AE8)

#define pbl_state_init (int (*)(struct pbl_state_type *)) 0xFC01B220
#define pbl_cold_boot_hw_init (int (*)(struct pbl_state_type *)) 0xFC015BA8
#define pbl_unk (int (*)(struct pbl_state_type *)) 0xFC018020
#define pbl_data_init (int (*)(struct pbl_state_type *)) 0xFC015D54
#define pbl_load_sbl (int (*)(struct pbl_state_type *)) 0xFC017CE4
#define pbl_populate_share_data (int (*)(struct pbl_state_type *)) 0xFC01805C

static uint8_t sbl1_uuid[] = { 0x2C, 0xBA, 0xA0, 0xDE, 0xDD, 0xCB, 0x05, 0x48, 0xB4, 0xF9, 0xF4, 0x28, 0x25, 0x1C, 0x3E, 0x99 };

struct sbl_header_type
{
	uint32_t  codeword;            /* Codeword/magic number defining flash type
		                  information. */
	uint32_t  magic;               /* Magic number */
	uint32_t  RESERVED_0;          /* RESERVED */
	uint32_t  RESERVED_1;          /* RESERVED */
	uint32_t  RESERVED_2;          /* RESERVED */
	uint32_t  image_src;             /* Location of RPM_SBL in flash or e-hostdl in RAM. This is given in
		                  byte offset from beginning of flash/RAM.  */
	uint8_t  *image_dest_ptr;        /* Pointer to location to store RPM_SBL/e-hostdl in RAM.
		                  Also, entry point at which execution begins.
		                  */
	uint32_t  image_size;      /* Size of RPM_SBL image in bytes */
	uint32_t  code_size;       /* Size of code region in RPM_SBL image in bytes */
	uint8_t  *signature_ptr;         /* Pointer to images attestation signature */
	uint32_t  signature_size;        /* Size of the attestation signature in
		                  bytes */
	uint8_t  *cert_chain_ptr;  /* Pointer to the chain of attestation
		                  certificates associated with the image. */
	uint32_t  cert_chain_size; /* Size of the attestation chain in bytes */

	uint32_t  oem_root_cert_sel;  /* Root certificate to use for authentication.
		                 Only used if SECURE_BOOT1 table_sel fuse is
		                 OEM_TABLE. 1 indicates the first root
		                 certificate in the chain should be used, etc */
	uint32_t  oem_num_root_certs; /* Number of root certificates in image.
		                 Only used if SECURE_BOOT1 table_sel fuse is
		                 OEM_TABLE. Denotes the number of certificates
		                 OEM has provisioned                          */
	  
	uint32_t  RESERVED_5;          /* RESERVED */
	uint32_t  RESERVED_6;          /* RESERVED */
	uint32_t  RESERVED_7;          /* RESERVED */
	uint32_t  RESERVED_8;          /* RESERVED */
	uint32_t  RESERVED_9;          /* RESERVED */
};

struct pbl_shared_data_type
{
	uint32_t pbl_version;
	uint32_t *pbl_page_tbl_base;
	uint32_t pbl_page_tbl_size;
	uint8_t  *boot_stack_base;
	uint32_t boot_stack_size;

	uint8_t  *shared_section_base;
	uint32_t shared_section_size;

	uint32_t pbl_enter_timestamp;
	uint32_t pbl_exit_timestamp;

	/* Apps proc clock speed set up in PBL */
	uint32_t proc_clk_speed;

	/*boot_flash_shared_dev_info_type*/ void *flash_shared_data;

	/*pbl_secboot_shared_info_type*/ void *secboot_shared_data;

	struct sbl_header_type *sbl_hdr;

	uint32_t *pbl_indirect_vec_tbl_base;

	/*boot_rpm_apps_shared_data_type*/ void  *rpm_apps_shared_data;
};

struct pbl_sdcc_gpt_info
{
	uint32_t is_gpt_parti;
	uint32_t is_primary_table;
	uint64_t starting_lba;
	uint64_t ending_lba;
};

struct pbl_flash_sdc_type
{
	uint32_t card_type;
	uint32_t card_state;
	uint32_t resp0;
	uint32_t hw_status;
	uint32_t rca;
	uint32_t block_len;
	uint32_t block_len_shft;
	uint32_t block_mode;
	uint32_t spec_vers;
	uint32_t phy_parti_size;
	uint32_t mclk;
	uint32_t port;
	uint32_t data_width;
	void *hw_regs;
	uint32_t sbl1_found;
	uint32_t field_60;
	uint32_t boot_cfg;
	struct pbl_sdcc_gpt_info *gpt_info;
};

struct pbl_flash_type
{
	uint32_t type;
	uint32_t CS_base;
	uint32_t data_width;
	uint32_t ctrl_type;
	uint32_t data_width_shift;
	uint32_t field_14;
	uint32_t read;
	uint32_t get_mbn_header;
	uint32_t populate_shared_data;
	struct pbl_flash_sdc_type sdc;
};

struct pbl_state_type
{
	int proc_clk_speed;
	int boot_device;
	int buffer_start;
	int buffer_end;
	int pbl_entry_timestamp;
	struct sbl_header_type *sbl_hdr;
	void (* sbl1_entry)(struct pbl_shared_data_type *);
	struct pbl_flash_type *flash;
	int field_20;
	/*rpm_apps_shared_data_type*/ void *rpm_apps_shared_data;
	struct pbl_shared_data_type *pbl_shared_data;
	int boot_mode;
	int field_30;
	int cache_init;
};

struct gpt_header
{
	char signature[8];
	uint32_t revision;
	uint32_t hdr_size;
	uint32_t hdr_crc;
	uint32_t reserved;
	uint64_t hdr_lba;
	uint64_t backup_lba;
	uint64_t first_lba;
	uint64_t last_lba;
	uint8_t disk_uuid[16];
	uint64_t ptable_lba;
	uint32_t entries_cnt;
	uint32_t entry_size;
	uint32_t ptable_crc;
};

struct gpt_entry
{
	uint8_t type_uuid[16];
	uint8_t part_uuid[16];
	uint64_t first_lba;
	uint64_t last_lba;
	uint64_t flags;
	int16_t name[36];
};

int pbl_cache_init(struct pbl_state_type *state)
{
	memzero(dword_FE800000, 0x4000);
	memzero(dword_FE804000, 0x1000);

	for (int i = 0xF81; i < 0x1000; ++i)
		dword_FE800000[i] = (i << 20) | 0xC16;

	pbl_configure_l3_page_table(0, 0xFC010000, 0x20000, 0x33A);
	pbl_configure_l3_page_table(1, 0xF8000000, 0x70000, 0x17B);
	pbl_configure_l3_page_table(1, 0xF8004000, 0x6C000, 0x17A);
	pbl_configure_l3_page_table(2, 0xFE800000, 0x40000, /*0x73*/ 0x17A);
	pbl_configure_l3_page_table(3, 0xFC100000, 0x20000, 0x73);

	dword_FE800000[0xFC0] = ((uint32_t) dword_FE804000 & 0xFFFFFC02) | 1;
	dword_FE800000[0xFE8] = (0xFE804800 & 0xFFFFFC02) | 1;
	dword_FE800000[0xFC1] = (0xFE804C00 & 0xFFFFFC02) | 1;
	dword_FE800000[0xF80] = (0xFE804400 & 0xFFFFFC02) | 9;

	mmu_configure_and_enable();

	sub_FC0105E4(0xF8000000, 0x70000, 0xFE803E00, (0xFE804400 & 0xFFFFFC02) | 9);

	state->cache_init = 1;

	return 0;
}

int pbl_detect_bootable_media(struct pbl_state_type *state)
{
	state->boot_mode = 0;
	state->boot_device = 2;
	
	return 0;
}

int pbl_flash_sdcc_find_sbl1(struct pbl_flash_sdc_type *sdc, struct gpt_entry *entries, uint32_t entries_len)
{
	struct gpt_header *gpt_header = pbl_flash_sdcc_parse_gpt(sdc, 1, entries, entries_len);
	if (!gpt_header)
		return -1;
	
	for (int i = 0; i < gpt_header->entries_cnt; i++)
	{
		struct gpt_entry *entry = &entries[i];
		
		if (memcmp(entry->type_uuid, sbl1_uuid, sizeof(sbl1_uuid)) == 0)
		{
			sdc->gpt_info->starting_lba = entry->first_lba;
			sdc->gpt_info->ending_lba = entry->last_lba;
			return entry->first_lba;
		}
	}
	
	return -1;
}

int pbl_init_boot_device(struct pbl_state_type *state)
{
	state->flash = g_flash;

	int ret = pbl_sdcc_init(state, 0);
	if (ret != 3)
		pbl_recoverable_error_handler("./apps/pbl_flash.c", 130, ret | 0x10600);

	int sbl1_found = pbl_flash_sdcc_find_sbl1(&state->flash->sdc, (struct gpt_entry *) state->buffer_start, ((state->buffer_end - state->buffer_start) >> 2) + 1);
	if (sbl1_found == -1)
		return -1;

	pbl_record_timestamp(0x5D1600);
	if (pbl_flash_sdcc_populate_flash_struct(state, sbl1_found, 5) != 3)
		pbl_recoverable_error_handler("./apps/pbl_flash.c", 130, ret | 0x10600);

	return 0;
}

int pbl_authenticate_sbl(struct pbl_state_type *state)
{
	state->sbl1_entry = (void (*)(struct pbl_shared_data_type *)) state->sbl_hdr->image_dest_ptr;

	return 0;
}

int post_exploit_fixup(struct pbl_state_type *state)
{
	mmu_update(pbl_configure_l3_page_table(2, 0xFE800000, 0x40000, 0x73));
	
	return 0;
}

int (*apps_main_procs[])(struct pbl_state_type *) =
{
	pbl_state_init,
	pbl_cold_boot_hw_init,
	pbl_cache_init,
	pbl_unk,
	pbl_data_init, 
	pbl_detect_bootable_media,
	pbl_init_boot_device,
	pbl_load_sbl,
	pbl_authenticate_sbl,
	pbl_populate_share_data, 
	post_exploit_fixup,
};

#define PMIC_ARB_CHNL0_CMD (*(volatile uint32_t *) 0xFC4CF800)
#define PMIC_ARB_CHNL0_STATUS (*(volatile uint32_t *) 0xFC4CF808)
#define PMIC_ARB_CHNL0_WDATA0 (*(volatile uint32_t *) 0xFC4CF810)
#define PMIC_ARB_CHNL0_RDATA0 (*(volatile uint32_t *) 0xFC4CF818)

void pmic_write(uint32_t addr, uint32_t value)
{
	PMIC_ARB_CHNL0_WDATA0 = value;
	PMIC_ARB_CHNL0_CMD = addr << 4;
	while (!PMIC_ARB_CHNL0_STATUS);
}

uint32_t pmic_read(uint32_t addr)
{
	PMIC_ARB_CHNL0_CMD = (1 << 27) | (addr << 4);
	while (!PMIC_ARB_CHNL0_STATUS);
	return PMIC_ARB_CHNL0_RDATA0;
}

void stage2_main()
{
	// Let the RPM know that we are ready!
	RPM_APPS_STATUS_MAGIC = 0;
	
	// disable led
	pmic_write(0x1D046, 0);

	sub_FC020D10();
	mmu_enable_instruction_cache();

	pbl_err_data_init();
	pbl_misc_data_init();
	pbl_init_tmr();
	pbl_sbl_shared_data_init();
	g_state->pbl_entry_timestamp = pbl_tmr_get_timestamp();

	for (int i = 0; i < sizeof(apps_main_procs) / sizeof(apps_main_procs[0]); i++)
	{
		int (*ptr)(struct pbl_state_type *) = apps_main_procs[i];
		int ret = 0;
		if (ptr)
		{
			ret = ptr(g_state);
			pbl_record_timestamp(i | 0x10800);
		}

		if (ret)
			pbl_recoverable_error_handler("./apps/pbl_mc.c", 0x1B1, ret);
	}

	if (!g_state->sbl1_entry)
		pbl_recoverable_error_handler("./apps/pbl_mc.c", 0x1B4, 0x10100);

	g_state->sbl1_entry(g_state->pbl_shared_data);
	
	while(1);
}

int memcmp(const void *a, const void *b, size_t size)
{
	int ret = 0;
	for (int i = 0; i < size; i++)
		ret |= ((uint8_t *)a)[i] ^ ((uint8_t *)b)[i];
	return ret;
}
