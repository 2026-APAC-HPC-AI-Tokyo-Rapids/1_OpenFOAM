#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <mpi.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

struct event
{
    char kind;
    uint64_t sequence;
    uint64_t enter_ns;
    uint64_t exit_ns;
};

static struct event *events;
static size_t event_count;
static size_t event_capacity;
static uint64_t allreduce_count;
static uint64_t waitall_count;

static uint64_t now_ns(void)
{
    struct timespec value;
    if (clock_gettime(CLOCK_REALTIME, &value) != 0) _exit(125);
    return (uint64_t)value.tv_sec * 1000000000ULL + (uint64_t)value.tv_nsec;
}

static void append_event(char kind, uint64_t sequence, uint64_t enter_ns, uint64_t exit_ns)
{
    if (event_count == event_capacity)
    {
        size_t capacity = event_capacity == 0 ? 256 : event_capacity * 2;
        struct event *replacement = realloc(events, capacity * sizeof(*events));
        if (replacement == NULL) _exit(125);
        events = replacement;
        event_capacity = capacity;
    }
    events[event_count++] = (struct event){.kind = kind, .sequence = sequence, .enter_ns = enter_ns, .exit_ns = exit_ns};
}

int MPI_Allreduce(const void *sendbuf, void *recvbuf, int count, MPI_Datatype datatype, MPI_Op operation, MPI_Comm communicator)
{
    uint64_t sequence = ++allreduce_count;
    uint64_t enter_ns = now_ns();
    int status = PMPI_Allreduce(sendbuf, recvbuf, count, datatype, operation, communicator);
    append_event('A', sequence, enter_ns, now_ns());
    return status;
}

int MPI_Waitall(int count, MPI_Request requests[], MPI_Status statuses[])
{
    uint64_t sequence = ++waitall_count;
    uint64_t enter_ns = now_ns();
    int status = PMPI_Waitall(count, requests, statuses);
    append_event('W', sequence, enter_ns, now_ns());
    return status;
}

int MPI_Finalize(void)
{
    const char *directory = getenv("MPI_TIMING_DIR");
    const char *rank = getenv("PMI_RANK");
    char path[PATH_MAX];
    FILE *output;
    if (directory == NULL || rank == NULL) _exit(125);
    int length = snprintf(path, sizeof(path), "%s/rank-%s.csv", directory, rank);
    if (length < 0 || (size_t)length >= sizeof(path)) _exit(125);
    output = fopen(path, "w");
    if (output == NULL) _exit(125);
    fprintf(output, "kind,sequence,enter_realtime_ns,exit_realtime_ns\n");
    for (size_t index = 0; index < event_count; index++)
    {
        const struct event *event = &events[index];
        fprintf(output, "%c,%" PRIu64 ",%" PRIu64 ",%" PRIu64 "\n", event->kind, event->sequence, event->enter_ns, event->exit_ns);
    }
    if (fclose(output) != 0) _exit(125);
    free(events);
    return PMPI_Finalize();
}
