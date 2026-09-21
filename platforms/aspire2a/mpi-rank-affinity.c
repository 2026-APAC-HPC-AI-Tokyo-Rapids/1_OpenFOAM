#define _GNU_SOURCE

#include <errno.h>
#include <mpi.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

/* PALS can overwrite a prior affinity mask while UCX initializes MPI. */
static void bind_local_rank(int required)
{
    const char *value = getenv("PMI_LOCAL_RANK");
    char *end = NULL;
    cpu_set_t mask;
    long cpu;

    if (value == NULL)
    {
        if (required)
        {
            fputs("PMI_LOCAL_RANK is required after MPI initialization\n", stderr);
            _exit(126);
        }
        return;
    }

    errno = 0;
    cpu = strtol(value, &end, 10);
    if (errno != 0 || end == value || *end != '\0' || cpu < 0 || cpu >= CPU_SETSIZE)
    {
        fprintf(stderr, "invalid PMI_LOCAL_RANK: %s\n", value);
        _exit(126);
    }

    CPU_ZERO(&mask);
    CPU_SET((int)cpu, &mask);
    if (sched_setaffinity(0, sizeof(mask), &mask) != 0)
    {
        perror("sched_setaffinity");
        _exit(126);
    }
}

__attribute__((constructor)) static void bind_at_load(void)
{
    bind_local_rank(0);
}

int MPI_Init(int *argc, char ***argv)
{
    int status = PMPI_Init(argc, argv);
    if (status == MPI_SUCCESS) bind_local_rank(1);
    return status;
}

int MPI_Init_thread(int *argc, char ***argv, int required, int *provided)
{
    int status = PMPI_Init_thread(argc, argv, required, provided);
    if (status == MPI_SUCCESS) bind_local_rank(1);
    return status;
}
