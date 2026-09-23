#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#include <dlfcn.h>
#include <execinfo.h>
#include <inttypes.h>
#include <limits.h>
#include <mpi.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

struct event
{
    char kind;
    uint64_t sequence;
    uint64_t enter_ns;
    uint64_t exit_ns;
};

enum { long_event_threshold_ns = 10000000, stack_depth = 24, request_history_capacity = 8192, datatype_cache_capacity = 16 };

struct long_event
{
    char kind;
    uint64_t sequence;
    uint64_t enter_ns;
    uint64_t exit_ns;
    int argument_count;
    int frame_count;
    void *frames[stack_depth];
};

struct request_issue
{
    MPI_Request request;
    MPI_Comm communicator;
    char kind;
    int peer;
    int tag;
    uint64_t bytes;
    uint64_t issued_ns;
};

struct wait_request_event
{
    uint64_t sequence;
    uint64_t wait_enter_ns;
    uint64_t wait_exit_ns;
    uint64_t issued_ns;
    uint64_t bytes;
    int request_index;
    int peer;
    int tag;
    int world_communicator;
    char kind;
};

struct datatype_size
{
    MPI_Datatype datatype;
    int size;
};

static struct event *events;
static size_t event_count;
static size_t event_capacity;
static uint64_t allreduce_count;
static uint64_t waitall_count;
static struct long_event *long_events;
static size_t long_event_count;
static size_t long_event_capacity;
static struct request_issue request_history[request_history_capacity];
static uint64_t request_issue_count;
static struct wait_request_event *wait_requests;
static size_t wait_request_count;
static size_t wait_request_capacity;
static struct datatype_size datatype_sizes[datatype_cache_capacity];
static size_t datatype_size_count;

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

static void append_long_event(char kind, uint64_t sequence, uint64_t enter_ns, uint64_t exit_ns, int argument_count)
{
    if (exit_ns < enter_ns || exit_ns - enter_ns < long_event_threshold_ns) return;
    if (long_event_count == long_event_capacity)
    {
        size_t capacity = long_event_capacity == 0 ? 32 : long_event_capacity * 2;
        struct long_event *replacement = realloc(long_events, capacity * sizeof(*long_events));
        if (replacement == NULL) _exit(125);
        long_events = replacement;
        long_event_capacity = capacity;
    }
    struct long_event *event = &long_events[long_event_count++];
    *event = (struct long_event){.kind = kind, .sequence = sequence, .enter_ns = enter_ns, .exit_ns = exit_ns, .argument_count = argument_count};
    event->frame_count = backtrace(event->frames, stack_depth);
}

static int datatype_bytes(MPI_Datatype datatype)
{
    for (size_t index = 0; index < datatype_size_count; index++)
    {
        if (datatype_sizes[index].datatype == datatype) return datatype_sizes[index].size;
    }
    int size;
    if (PMPI_Type_size(datatype, &size) != MPI_SUCCESS || size < 0) _exit(125);
    if (datatype_size_count < datatype_cache_capacity) datatype_sizes[datatype_size_count++] = (struct datatype_size){.datatype = datatype, .size = size};
    return size;
}

static void record_request(MPI_Request request, MPI_Comm communicator, char kind, int peer, int tag, int count, MPI_Datatype datatype)
{
    if (request == MPI_REQUEST_NULL) return;
    struct request_issue *issue = &request_history[request_issue_count % request_history_capacity];
    *issue = (struct request_issue){.request = request, .communicator = communicator, .kind = kind, .peer = peer, .tag = tag, .bytes = (uint64_t)count * (uint64_t)datatype_bytes(datatype), .issued_ns = now_ns()};
    request_issue_count++;
}

static const struct request_issue *find_request(MPI_Request request, uint64_t wait_enter_ns)
{
    uint64_t available = request_issue_count < request_history_capacity ? request_issue_count : request_history_capacity;
    for (uint64_t offset = 0; offset < available; offset++)
    {
        const struct request_issue *issue = &request_history[(request_issue_count - offset - 1) % request_history_capacity];
        if (issue->request == request && issue->issued_ns <= wait_enter_ns) return issue;
    }
    return NULL;
}

static void append_wait_request(uint64_t sequence, uint64_t enter_ns, uint64_t exit_ns, int request_index, MPI_Request request)
{
    if (wait_request_count == wait_request_capacity)
    {
        size_t capacity = wait_request_capacity == 0 ? 32 : wait_request_capacity * 2;
        struct wait_request_event *replacement = realloc(wait_requests, capacity * sizeof(*wait_requests));
        if (replacement == NULL) _exit(125);
        wait_requests = replacement;
        wait_request_capacity = capacity;
    }
    const struct request_issue *issue = request == MPI_REQUEST_NULL ? NULL : find_request(request, enter_ns);
    struct wait_request_event *event = &wait_requests[wait_request_count++];
    *event = (struct wait_request_event){.sequence = sequence, .wait_enter_ns = enter_ns, .wait_exit_ns = exit_ns, .request_index = request_index, .kind = request == MPI_REQUEST_NULL ? 'N' : 'U'};
    if (issue != NULL)
    {
        event->kind = issue->kind;
        event->peer = issue->peer;
        event->tag = issue->tag;
        event->bytes = issue->bytes;
        event->issued_ns = issue->issued_ns;
        event->world_communicator = issue->communicator == MPI_COMM_WORLD;
    }
}

