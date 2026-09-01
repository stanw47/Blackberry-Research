#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <vector>
#include <string>

#define ELFINFO_MAGIC_SIZE (16)

typedef struct
{
  uint8_t  e_ident[ELFINFO_MAGIC_SIZE]; /* Magic number and other info   */
  uint16_t e_type;                /* Object file type                    */
  uint16_t e_machine;             /* Architecture                        */
  uint32_t e_version;             /* Object file version                 */
  uint32_t e_entry;               /* Entry point virtual address         */
  uint32_t e_phoff;               /* Program header table file offset    */
  uint32_t e_shoff;               /* Section header table file offset    */
  uint32_t e_flags;               /* Processor-specific flags            */
  uint16_t e_ehsize;              /* ELF header size in bytes            */
  uint16_t e_phentsize;           /* Program header table entry size     */
  uint16_t e_phnum;               /* Program header table entry count    */
  uint16_t e_shentsize;           /* Section header table entry size     */
  uint16_t e_shnum;               /* Section header table entry count    */
  uint16_t e_shstrndx;            /* Section header string table index   */
} Elf32_Ehdr;

#define MI_PBT_ELF_PT_NULL    0
#define MI_PBT_ELF_PT_LOAD    1
#define MI_PBT_ELF_PT_DYNAMIC 2
#define MI_PBT_ELF_PT_INTERP  3
#define MI_PBT_ELF_PT_NOTE    4
#define MI_PBT_ELF_PT_SHLIB   5
#define MI_PBT_ELF_PT_PHDR    6
#define MI_PBT_ELF_TLS        7

typedef struct
{
  uint32_t p_type;                   /* Segment type */
  uint32_t p_offset;                 /* Segment file offset */
  uint32_t p_vaddr;                  /* Segment virtual address */
  uint32_t p_paddr;                  /* Segment physical address */
  uint32_t p_filesz;                 /* Segment size in file */
  uint32_t p_memsz;                  /* Segment size in memory */
  uint32_t p_flags;                  /* Segment flags */
  uint32_t p_align;                  /* Segment alignment */
} Elf32_Phdr;

struct program_info
{
	uint32_t addr;
	std::string data;
};

std::vector<program_info> program_list;

int generate_elf(std::string filename)
{
	FILE *f = fopen(filename.c_str(), "wb");
	if (!f)
	{
		printf("Failed to open %s\n", filename.c_str());
		return -1;
	}
	
	Elf32_Ehdr ehdr;
	memset(&ehdr, 0, sizeof(ehdr));
	ehdr.e_ident[0] = 0x7f;
	ehdr.e_ident[1] = 'E';
	ehdr.e_ident[2] = 'L';
	ehdr.e_ident[3] = 'F';
	ehdr.e_ident[4] = 1;
	ehdr.e_ident[5] = 1;
	ehdr.e_ident[6] = 1;
	ehdr.e_type = 2;
	ehdr.e_machine = 0x28;
	ehdr.e_version = 1;
	ehdr.e_entry = 0xFE800000;
	ehdr.e_phoff = sizeof(ehdr);
	ehdr.e_ehsize = sizeof(ehdr);
	ehdr.e_phentsize = sizeof(Elf32_Phdr);
	ehdr.e_phnum = program_list.size();
	fwrite(&ehdr, 1, sizeof(ehdr), f);
	
	uint32_t offset = sizeof(Elf32_Ehdr) + sizeof(Elf32_Phdr) * ehdr.e_phnum;
	
	for (program_info &pi : program_list)
	{
		Elf32_Phdr phdr;
		memset(&phdr, 0, sizeof(phdr));
		phdr.p_type = MI_PBT_ELF_PT_LOAD;
		phdr.p_offset = offset;
		phdr.p_vaddr = phdr.p_paddr = pi.addr;
		phdr.p_filesz = phdr.p_memsz = pi.data.size();
		fwrite(&phdr, 1, sizeof(phdr), f);
		
		offset += phdr.p_filesz;
	}
	
	for (program_info &pi : program_list)
	{
		fwrite(pi.data.data(), 1, pi.data.size(), f);
	}
	
	fclose(f);

	return 0;
}

void add_arr(uint32_t addr, void *value, uint32_t size)
{
	struct program_info pi;
	pi.addr = addr;
	pi.data = std::string((char *) value, size);
	program_list.push_back(pi);
}

void add_str(uint32_t addr, std::string value)
{
	struct program_info pi;
	pi.addr = addr;
	pi.data = value;
	program_list.push_back(pi);
}

void add_int(uint32_t addr, uint32_t value)
{
	struct program_info pi;
	pi.addr = addr;
	pi.data = std::string((char *) &value, sizeof(value));
	program_list.push_back(pi);
}

int main(int argc, char ** argv)
{
	if (argc != 4)
	{
		printf("Usage: %s <rpm> <apps> <output>\n", argv[0]);
		return -1;
	}

	// Load RPM
	{
		FILE *fp = fopen(argv[1], "rb");
		if (!fp)
		{
			printf("Failed to open %s\n", argv[1]);
			return -1;
		}
		fseek(fp, 0, SEEK_END);
		std::string data;
		data.resize(ftell(fp));
		fseek(fp, 0, SEEK_SET);
		fread(data.data(), 1, data.size(), fp);
		fclose(fp);

		add_str(0xFC100080, data);
	}

	uint8_t trambuline[8];
	*(uint32_t *)trambuline = 0xE51FF004;
	*(uint32_t *)&trambuline[4] = 0xFE820000;
	add_arr(0xFE800000, trambuline, sizeof(trambuline));

	// Load APPS PBL replacement
	{
		FILE *fp = fopen(argv[2], "rb");
		if (!fp)
		{
			printf("Failed to open %s\n", argv[1]);
			return -1;
		}
		fseek(fp, 0, SEEK_END);
		std::string data;
		data.resize(ftell(fp));
		fseek(fp, 0, SEEK_SET);
		fread(data.data(), 1, data.size(), fp);
		fclose(fp);

		add_str(0xFE820000, data);
	}

	// Start RPM
	add_int(0xFC10000C, 0x100080);
	add_int(0xFC100008, 0xA4CD7EA2);
	
	return generate_elf(argv[3]);
}
