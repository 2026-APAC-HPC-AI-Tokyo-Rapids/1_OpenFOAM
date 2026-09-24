#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#include <dlfcn.h>
#include <errno.h>
#include <execinfo.h>
#include <inttypes.h>
#include <linux/perf_event.h>
#include <limits.h>
#include <mpi.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

struct event
{
    char kind;
    uint64_t sequence;
    uint64_t enter_ns;
    uint64_t exit_ns;
};

struct phase_event
{
    uint64_t at_ns;
    char phase[64];
    char field[64];
};

struct pmu_event
{
    uint64_t at_ns;
    uint64_t thread_cpu_ns;
    int group;
    uint64_t cycles;
    uint64_t local_l2_refills;
    uint64_t local_cache_refills;
    uint64_t local_dram_refills;
    uint64_t remote_dram_refills;
    uint64_t time_enabled;
    uint64_t time_running;
    long voluntary_switches;
    long involuntary_switches;
    char phase[64];
};

struct pmu_group_read
{
    uint64_t count;
    uint64_t time_enabled;
    uint64_t time_running;
    uint64_t values[3];
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
static struct phase_event *phase_events;
static size_t phase_event_count;
static size_t phase_event_capacity;
static struct pmu_event *pmu_events;
static size_t pmu_event_count;
static size_t pmu_event_capacity;
static int pmu_selected = -1;
static int pmu_group_fds[2] = {-1, -1};
static int pmu_member_fds[2][2] = {{-1, -1}, {-1, -1}};
static int pmu_active_group = -1;
static int pmu_iteration = -1;
static int pmu_available = -1;
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
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) _exit(125);
    return (uint64_t)value.tv_sec * 1000000000ULL + (uint64_t)value.tv_nsec;
}

static int selected_pmu_rank(void)
{
    if (pmu_selected >= 0) return pmu_selected;
    const char *rank_text = getenv("PMI_RANK");
    if (rank_text == NULL) _exit(125);
    char *end;
    long rank = strtol(rank_text, &end, 10);
    if (*end != '\0') _exit(125);
    // Early and late omega-Amul arrivals observed in the prior 10-iteration run.
    const int selected[] = {44, 102, 176, 208, 287, 349, 407, 494};
    pmu_selected = 0;
    for (size_t index = 0; index < sizeof(selected) / sizeof(selected[0]); index++)
    {
        if (rank == selected[index]) pmu_selected = 1;
    }
    return pmu_selected;
}

static int pmu_phase(const char *phase)
{
    const char *names[] =
    {
        "kOmegaSST.omegaDiv.begin", "kOmegaSST.omegaDiv.end",
        "omegaDiv.surfaceIntegrate.begin", "omegaDiv.surfaceIntegrate.end",
        "omegaDiv.gauss.begin", "omegaDiv.gauss.end",
        "omegaDiv.weights.begin", "omegaDiv.weights.end",
        "omegaDiv.matrixAlloc.begin", "omegaDiv.matrixAlloc.end",
        "omegaDiv.internalFaces.begin", "omegaDiv.internalFaces.end",
        "omegaDiv.negSumDiag.begin", "omegaDiv.negSumDiag.end",
        "omegaDiv.boundaryCoeffs.begin", "omegaDiv.boundaryCoeffs.end"
    };
    for (size_t index = 0; index < sizeof(names) / sizeof(names[0]); index++)
    {
        if (strcmp(phase, names[index]) == 0) return 1;
    }
    return 0;
}

static int open_pmu_event(uint32_t type, uint64_t config, int group_fd)
{
    struct perf_event_attr attributes = {0};
    attributes.type = type;
    attributes.size = sizeof(attributes);
    attributes.config = config;
    attributes.exclude_kernel = 1;
    attributes.exclude_hv = 1;
    attributes.disabled = group_fd == -1;
    attributes.read_format = PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING;
    return (int)syscall(__NR_perf_event_open, &attributes, 0, -1, group_fd, 0);
}