int MPI_Isend(const void *buffer, int count, MPI_Datatype datatype, int destination, int tag, MPI_Comm communicator, MPI_Request *request)
{
    int status = PMPI_Isend(buffer, count, datatype, destination, tag, communicator, request);
    if (status == MPI_SUCCESS && request != NULL) record_request(*request, communicator, 'S', destination, tag, count, datatype);
    return status;
}

int MPI_Irecv(void *buffer, int count, MPI_Datatype datatype, int source, int tag, MPI_Comm communicator, MPI_Request *request)
{
    int status = PMPI_Irecv(buffer, count, datatype, source, tag, communicator, request);
    if (status == MPI_SUCCESS && request != NULL) record_request(*request, communicator, 'R', source, tag, count, datatype);
    return status;
}

int MPI_Allreduce(const void *sendbuf, void *recvbuf, int count, MPI_Datatype datatype, MPI_Op operation, MPI_Comm communicator)
{
    uint64_t sequence = ++allreduce_count;
    uint64_t enter_ns = now_ns();
    int status = PMPI_Allreduce(sendbuf, recvbuf, count, datatype, operation, communicator);
    uint64_t exit_ns = now_ns();
    append_event('A', sequence, enter_ns, exit_ns);
    append_long_event('A', sequence, enter_ns, exit_ns, count);
    return status;
}

int MPI_Waitall(int count, MPI_Request requests[], MPI_Status statuses[])
{
    uint64_t sequence = ++waitall_count;
    uint64_t enter_ns = now_ns();
    MPI_Request stack_requests[64];
    MPI_Request *original_requests = count > 64 ? malloc((size_t)count * sizeof(*original_requests)) : stack_requests;
    if (count > 64 && original_requests == NULL) _exit(125);
    for (int index = 0; index < count; index++) original_requests[index] = requests[index];
    int status = PMPI_Waitall(count, requests, statuses);
    uint64_t exit_ns = now_ns();
    append_event('W', sequence, enter_ns, exit_ns);
    append_long_event('W', sequence, enter_ns, exit_ns, count);
    if (exit_ns >= enter_ns && exit_ns - enter_ns >= long_event_threshold_ns)
    {
        for (int index = 0; index < count; index++) append_wait_request(sequence, enter_ns, exit_ns, index, original_requests[index]);
    }
    if (original_requests != stack_requests) free(original_requests);
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
    length = snprintf(path, sizeof(path), "%s/rank-%s-long.tsv", directory, rank);
    if (length < 0 || (size_t)length >= sizeof(path)) _exit(125);
    output = fopen(path, "w");
    if (output == NULL) _exit(125);
    fprintf(output, "kind\tsequence\tenter_realtime_ns\texit_realtime_ns\targument_count\tframe\tmodule\tmodule_offset_hex\tsymbol\tsymbol_offset_hex\n");
    for (size_t index = 0; index < long_event_count; index++)
    {
        const struct long_event *event = &long_events[index];
        for (int frame = 0; frame < event->frame_count; frame++)
        {
            Dl_info symbol = {0};
            void *address = event->frames[frame];
            if (dladdr(address, &symbol) == 0) continue;
            uintptr_t module_offset = (uintptr_t)address - (uintptr_t)symbol.dli_fbase;
            uintptr_t symbol_offset = symbol.dli_saddr == NULL ? 0 : (uintptr_t)address - (uintptr_t)symbol.dli_saddr;
            fprintf(output, "%c\t%" PRIu64 "\t%" PRIu64 "\t%" PRIu64 "\t%d\t%d\t%s\t%" PRIxPTR "\t%s\t%" PRIxPTR "\n", event->kind, event->sequence, event->enter_ns, event->exit_ns, event->argument_count, frame, symbol.dli_fname == NULL ? "" : symbol.dli_fname, module_offset, symbol.dli_sname == NULL ? "" : symbol.dli_sname, symbol_offset);
        }
    }
    if (fclose(output) != 0) _exit(125);
    length = snprintf(path, sizeof(path), "%s/rank-%s-requests.tsv", directory, rank);
    if (length < 0 || (size_t)length >= sizeof(path)) _exit(125);
    output = fopen(path, "w");
    if (output == NULL) _exit(125);
    fprintf(output, "wait_sequence\twait_enter_realtime_ns\twait_exit_realtime_ns\trequest_index\tkind\tpeer\ttag\tbytes\tissued_realtime_ns\tworld_communicator\n");
    for (size_t index = 0; index < wait_request_count; index++)
    {
        const struct wait_request_event *event = &wait_requests[index];
        fprintf(output, "%" PRIu64 "\t%" PRIu64 "\t%" PRIu64 "\t%d\t%c\t%d\t%d\t%" PRIu64 "\t%" PRIu64 "\t%d\n", event->sequence, event->wait_enter_ns, event->wait_exit_ns, event->request_index, event->kind, event->peer, event->tag, event->bytes, event->issued_ns, event->world_communicator);
    }
    if (fclose(output) != 0) _exit(125);
    free(events);
    free(long_events);
    free(wait_requests);
    return PMPI_Finalize();
}
