/*
 * unlock_path_trust.c
 *
 *  Created on:  Feb 07, 2026
 *      Author: lc
 */
#include "procmgr.h"
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/debug.h>
#include <sys/mman.h>
#include <sys/neutrino.h>
#include <sys/procfs.h>
#include <sys/procmsg.h>
#include <sys/syspage.h>
#include <sys/iofunc.h>
#include <sys/dispatch.h>
#include <process.h>
#include <unistd.h>
#include <getopt.h>


#pragma pack(push, 1)
typedef struct
{
  uint16_t cmd;      /* 0x73 */
  uint16_t flags;    /* r0 */
  uint32_t pid;      /* r1 */
  uint32_t dev;      /* r2 */
  uint32_t zero0;    /* 0 */
  uint64_t ino;      /* (r8:r9) */
  uint8_t  pad[16];  /* \u0434\u043e 0x28 */
} trustpath_msg_t;
#pragma pack(pop)

static int trustpath_msg(uint16_t flags, uint32_t pid, uint32_t dev, uint64_t ino)
{
  trustpath_msg_t msg;
  uint32_t reply = 0;

  memset(&msg, 0, sizeof(msg));

  msg.cmd   = 0x73;
  msg.flags = flags;
  msg.pid   = pid;
  msg.dev   = dev;
  msg.zero0 = 0;
  msg.ino   = ino;

  if (MsgSendnc(0x40000000, &msg, sizeof(msg), &reply, 0) == -1)
    return -1;

  return 0;
}

int trust(const char * path, uint16_t flags)
{
  int exit_code;
  int fd = open64(path, 0);
  if (fd < 0)
  {
    fprintf(stderr, "open for '%s' failed: %d\n", path, errno);
    return(2);
  }

  struct stat64 st;
  if (fstat64(fd, &st) < 0)
  {
    fprintf(stderr, "fstat for '%s' failed: %d\n", path, errno);
    close(fd);
    return(2);
  }

  struct _server_info si;
  memset(&si, 0, sizeof(si));

  if (ConnectServerInfo(0, fd, &si) < 0)
  {
    fprintf(stderr, "ConnectServerInfo for '%s' failed: %d\n", path, errno);
    close(fd);
    return(2);
  }

  uint32_t pid = (uint32_t)si.pid;
  uint32_t dev = (uint32_t)st.st_dev;
  uint64_t ino = (uint64_t)st.st_ino;

  int rc = trustpath_msg(flags, pid, dev, ino);

  if (rc >= 0)
    errno = 0;

  if (errno == 0)
  {
    printf("'%s': trusted\n", path);
  }
  else if (errno == 1)
  {
    if (exit_code == 0)
      exit_code = 1;

    printf("'%s': untrusted\n", path);
  }
  else
  {
    printf("'%s': failure(%d)\n", path, errno);
    exit_code = 2;
  }

  close(fd);
  return exit_code;
}


#define MAX_SEGMENTS 1024
#define MAX_THREADS 512

int clear_list = 0;

void dump_procfs_map_info(int fd, int pid)
{
  // fetch information about the memory regions for this pid
  procfs_mapinfo *membufs;
  procfs_status my_status, old_status;

  int threads_count = 0;
  procfs_greg my_greg;

  int size, j;

  int nmembuf;
  int sts;
  int res;
  int target = 0;
  int new_sp, new_ip;
  unsigned char *xbuff;

  membufs = malloc(sizeof(procfs_mapinfo) * MAX_SEGMENTS);
  if (!membufs)
  {
    printf("membufs alloc error");
    exit(1);
  }

  //printf("DCMD_PROC_MAPINFO\n");
  sts = devctl(fd, DCMD_PROC_MAPINFO, membufs,
               sizeof(procfs_mapinfo) * MAX_SEGMENTS, &nmembuf);
  if (sts != EOK)
  {
    fprintf(stderr, "DCMD_PROC_MAPINFO process %d, error %d (%s)\n", pid, sts,
            strerror(sts));
    exit(EXIT_FAILURE);
  }
  //printf("PAGEDATA ok (%d)\n", nmembuf);

  // check to see we haven't overflowed
  if (nmembuf > MAX_SEGMENTS)
  {
    fprintf(stderr, "proc %d has > %d memsegs (%d)!!!\n", pid, MAX_SEGMENTS,
            nmembuf);
    exit(EXIT_FAILURE);
  }

  if (2 != nmembuf) {
    printf("something wrong with procnto\n");
    exit(EXIT_FAILURE);
  }

  _Uint64t base_c = membufs[0].vaddr;
  _Uint64t data_launcher = membufs[1].vaddr;

  uint32_t launcher_base = data_launcher;

  printf("Check status\n");

  //uint8_t ;
  uint32_t trust_head, trust_locked;
  off_t addr = (off_t)(launcher_base + 0x9CC0);
  off_t addr1 = (off_t)(launcher_base + 0x9CC4);

  res = pread(fd, &trust_locked, sizeof(trust_locked), addr);
  if (res != sizeof(trust_locked)) {
    printf("pread res=%d errno=%d (%s)\n", res, errno, strerror(errno));
    return;
  }
  printf("Current state: %s\n", trust_locked?"locked":"unlocked");
  if (trust_locked) {
    trust_locked = 0;
    printf("Clear LOCKED\n");
    res = pwrite(fd, &trust_locked, sizeof(trust_locked), addr);
    if (res != sizeof(trust_locked)) {
      perror("pwrite");
    }
    res = pread(fd, &trust_locked, sizeof(trust_locked), addr);
    if (res != sizeof(trust_locked)) {
      printf("pread res=%d errno=%d (%s)\n", res, errno, strerror(errno));
      return;
    }
    printf("Current state: %s\n", trust_locked?"locked":"unlocked");
  }
  if (clear_list) {
    printf("Dropping current pathtrust list\n");
    res = pread(fd, &trust_head, sizeof(trust_head), addr1);
    if (res != sizeof(trust_head)) {
      printf("pread res=%d errno=%d (%s)\n", res, errno, strerror(errno));
      return;
    }
    printf("last node: %08x\n", trust_head);
    trust_head = 0;
    res = pwrite(fd, &trust_head, sizeof(trust_head), addr1);
    if (res != sizeof(trust_head)) {
      perror("pwrite");
    }
    res = pread(fd, &trust_head, sizeof(trust_head), addr1);
    if (res != sizeof(trust_head)) {
      printf("pread res=%d errno=%d (%s)\n", res, errno, strerror(errno));
      return;
    }
    printf("last_node: %08x\n", trust_head);
    printf("Creating own pathtrust list\n");
    trust("/proc/boot", 0);
    trust("/base", 0);
    trust("/radio", 0);
    trust("/", 0);
  }
  printf("Done!\n");
}

void iterate_process(int pid)
{
  char paths[PATH_MAX];
  int fd;

  sprintf(paths, "/proc/%d/as", pid);

  if ((fd = open64(paths, O_RDWR)) == -1)
  {
    printf("Can't open '%s' for RW!\n", paths);
    return;
  }
  dump_procfs_map_info(fd, pid);
  close(fd);
}


int main(int argc, char **argv)
{
  char c;
  while ((c = getopt(argc, argv, "c")) != -1) {
    switch (c) {
      case 'c':
        clear_list = 1;
    }
  }

  iterate_process(1);

  return EXIT_SUCCESS;
}