static void initialize_pmu(void)
{
    // Each group uses three counters. Run them in alternating iterations so
    // both groups can be scheduled even when six simultaneous events cannot.
    const uint64_t masks[2][2] = {{0x01, 0x02}, {0x08, 0x40}};
    for (size_t group = 0; group < 2; group++)
    {
        pmu_group_fds[group] = open_pmu_event(PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES, -1);
        if (pmu_group_fds[group] >= 0) pmu_member_fds[group][0] = open_pmu_event(PERF_TYPE_RAW, 0x43 | (masks[group][0] << 8), pmu_group_fds[group]);
        if (pmu_member_fds[group][0] >= 0) pmu_member_fds[group][1] = open_pmu_event(PERF_TYPE_RAW, 0x43 | (masks[group][1] << 8), pmu_group_fds[group]);
    }
    if (pmu_member_fds[0][1] >= 0 && pmu_member_fds[1][1] >= 0)
    {
        pmu_available = 1;
        return;
    }
    fprintf(stderr, "issue33 PMU unavailable for rank %s: %s\n", getenv("PMI_RANK"), strerror(errno));
    for (size_t group = 0; group < 2; group++)
    {
        if (pmu_group_fds[group] >= 0) close(pmu_group_fds[group]);
        for (size_t member = 0; member < 2; member++) if (pmu_member_fds[group][member] >= 0) close(pmu_member_fds[group][member]);
    }
    pmu_available = 0;
}

