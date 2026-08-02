#include "vtuneTaskTrace.H"

#include <ittnotify.h>

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <limits>
#include <iterator>
#include <mutex>
#include <string>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>
#include <vector>

namespace
{

using Foam::vtuneTaskKind;

constexpr const char* processLifetimeName = "OpenFOAM process lifetime";

constexpr const char* taskNames[] =
{
    "Foam::GaussSeidelSmoother::smooth",
    "Foam::fv::cellLimitedGrad::calcGrad",
    "Foam::lduMatrix::residual",
    "Foam::lduMatrix::Amul",
    "Foam::fv::gaussGrad::gradf",
    "Foam::linearUpwindV::correction"
};

static_assert
(
    sizeof(taskNames)/sizeof(taskNames[0])
 == static_cast<std::size_t>(vtuneTaskKind::linearUpwindVCorrection) + 1
);


std::uint64_t monotonicRawNs() noexcept
{
    timespec value{};
    if (::clock_gettime(CLOCK_MONOTONIC_RAW, &value) != 0)
    {
        return 0;
    }
    return
        static_cast<std::uint64_t>(value.tv_sec)*1'000'000'000ULL
      + static_cast<std::uint64_t>(value.tv_nsec);
}


long currentThreadId() noexcept
{
    return static_cast<long>(::syscall(SYS_gettid));
}


std::size_t configuredEventLimit() noexcept
{
    constexpr std::size_t defaultLimit = 1'000'000;
    const char* value = std::getenv("OPENFOAM_TASK_TRACE_MAX_EVENTS");
    if (!value || !*value)
    {
        return defaultLimit;
    }

    errno = 0;
    char* end = nullptr;
    const unsigned long long parsed = std::strtoull(value, &end, 10);
    if
    (
        errno
     || end == value
     || *end
     || parsed == 0
     || parsed > std::numeric_limits<std::size_t>::max()
    )
    {
        return defaultLimit;
    }
    return static_cast<std::size_t>(parsed);
}


struct Event
{
    vtuneTaskKind kind;
    std::uint64_t startNs;
    std::uint64_t endNs;
    long threadId;
};


class Recorder
{
    std::string path_;
    std::uint64_t processStartNs_;
    std::uint64_t processEndNs_;
    pid_t processId_;
    long mainThreadId_;
    std::size_t eventLimit_;
    std::atomic_size_t droppedEvents_;
    std::vector<Event> events_;
    std::mutex mutex_;
    __itt_domain* domain_;
    __itt_string_handle* handles_[sizeof(taskNames)/sizeof(taskNames[0])];

    void writeCsv() noexcept
    {
        if (path_.empty())
        {
            return;
        }

        std::FILE* output = std::fopen(path_.c_str(), "w");
        if (!output)
        {
            std::fprintf
            (
                stderr,
                "OpenFOAM VTune task trace: cannot open %s: %s\n",
                path_.c_str(),
                std::strerror(errno)
            );
            return;
        }

        std::fprintf
        (
            output,
            "name,start_tsc.CLOCK_MONOTONIC_RAW,end_tsc,pid,tid\n"
        );
        std::fprintf
        (
            output,
            "%s,%llu,%llu,%ld,%ld\n",
            processLifetimeName,
            static_cast<unsigned long long>(processStartNs_),
            static_cast<unsigned long long>(processEndNs_),
            static_cast<long>(processId_),
            mainThreadId_
        );
        for (const Event& event : events_)
        {
            const std::size_t index = static_cast<std::size_t>(event.kind);
            std::fprintf
            (
                output,
                "%s,%llu,%llu,%ld,%ld\n",
                taskNames[index],
                static_cast<unsigned long long>(event.startNs),
                static_cast<unsigned long long>(event.endNs),
                static_cast<long>(processId_),
                event.threadId
            );
        }
        const std::size_t dropped = droppedEvents_.load();
        if (dropped)
        {
            std::fprintf
            (
                output,
                "OpenFOAM dropped task events=%zu,%llu,%llu,%ld,%ld\n",
                dropped,
                static_cast<unsigned long long>(processEndNs_),
                static_cast<unsigned long long>(processEndNs_),
                static_cast<long>(processId_),
                mainThreadId_
            );
            std::fprintf
            (
                stderr,
                "OpenFOAM VTune task trace: dropped %zu events after limit %zu\n",
                dropped,
                eventLimit_
            );
        }
        if (std::fclose(output) != 0)
        {
            std::fprintf
            (
                stderr,
                "OpenFOAM VTune task trace: cannot close %s: %s\n",
                path_.c_str(),
                std::strerror(errno)
            );
        }
    }

public:

    Recorder() noexcept
    :
        processStartNs_(monotonicRawNs()),
        processEndNs_(processStartNs_),
        processId_(::getpid()),
        mainThreadId_(currentThreadId()),
        eventLimit_(configuredEventLimit()),
        droppedEvents_(0),
        domain_(nullptr),
        handles_{}
    {
        const char* path = std::getenv("OPENFOAM_TASK_TRACE_PATH");
        if (!path || !*path)
        {
            return;
        }

        try
        {
            path_ = path;
            events_.reserve(std::min<std::size_t>(eventLimit_, 65'536));
        }
        catch (...)
        {
            path_.clear();
            return;
        }

        domain_ = __itt_domain_create("OpenFOAM");
        for (std::size_t index = 0; index < std::size(handles_); ++index)
        {
            handles_[index] = __itt_string_handle_create(taskNames[index]);
        }
    }

    ~Recorder() noexcept
    {
        processEndNs_ = monotonicRawNs();
        writeCsv();
    }

    bool active() const noexcept
    {
        return !path_.empty();
    }

    void begin(const vtuneTaskKind kind) noexcept
    {
        if (!domain_)
        {
            return;
        }
        const std::size_t index = static_cast<std::size_t>(kind);
        __itt_task_begin(domain_, __itt_null, __itt_null, handles_[index]);
    }

    void end
    (
        const vtuneTaskKind kind,
        const std::uint64_t startNs,
        const std::uint64_t endNs,
        const long threadId
    ) noexcept
    {
        if (domain_)
        {
            __itt_task_end(domain_);
        }
        try
        {
            std::lock_guard<std::mutex> guard(mutex_);
            if (events_.size() < eventLimit_)
            {
                events_.push_back(Event{kind, startNs, endNs, threadId});
            }
            else
            {
                ++droppedEvents_;
            }
        }
        catch (...)
        {
            ++droppedEvents_;
        }
    }
};


Recorder recorder;

} // End anonymous namespace


Foam::vtuneTaskScope::vtuneTaskScope(const vtuneTaskKind kind) noexcept
:
    kind_(kind),
    startNs_(0),
    threadId_(0),
    active_(recorder.active())
{
    if (active_)
    {
        startNs_ = monotonicRawNs();
        threadId_ = currentThreadId();
        recorder.begin(kind_);
    }
}


Foam::vtuneTaskScope::~vtuneTaskScope() noexcept
{
    if (active_)
    {
        recorder.end(kind_, startNs_, monotonicRawNs(), threadId_);
    }
}
