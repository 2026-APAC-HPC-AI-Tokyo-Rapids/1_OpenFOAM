#define _GNU_SOURCE

#include <errno.h>
#include <mpi.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

/* ASPIRE-2A: each node has 16 L3 groups (CCDs) with 8 physical cores each.
   Ranks are spread so that ASPIRE2A_RANKS_PER_L3 ranks share one L3; the
   default 8 equals one rank per physical core across all L3 groups, while a
   smaller value reserves cores per L3 to reduce cache overflow. */
#define ASPIRE2A_L3_GROUPS 16
#define ASPIRE2A_CORES_PER_L3 8

static long ranks_per_l3(void)
{
    const char *value = getenv("ASPIRE2A_RANKS_PER_L3");
    char *end = NULL;
    long parsed;

    if (value == NULL || *value == '\0')
    {
        return ASPIRE2A_CORES_PER_L3;
    }
    errno = 0;
    parsed = strtol(value, &end, 10);
    if (errno != 0 || end == value || *end != '\0' || parsed < 1 || parsed > ASPIRE2A_CORES_PER_L3)
    {
        fprintf(stderr, "invalid ASPIRE2A_RANKS_PER_L3: %s\n", value);
        _exit(126);
    }
    return parsed;
}

/* PALS can overwrite a prior affinity mask while UCX initializes MPI. */
static void bind_local_rank(void)
{
    const char *value = getenv("PMI_LOCAL_RANK");
    char *end = NULL;
    cpu_set_t mask;
    cpu_set_t observed;
    long rank;
    long per_l3 = ranks_per_l3();
    long cpu;

    if (value == NULL)
    {
        fputs("PMI_LOCAL_RANK is required after MPI initialization\n", stderr);
        _exit(126);
    }

    errno = 0;
    rank = strtol(value, &end, 10);
    if (errno != 0 || end == value || *end != '\0' || rank < 0 || rank >= CPU_SETSIZE)
    {
        fprintf(stderr, "invalid PMI_LOCAL_RANK: %s\n", value);
        _exit(126);
    }

    cpu = (rank / per_l3) * ASPIRE2A_CORES_PER_L3 + (rank % per_l3);
    if (cpu < 0 || cpu >= ASPIRE2A_L3_GROUPS * ASPIRE2A_CORES_PER_L3 * 2)
    {
        fprintf(stderr, "L3-aware CPU mapping is out of range for rank %s\n", value);
        _exit(126);
    }

    CPU_ZERO(&mask);
    CPU_SET((int)cpu, &mask);
    if (sched_setaffinity(0, sizeof(mask), &mask) != 0)
    {
        perror("sched_setaffinity");
        _exit(126);
    }
    if (sched_getaffinity(0, sizeof(observed), &observed) != 0)
    {
        perror("sched_getaffinity");
        _exit(126);
    }
    if (CPU_COUNT(&observed) != 1 || !CPU_ISSET((int)cpu, &observed))
    {
        fputs("MPI rank affinity verification failed\n", stderr);
        _exit(126);
    }
}

int MPI_Init(int *argc, char ***argv)
{
    int status = PMPI_Init(argc, argv);
    if (status == MPI_SUCCESS) bind_local_rank();
    return status;
}

int MPI_Init_thread(int *argc, char ***argv, int required, int *provided)
{
    int status = PMPI_Init_thread(argc, argv, required, provided);
    if (status == MPI_SUCCESS) bind_local_rank();
    return status;
}