static void append_pmu_event(const char *phase, uint64_t at_ns)
{
    if (!selected_pmu_rank() || !pmu_phase(phase)) return;
    if (pmu_available == -1) initialize_pmu();
    if (strcmp(phase, "kOmegaSST.omegaDiv.begin") == 0)
    {
        pmu_iteration++;
        pmu_active_group = pmu_iteration % 2;
        if (pmu_available)
        {
            if (ioctl(pmu_group_fds[pmu_active_group], PERF_EVENT_IOC_RESET, PERF_IOC_FLAG_GROUP) != 0) _exit(125);
            if (ioctl(pmu_group_fds[pmu_active_group], PERF_EVENT_IOC_ENABLE, PERF_IOC_FLAG_GROUP) != 0) _exit(125);
        }
    }
    if (pmu_active_group < 0) _exit(125);
    if (pmu_event_count == pmu_event_capacity)
    {
        size_t capacity = pmu_event_capacity == 0 ? 256 : pmu_event_capacity * 2;
        struct pmu_event *replacement = realloc(pmu_events, capacity * sizeof(*replacement));
        if (replacement == NULL) _exit(125);
        pmu_events = replacement;
        pmu_event_capacity = capacity;
    }
    struct pmu_event *event = &pmu_events[pmu_event_count++];
    *event = (struct pmu_event){.at_ns = at_ns, .group = pmu_active_group};
    if (snprintf(event->phase, sizeof(event->phase), "%s", phase) >= (int)sizeof(event->phase)) _exit(125);
    struct timespec thread_time;
    if (clock_gettime(CLOCK_THREAD_CPUTIME_ID, &thread_time) != 0) _exit(125);
    event->thread_cpu_ns = (uint64_t)thread_time.tv_sec * 1000000000ULL + (uint64_t)thread_time.tv_nsec;
    struct rusage usage;
    if (getrusage(RUSAGE_THREAD, &usage) != 0) _exit(125);
    event->voluntary_switches = usage.ru_nvcsw;
    event->involuntary_switches = usage.ru_nivcsw;
    if (pmu_available)
    {
        struct pmu_group_read counters;
        if (read(pmu_group_fds[pmu_active_group], &counters, sizeof(counters)) != sizeof(counters) || counters.count != 3) _exit(125);
        event->time_enabled = counters.time_enabled;
        event->time_running = counters.time_running;
        event->cycles = counters.values[0];
        if (pmu_active_group == 0)
        {
            event->local_l2_refills = counters.values[1];
            event->local_cache_refills = counters.values[2];
        }
        else
        {
            event->local_dram_refills = counters.values[1];
            event->remote_dram_refills = counters.values[2];
        }
    }
    if (strcmp(phase, "kOmegaSST.omegaDiv.end") == 0 && pmu_available)
    {
        if (ioctl(pmu_group_fds[pmu_active_group], PERF_EVENT_IOC_DISABLE, PERF_IOC_FLAG_GROUP) != 0) _exit(125);
    }
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

void openfoam_issue33_phase_marker(const char *phase, const char *field)
{
    uint64_t at_ns = now_ns();
    if (phase == NULL) _exit(125);
    if (phase_event_count == phase_event_capacity)
    {
        size_t capacity = phase_event_capacity == 0 ? 256 : phase_event_capacity * 2;
        struct phase_event *replacement = realloc(phase_events, capacity * sizeof(*replacement));
        if (replacement == NULL) _exit(125);
        phase_events = replacement;
        phase_event_capacity = capacity;
    }
    struct phase_event *event = &phase_events[phase_event_count++];
    event->at_ns = at_ns;
    if (snprintf(event->phase, sizeof(event->phase), "%s", phase) >= (int)sizeof(event->phase)) _exit(125);
    if (snprintf(event->field, sizeof(event->field), "%s", field == NULL ? "" : field) >= (int)sizeof(event->field)) _exit(125);
    append_pmu_event(phase, at_ns);
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
    fprintf(output, "kind,sequence,enter_monotonic_ns,exit_monotonic_ns\n");
    for (size_t index = 0; index < event_count; index++)
    {
        const struct event *event = &events[index];
        fprintf(output, "%c,%" PRIu64 ",%" PRIu64 ",%" PRIu64 "\n", event->kind, event->sequence, event->enter_ns, event->exit_ns);
    }
    if (fclose(output) != 0) _exit(125);
    if (pmu_selected == 1)
    {
        length = snprintf(path, sizeof(path), "%s/rank-%s-pmu.tsv", directory, rank);
        if (length < 0 || (size_t)length >= sizeof(path)) _exit(125);
        output = fopen(path, "w");
        if (output == NULL) _exit(125);
        fprintf(output, "phase\tat_monotonic_ns\tthread_cpu_ns\tgroup\tcycles\tlocal_l2_refills\tlocal_cache_refills\tlocal_dram_refills\tremote_dram_refills\ttime_enabled\ttime_running\tvoluntary_switches\tinvoluntary_switches\n");
        for (size_t index = 0; index < pmu_event_count; index++)
        {
            const struct pmu_event *event = &pmu_events[index];
            fprintf(output, "%s\t%" PRIu64 "\t%" PRIu64 "\t%d\t%" PRIu64 "\t", event->phase, event->at_ns, event->thread_cpu_ns, event->group, event->cycles);
            fprintf(output, "%" PRIu64 "\t%" PRIu64 "\t%" PRIu64 "\t%" PRIu64 "\t%" PRIu64 "\t%" PRIu64 "\t%ld\t%ld\n", event->local_l2_refills, event->local_cache_refills, event->local_dram_refills, event->remote_dram_refills, event->time_enabled, event->time_running, event->voluntary_switches, event->involuntary_switches);
        }
        if (fclose(output) != 0) _exit(125);
    }
    length = snprintf(path, sizeof(path), "%s/rank-%s-phases.tsv", directory, rank);
    if (length < 0 || (size_t)length >= sizeof(path)) _exit(125);
    output = fopen(path, "w");
    if (output == NULL) _exit(125);
    fprintf(output, "phase\tfield\tat_monotonic_ns\n");
    for (size_t index = 0; index < phase_event_count; index++)
    {
        const struct phase_event *event = &phase_events[index];
        fprintf(output, "%s\t%s\t%" PRIu64 "\n", event->phase, event->field, event->at_ns);
    }
    if (fclose(output) != 0) _exit(125);
    length = snprintf(path, sizeof(path), "%s/rank-%s-long.tsv", directory, rank);
    if (length < 0 || (size_t)length >= sizeof(path)) _exit(125);
    output = fopen(path, "w");
    if (output == NULL) _exit(125);
    fprintf(output, "kind\tsequence\tenter_monotonic_ns\texit_monotonic_ns\targument_count\tframe\tmodule\tmodule_offset_hex\tsymbol\tsymbol_offset_hex\n");
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
    fprintf(output, "wait_sequence\twait_enter_monotonic_ns\twait_exit_monotonic_ns\trequest_index\tkind\tpeer\ttag\tbytes\tissued_monotonic_ns\tworld_communicator\n");
    for (size_t index = 0; index < wait_request_count; index++)
    {
        const struct wait_request_event *event = &wait_requests[index];
        fprintf(output, "%" PRIu64 "\t%" PRIu64 "\t%" PRIu64 "\t%d\t%c\t%d\t%d\t%" PRIu64 "\t%" PRIu64 "\t%d\n", event->sequence, event->wait_enter_ns, event->wait_exit_ns, event->request_index, event->kind, event->peer, event->tag, event->bytes, event->issued_ns, event->world_communicator);
    }
    if (fclose(output) != 0) _exit(125);
    free(events);
    free(phase_events);
    free(pmu_events);
    for (size_t group = 0; group < 2; group++)
    {
        if (pmu_group_fds[group] >= 0) close(pmu_group_fds[group]);
        for (size_t member = 0; member < 2; member++) if (pmu_member_fds[group][member] >= 0) close(pmu_member_fds[group][member]);
    }
    free(long_events);
    free(wait_requests);
    return PMPI_Finalize();
}
