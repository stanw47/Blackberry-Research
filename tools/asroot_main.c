/*
 * main.c
 *
 *  Created on: Mar 11, 2025
 *      Author: lc
 */
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include "procmgr.h"
#include <sys/neutrino.h>
//extern int procmgr_ability(pid_t __pid, unsigned __ability, ...);

#include <assert.h>
#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>

typedef enum
{
    STR2INT_SUCCESS, STR2INT_OVERFLOW, STR2INT_UNDERFLOW, STR2INT_INCONVERTIBLE
} str2int_errno;

/* Convert string s to int out.
 *
 * @param[out] out The converted int. Cannot be NULL.
 *
 * @param[in] s Input string to be converted.
 *
 *     The format is the same as strtol,
 *     except that the following are inconvertible:
 *
 *     - empty string
 *     - leading whitespace
 *     - any trailing characters that are not part of the number
 *
 *     Cannot be NULL.
 *
 * @param[in] base Base to interpret string in. Same range as strtol (2 to 36).
 *
 * @return Indicates if the operation succeeded, or why it failed.
 */
str2int_errno str2int(int *out, char *s, int base)
{
    char *end;
    if (s[0] == '\0' || isspace(s[0]))
        return STR2INT_INCONVERTIBLE;
    errno = 0;
    long l = strtol(s, &end, base);
    /* Both checks are needed because INT_MAX == LONG_MAX is possible. */
    if (l > INT_MAX || (errno == ERANGE && l == LONG_MAX))
        return STR2INT_OVERFLOW;
    if (l < INT_MIN || (errno == ERANGE && l == LONG_MIN))
        return STR2INT_UNDERFLOW;
    if (*end != '\0')
        return STR2INT_INCONVERTIBLE;
    *out = l;
    return STR2INT_SUCCESS;
}

int main(int argc, char** argv)
{

    uid_t uid = getuid();
    gid_t gid = getgid();
    pid_t pid = getpid();

    uid_t euid = geteuid();
    gid_t egid = getegid();

    printf("uid:%d euid:%d gid:%d egid:%d\n", getuid(), geteuid(), getgid(), getegid());
    if (argc > 1) {

        if (0 == stricmp(argv[1], "root")) {
            euid = 0;
            egid = 0;
        } else if (argc >= 3) {
            _INT32 tmp;
            if (str2int(&tmp, argv[1], 10) != STR2INT_SUCCESS) {
                euid = tmp;
            }
            if (str2int(&tmp, argv[2], 10) != STR2INT_SUCCESS) {
                egid = tmp;
            }
        }
    }

    int i, k, res;
    int plain[] = { PROCMGR_AID_SPAWN_SETUID, PROCMGR_AID_SPAWN_SETGID, PROCMGR_AID_SETUID,
    PROCMGR_AID_SETGID, PROCMGR_AID_GETID, PROCMGR_AID_PATHSPACE, PROCMGR_AID_REBOOT,
    PROCMGR_AID_CPUMODE,
    PROCMGR_AID_CONFSET, PROCMGR_AID_RSRCDBMGR, PROCMGR_AID_UMASK,
    PROCMGR_AID_MEM_SPECIAL,
    PROCMGR_AID_MEM_GLOBAL, PROCMGR_AID_SPAWN, PROCMGR_AID_FORK, PROCMGR_AID_V86,
    PROCMGR_AID_QNET, PROCMGR_AID_KEYDATA, PROCMGR_AID_IO, PROCMGR_AID_TRACE,
    PROCMGR_AID_CONNECTION, PROCMGR_AID_SCHEDULE, PROCMGR_AID_PATH_TRUST,
    PROCMGR_AID_SWAP,
    PROCMGR_AID_RCONSTRAINT, PROCMGR_AID_CHILD_NEWAPP, PROCMGR_AID_PUBLIC_CHANNEL,
    PROCMGR_AID_APS_ROOT,
    PROCMGR_AID_ABLE_CREATE, PROCMGR_AID_DEFAULT_TIMER_TOLERANCE };
    int range[] = {
    //PROCMGR_AID_SPAWN_SETUID, PROCMGR_AID_SPAWN_SETGID, PROCMGR_AID_SETUID, PROCMGR_AID_SETGID,
            PROCMGR_AID_RUNSTATE, PROCMGR_AID_SESSION, PROCMGR_AID_EVENT, PROCMGR_AID_RLIMIT,
            PROCMGR_AID_MEM_ADD, PROCMGR_AID_MEM_PHYS, PROCMGR_AID_MEM_PEER,
            PROCMGR_AID_MEM_LOCK,
            PROCMGR_AID_PROT_EXEC, PROCMGR_AID_WAIT, PROCMGR_AID_CLOCKSET,
            PROCMGR_AID_CLOCKPERIOD,
            PROCMGR_AID_INTERRUPT, PROCMGR_AID_PRIORITY, PROCMGR_AID_SIGNAL, PROCMGR_AID_TIMER,
            PROCMGR_AID_PGRP, PROCMGR_AID_MAP_FIXED, PROCMGR_AID_RUNSTATE_BURST };

    k = sizeof(plain) / 4;
    for (i = 0; i < k; i++) {
        res = procmgr_ability(pid,
        PROCMGR_ADN_NONROOT | PROCMGR_AOP_INHERIT_YES | PROCMGR_AOP_ALLOW | plain[i],
        PROCMGR_AID_EOL);
        if (!res)
            printf("%d set for all %X\n", plain[i], res);
    }

    k = sizeof(range) / 4;
    for (i = 0; i < k; i++) {
        res = procmgr_ability(pid,
                PROCMGR_ADN_NONROOT | PROCMGR_AOP_INHERIT_YES | PROCMGR_AOP_ALLOW
                        | PROCMGR_AOP_SUBRANGE | range[i], (_Uint64t) 0, ~(_Uint64t) 0,
                PROCMGR_AID_EOL);
        if (!res)
            printf("%d set for all %X\n", range[i], res);
    }

    setuid(euid);
    setgid(egid);

    setregid(egid, egid);
    setreuid(euid, euid);

    printf("uid:%d euid:%d gid:%d egid:%d\n", getuid(), geteuid(), getgid(), getegid());

    system("/bin/ksh");
    printf("Was uid:%d euid:%d gid:%d egid:%d\n", getuid(), geteuid(), getgid(), getegid());
    printf("Back to uid:%d gid:%d \n", uid, gid);

    return EXIT_SUCCESS;
}
