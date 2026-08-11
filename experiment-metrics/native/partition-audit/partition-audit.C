/*---------------------------------------------------------------------------*\
  Native v2 partition topology verifier.

  Processor meshes are deliberately opened one at a time.  The serial mesh is
  the source of truth; no OpenFOAM file is parsed outside OpenFOAM's readers.
\*---------------------------------------------------------------------------*/

#include "argList.H"
#include "Time.H"
#include "fvMesh.H"
#include "labelIOList.H"
#include "processorPolyPatch.H"
#include "bitSet.H"
#include "PackedList.H"
#include "OSspecific.H"
#include "OFstream.H"

#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <map>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

using namespace Foam;

#define AUDIT_CHECK(condition, message)                                      \
    do                                                                       \
    {                                                                        \
        if (!(condition))                                                    \
        {                                                                    \
            FatalErrorInFunction << message << nl << exit(FatalError);       \
        }                                                                    \
    } while (false)

namespace
{

struct Locator
{
    fileName path;
    std::uint64_t sizeBytes;
    std::string sha256;
};

struct SubdomainRecord
{
    label rank;
    label cellCount;
    std::array<Locator, 5> mesh;
    std::array<Locator, 4> addressing;
};

struct InterfaceState
{
    bool lowerSeen = false;
    bool upperSeen = false;
    label nFaces = -1;
    std::vector<label> lowerFaceIds;
};

class Sha256
{
    std::array<std::uint32_t, 8> state_
    {{
        0x6a09e667u, 0xbb67ae85u, 0x3c6ef372u, 0xa54ff53au,
        0x510e527fu, 0x9b05688cu, 0x1f83d9abu, 0x5be0cd19u
    }};
    std::array<unsigned char, 64> block_{};
    std::uint64_t totalBytes_ = 0;
    std::size_t blockSize_ = 0;

    static std::uint32_t rotateRight(const std::uint32_t value, const int bits)
    {
        return (value >> bits) | (value << (32 - bits));
    }

    void transform(const unsigned char* data)
    {
        static constexpr std::array<std::uint32_t, 64> constants
        {{
            0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u,
            0x3956c25bu, 0x59f111f1u, 0x923f82a4u, 0xab1c5ed5u,
            0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u,
            0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u,
            0xe49b69c1u, 0xefbe4786u, 0x0fc19dc6u, 0x240ca1ccu,
            0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
            0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u,
            0xc6e00bf3u, 0xd5a79147u, 0x06ca6351u, 0x14292967u,
            0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u,
            0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u,
            0xa2bfe8a1u, 0xa81a664bu, 0xc24b8b70u, 0xc76c51a3u,
            0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
            0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u,
            0x391c0cb3u, 0x4ed8aa4au, 0x5b9cca4fu, 0x682e6ff3u,
            0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u,
            0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u
        }};

        std::array<std::uint32_t, 64> schedule{};
        for (std::size_t i = 0; i < 16; ++i)
        {
            schedule[i] =
                (std::uint32_t(data[4*i]) << 24)
              | (std::uint32_t(data[4*i + 1]) << 16)
              | (std::uint32_t(data[4*i + 2]) << 8)
              | std::uint32_t(data[4*i + 3]);
        }
        for (std::size_t i = 16; i < schedule.size(); ++i)
        {
            const std::uint32_t s0 =
                rotateRight(schedule[i - 15], 7)
              ^ rotateRight(schedule[i - 15], 18)
              ^ (schedule[i - 15] >> 3);
            const std::uint32_t s1 =
                rotateRight(schedule[i - 2], 17)
              ^ rotateRight(schedule[i - 2], 19)
              ^ (schedule[i - 2] >> 10);
            schedule[i] = schedule[i - 16] + s0 + schedule[i - 7] + s1;
        }

        std::uint32_t a = state_[0];
        std::uint32_t b = state_[1];
        std::uint32_t c = state_[2];
        std::uint32_t d = state_[3];
        std::uint32_t e = state_[4];
        std::uint32_t f = state_[5];
        std::uint32_t g = state_[6];
        std::uint32_t h = state_[7];

        for (std::size_t i = 0; i < schedule.size(); ++i)
        {
            const std::uint32_t sum1 =
                rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
            const std::uint32_t choose = (e & f) ^ ((~e) & g);
            const std::uint32_t temp1 =
                h + sum1 + choose + constants[i] + schedule[i];
            const std::uint32_t sum0 =
                rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
            const std::uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
            const std::uint32_t temp2 = sum0 + majority;

            h = g;
            g = f;
            f = e;
            e = d + temp1;
            d = c;
            c = b;
            b = a;
            a = temp1 + temp2;
        }

        state_[0] += a;
        state_[1] += b;
        state_[2] += c;
        state_[3] += d;
        state_[4] += e;
        state_[5] += f;
        state_[6] += g;
        state_[7] += h;
    }

public:
    void update(const unsigned char* data, std::size_t size)
    {
        totalBytes_ += size;
        while (size)
        {
            const std::size_t count = std::min(size, block_.size() - blockSize_);
            std::copy(data, data + count, block_.begin() + blockSize_);
            blockSize_ += count;
            data += count;
            size -= count;
            if (blockSize_ == block_.size())
            {
                transform(block_.data());
                blockSize_ = 0;
            }
        }
    }

    std::string finish()
    {
        const std::uint64_t totalBits = totalBytes_ * 8u;
        block_[blockSize_++] = 0x80u;
        if (blockSize_ > 56)
        {
            std::fill(block_.begin() + blockSize_, block_.end(), 0u);
            transform(block_.data());
            blockSize_ = 0;
        }
        std::fill(block_.begin() + blockSize_, block_.begin() + 56, 0u);
        for (std::size_t i = 0; i < 8; ++i)
        {
            block_[63 - i] = static_cast<unsigned char>(totalBits >> (8*i));
        }
        transform(block_.data());

        std::ostringstream digest;
        digest << std::hex << std::setfill('0');
        for (const std::uint32_t word : state_)
        {
            digest << std::setw(8) << word;
        }
        return digest.str();
    }
};

std::string sha256File(const fileName& path)
{
    std::ifstream input(path.c_str(), std::ios::binary);
    AUDIT_CHECK(input.good(), "cannot open exact mesh file for SHA-256: " << path);

    Sha256 sha;
    std::array<unsigned char, 1024*1024> buffer{};
    while (input)
    {
        input.read
        (
            reinterpret_cast<char*>(buffer.data()),
            static_cast<std::streamsize>(buffer.size())
        );
        const std::streamsize count = input.gcount();
        if (count > 0)
        {
            sha.update(buffer.data(), static_cast<std::size_t>(count));
        }
    }
    AUDIT_CHECK(input.eof(), "error while hashing exact mesh file: " << path);
    return sha.finish();
}

Locator makeLocator(const fileName& casePath, const fileName& relativePath)
{
    const fileName fullPath(casePath/relativePath);
    AUDIT_CHECK
    (
        fullPath.type(false, false) == fileName::FILE,
        "required exact regular file is missing or is a symlink: " << relativePath
    );
    const off_t before = fileSize(fullPath, false);
    AUDIT_CHECK(before >= 0, "cannot stat exact mesh file: " << relativePath);
    const std::string digest = sha256File(fullPath);
    const off_t after = fileSize(fullPath, false);
    AUDIT_CHECK
    (
        after == before,
        "mesh file size changed while hashing: " << relativePath
    );
    return Locator
    {
        relativePath,
        static_cast<std::uint64_t>(before),
        digest
    };
}

bool parseProcessorRank(const fileName& entry, label& rank)
{
    const std::string name(entry);
    static const std::string prefix("processor");
    if (name.compare(0, prefix.size(), prefix) != 0)
    {
        return false;
    }
    const std::string digits(name.substr(prefix.size()));
    AUDIT_CHECK(!digits.empty(), "invalid processor directory name: " << entry);
    AUDIT_CHECK
    (
        digits.size() == 1 || digits.front() != '0',
        "non-canonical processor directory name: " << entry
    );

    std::uint64_t value = 0;
    for (const char ch : digits)
    {
        AUDIT_CHECK
        (
            ch >= '0' && ch <= '9',
            "invalid processor directory name: " << entry
        );
        const unsigned digit = static_cast<unsigned>(ch - '0');
        AUDIT_CHECK
        (
            value <= (std::uint64_t(labelMax) - digit)/10u,
            "processor rank exceeds OpenFOAM label range: " << entry
        );
        value = value*10u + digit;
    }
    rank = static_cast<label>(value);
    return true;
}

std::vector<label> discoverRanks(const fileName& casePath)
{
    const fileNameList directories =
        readDir(casePath, fileName::DIRECTORY, false, false);
    std::vector<label> ranks;
    for (const fileName& entry : directories)
    {
        label rank = -1;
        if (parseProcessorRank(entry, rank))
        {
            ranks.push_back(rank);
        }
    }
    std::sort(ranks.begin(), ranks.end());
    AUDIT_CHECK(!ranks.empty(), "no canonical processorN directories found");
    AUDIT_CHECK
    (
        ranks.size() <= static_cast<std::size_t>(labelMax),
        "processor directory count exceeds OpenFOAM label range"
    );
    for (std::size_t i = 0; i < ranks.size(); ++i)
    {
        AUDIT_CHECK
        (
            ranks[i] == static_cast<label>(i),
            "processor ranks must be unique and contiguous from zero; index "
                << i << " contains rank " << ranks[i]
        );
    }
    return ranks;
}

autoPtr<fvMesh> openProcessorMesh
(
    const argList& args,
    const word& regionName,
    const label rank,
    autoPtr<Time>& processorTime
)
{
    processorTime.reset
    (
        new Time
        (
            Time::controlDictName,
            args.rootPath(),
            args.caseName()/("processor" + Foam::name(rank)),
            args.allowFunctionObjects(),
            args.allowLibs()
        )
    );
    autoPtr<fvMesh> result
    (
        new fvMesh
        (
            IOobject
            (
                regionName,
                processorTime().constant(),
                processorTime(),
                IOobject::MUST_READ
            ),
            false
        )
    );
    result().init(true);
    return result;
}

labelIOList readAddressing(const fvMesh& mesh, const word& name)
{
    return labelIOList
    (
        IOobject
        (
            name,
            mesh.facesInstance(),
            polyMesh::meshSubDir,
            mesh.thisDb(),
            IOobject::MUST_READ,
            IOobject::NO_WRITE,
            IOobject::NO_REGISTER
        )
    );
}

bool cyclicMatch
(
    const face& localFace,
    const labelIOList& pointAddressing,
    const face& serialFace,
    const bool positive
)
{
    if (localFace.size() != serialFace.size() || localFace.empty())
    {
        return false;
    }
    const label first = pointAddressing[localFace[0]];
    forAll(serialFace, start)
    {
        if (serialFace[start] != first)
        {
            continue;
        }
        bool matches = true;
        for (label offset = 1; offset < localFace.size(); ++offset)
        {
            const label serialOffset = positive ? offset : -offset;
            const label serialIndex =
                (start + serialOffset + serialFace.size()) % serialFace.size();
            if
            (
                pointAddressing[localFace[offset]]
             != serialFace[serialIndex]
            )
            {
                matches = false;
                break;
            }
        }
        if (matches)
        {
            return true;
        }
    }
    return false;
}

void writeJsonString(Ostream& output, const std::string& value)
{
    output << '"';
    for (const unsigned char ch : value)
    {
        switch (ch)
        {
            case '"': output << "\\\""; break;
            case '\\': output << "\\\\"; break;
            case '\b': output << "\\b"; break;
            case '\f': output << "\\f"; break;
            case '\n': output << "\\n"; break;
            case '\r': output << "\\r"; break;
            case '\t': output << "\\t"; break;
            default:
                if (ch < 0x20u)
                {
                    static const char hex[] = "0123456789abcdef";
                    output << "\\u00" << hex[ch >> 4] << hex[ch & 0x0f];
                }
                else
                {
                    output << static_cast<char>(ch);
                }
        }
    }
    output << '"';
}

void writeLocator(Ostream& output, const Locator& locator)
{
    output << "{\"locator_kind\":\"runtime_relative_ephemeral\",\"path\":";
    writeJsonString(output, std::string(locator.path));
    output << ",\"size_bytes\":" << locator.sizeBytes << ",\"sha256\":";
    // Foam::Ostream quotes std::string values itself.  Surrounding that
    // insertion with literal quotes therefore produced ""<digest>"" and an
    // invalid partition-observed document.  Use the same byte-wise JSON
    // string writer as paths so the representation is independent of the
    // OpenFOAM stream overload selected for std::string.
    writeJsonString(output, locator.sha256);
    output << '}';
}

void writeNamedLocators
(
    Ostream& output,
    const std::array<Locator, 5>& locators
)
{
    static const std::array<const char*, 5> names
    {{"points", "faces", "owner", "neighbour", "boundary"}};
    output << '{';
    for (std::size_t i = 0; i < names.size(); ++i)
    {
        if (i) output << ',';
        output << '"' << names[i] << "\":";
        writeLocator(output, locators[i]);
    }
    output << '}';
}

void writeAddressLocators
(
    Ostream& output,
    const std::array<Locator, 4>& locators
)
{
    static const std::array<const char*, 4> names
    {{"cell", "face", "point", "boundary"}};
    output << '{';
    for (std::size_t i = 0; i < names.size(); ++i)
    {
        if (i) output << ',';
        output << '"' << names[i] << "\":";
        writeLocator(output, locators[i]);
    }
    output << '}';
}

} // End anonymous namespace

int main(int argc, char *argv[])
{
    argList::addNote("verify and write the v2 partition-observed source");
    argList::addOption("output", "file", "v2 partition JSON output");
    argList::addBoolOption
    (
        "constant",
        "audit only the required constant/polyMesh topology"
    );
    #include "setRootCase.H"
    #include "createTime.H"

    AUDIT_CHECK(args.found("output"), "-output is required");
    AUDIT_CHECK(args.found("constant"), "-constant is required");

    const word regionName(polyMesh::defaultRegion);
    Info<< "Create serial mesh from constant/polyMesh" << nl << endl;
    fvMesh mesh
    (
        IOobject
        (
            regionName,
            runTime.constant(),
            runTime,
            IOobject::MUST_READ
        ),
        false
    );
    mesh.init(true);
    AUDIT_CHECK
    (
        mesh.facesInstance() == runTime.constant()
     && mesh.pointsInstance() == runTime.constant(),
        "partition-observed/v1 requires the serial topology in constant/polyMesh"
    );

    const fileName casePath(args.path());
    const std::vector<label> ranks = discoverRanks(casePath);
    const label nRanks = static_cast<label>(ranks.size());

    const std::array<fileName, 5> meshNames
    {{"points", "faces", "owner", "neighbour", "boundary"}};
    const std::array<fileName, 4> addressNames
    {{
        "cellProcAddressing",
        "faceProcAddressing",
        "pointProcAddressing",
        "boundaryProcAddressing"
    }};

    std::array<Locator, 5> serialLocators;
    for (std::size_t i = 0; i < meshNames.size(); ++i)
    {
        serialLocators[i] = makeLocator
        (
            casePath,
            fileName("constant")/polyMesh::meshSubDir/meshNames[i]
        );
    }

    bitSet globalCells(mesh.nCells());
    labelList cellRank(mesh.nCells(), -1);
    std::vector<label> cellCounts(static_cast<std::size_t>(nRanks), 0);

    // First pass: establish the unique owner rank of every serial cell.
    for (const label rank : ranks)
    {
        autoPtr<Time> processorTime;
        autoPtr<fvMesh> processorMesh =
            openProcessorMesh(args, regionName, rank, processorTime);
        const fvMesh& procMesh = processorMesh();
        AUDIT_CHECK
        (
            procMesh.facesInstance() == processorTime().constant()
         && procMesh.pointsInstance() == processorTime().constant(),
            "processor" << rank
                << " topology must be in constant/polyMesh"
        );
        const labelIOList cellAddressing =
            readAddressing(procMesh, "cellProcAddressing");
        AUDIT_CHECK
        (
            cellAddressing.size() == procMesh.nCells(),
            "processor" << rank << " cellProcAddressing size "
                << cellAddressing.size() << " differs from local cell count "
                << procMesh.nCells()
        );
        AUDIT_CHECK
        (
            procMesh.nCells() > 0,
            "processor" << rank << " has no cells; subdomain cell_count must be positive"
        );
        forAll(cellAddressing, localCell)
        {
            const label globalCell = cellAddressing[localCell];
            AUDIT_CHECK
            (
                globalCell >= 0 && globalCell < mesh.nCells(),
                "processor" << rank << " cellProcAddressing[" << localCell
                    << "] is out of serial range: " << globalCell
            );
            AUDIT_CHECK
            (
                !globalCells.test(globalCell),
                "serial cell " << globalCell
                    << " is assigned more than once (encountered at processor"
                    << rank << ')'
            );
            globalCells.set(globalCell);
            cellRank[globalCell] = rank;
        }
        cellCounts[static_cast<std::size_t>(rank)] = procMesh.nCells();
        processorMesh.clear();
        processorTime.clear();
    }
    AUDIT_CHECK
    (
        globalCells.all(),
        "cellProcAddressing union contains " << globalCells.count()
            << " cells but serial mesh contains " << mesh.nCells()
    );

    bitSet globalPoints(mesh.nPoints());
    PackedList<2> faceAppearances(mesh.nFaces(), 0u);
    bitSet positiveFaces(mesh.nFaces());
    bitSet negativeFaces(mesh.nFaces());
    std::map<std::pair<label, label>, InterfaceState> interfaces;
    std::vector<SubdomainRecord> subdomains;
    subdomains.reserve(ranks.size());

    const labelUList& serialOwner = mesh.faceOwner();
    const labelUList& serialNeighbour = mesh.faceNeighbour();
    const polyBoundaryMesh& serialBoundary = mesh.boundaryMesh();

    // Second pass: verify all addressing, face topology, and bilateral patches.
    for (const label rank : ranks)
    {
        autoPtr<Time> processorTime;
        autoPtr<fvMesh> processorMesh =
            openProcessorMesh(args, regionName, rank, processorTime);
        const fvMesh& procMesh = processorMesh();
        AUDIT_CHECK
        (
            procMesh.facesInstance() == processorTime().constant()
         && procMesh.pointsInstance() == processorTime().constant(),
            "processor" << rank
                << " topology moved out of constant/polyMesh between audit passes"
        );

        const labelIOList cellAddressing =
            readAddressing(procMesh, "cellProcAddressing");
        const labelIOList faceAddressing =
            readAddressing(procMesh, "faceProcAddressing");
        const labelIOList pointAddressing =
            readAddressing(procMesh, "pointProcAddressing");
        const labelIOList boundaryAddressing =
            readAddressing(procMesh, "boundaryProcAddressing");

        AUDIT_CHECK
        (
            cellAddressing.size() == procMesh.nCells()
         && procMesh.nCells() == cellCounts[static_cast<std::size_t>(rank)],
            "processor" << rank << " cell topology changed between audit passes"
        );
        bitSet currentRankCells(mesh.nCells());
        forAll(cellAddressing, localCell)
        {
            const label globalCell = cellAddressing[localCell];
            AUDIT_CHECK
            (
                globalCell >= 0 && globalCell < mesh.nCells()
             && cellRank[globalCell] == rank
             && !currentRankCells.test(globalCell),
                "processor" << rank << " cellProcAddressing changed at local cell "
                    << localCell
            );
            currentRankCells.set(globalCell);
        }
        AUDIT_CHECK
        (
            faceAddressing.size() == procMesh.nFaces(),
            "processor" << rank << " faceProcAddressing size "
                << faceAddressing.size() << " differs from local face count "
                << procMesh.nFaces()
        );
        AUDIT_CHECK
        (
            pointAddressing.size() == procMesh.nPoints(),
            "processor" << rank << " pointProcAddressing size "
                << pointAddressing.size() << " differs from local point count "
                << procMesh.nPoints()
        );
        AUDIT_CHECK
        (
            boundaryAddressing.size() == procMesh.boundaryMesh().size(),
            "processor" << rank << " boundaryProcAddressing size "
                << boundaryAddressing.size() << " differs from local patch count "
                << procMesh.boundaryMesh().size()
        );

        bitSet localPoints(mesh.nPoints());
        forAll(pointAddressing, localPoint)
        {
            const label globalPoint = pointAddressing[localPoint];
            AUDIT_CHECK
            (
                globalPoint >= 0 && globalPoint < mesh.nPoints(),
                "processor" << rank << " pointProcAddressing[" << localPoint
                    << "] is out of serial range: " << globalPoint
            );
            AUDIT_CHECK
            (
                !localPoints.test(globalPoint),
                "processor" << rank << " maps multiple local points to serial point "
                    << globalPoint
            );
            localPoints.set(globalPoint);
            globalPoints.set(globalPoint);
        }

        const polyBoundaryMesh& procBoundary = procMesh.boundaryMesh();
        forAll(procBoundary, patchi)
        {
            const polyPatch& patch = procBoundary[patchi];
            const processorPolyPatch* processorPatch =
                isA<processorPolyPatch>(patch);
            if (processorPatch)
            {
                AUDIT_CHECK
                (
                    boundaryAddressing[patchi] == -1,
                    "processor" << rank << " processor patch " << patch.name()
                        << " must have boundaryProcAddressing=-1"
                );
                AUDIT_CHECK
                (
                    processorPatch->myProcNo() == rank,
                    "processor patch " << patch.name() << " declares myProcNo="
                        << processorPatch->myProcNo() << " while loaded as rank "
                        << rank
                );
                const label neighbourRank = processorPatch->neighbProcNo();
                AUDIT_CHECK
                (
                    neighbourRank >= 0 && neighbourRank < nRanks
                 && neighbourRank != rank,
                    "processor" << rank << " patch " << patch.name()
                        << " has invalid neighbour rank " << neighbourRank
                );
                AUDIT_CHECK
                (
                    patch.size() > 0,
                    "processor interface patch " << patch.name()
                        << " has no faces"
                );

                const label lower = std::min(rank, neighbourRank);
                const label upper = std::max(rank, neighbourRank);
                InterfaceState& state = interfaces[std::make_pair(lower, upper)];
                std::vector<label> ids;
                ids.reserve(static_cast<std::size_t>(patch.size()));
                for (label offset = 0; offset < patch.size(); ++offset)
                {
                    const label localFace = patch.start() + offset;
                    const label encoded = faceAddressing[localFace];
                    AUDIT_CHECK
                    (
                        encoded != 0 && encoded != labelMin,
                        "processor patch " << patch.name()
                            << " contains invalid faceProcAddressing value " << encoded
                    );
                    const label globalFace =
                        (encoded > 0 ? encoded : -encoded) - 1;
                    AUDIT_CHECK
                    (
                        globalFace >= 0 && globalFace < mesh.nFaces(),
                        "processor patch " << patch.name()
                            << " maps outside the serial face range"
                    );
                    ids.push_back(globalFace);
                }
                std::sort(ids.begin(), ids.end());
                AUDIT_CHECK
                (
                    std::adjacent_find(ids.begin(), ids.end()) == ids.end(),
                    "processor patch " << patch.name()
                        << " repeats a mapped serial face"
                );

                if (rank == lower)
                {
                    AUDIT_CHECK
                    (
                        !state.lowerSeen,
                        "multiple processor" << lower << " patches target processor"
                            << upper
                    );
                    state.lowerSeen = true;
                    state.nFaces = patch.size();
                    state.lowerFaceIds = std::move(ids);
                }
                else
                {
                    AUDIT_CHECK
                    (
                        state.lowerSeen && !state.upperSeen,
                        "processor interface " << lower << "-" << upper
                            << " is missing or duplicated on one side"
                    );
                    AUDIT_CHECK
                    (
                        state.nFaces == patch.size()
                     && state.lowerFaceIds == ids,
                        "processor interface " << lower << "-" << upper
                            << " has unequal nFaces or mapped face IDs"
                    );
                    state.upperSeen = true;
                    state.lowerFaceIds.clear();
                    state.lowerFaceIds.shrink_to_fit();
                }
            }
            else
            {
                const label serialPatchi = boundaryAddressing[patchi];
                AUDIT_CHECK
                (
                    serialPatchi >= 0 && serialPatchi < serialBoundary.size(),
                    "processor" << rank << " nonprocessor patch " << patch.name()
                        << " has invalid boundaryProcAddressing " << serialPatchi
                );
                const polyPatch& serialPatch = serialBoundary[serialPatchi];
                AUDIT_CHECK
                (
                    patch.name() == serialPatch.name()
                 && patch.type() == serialPatch.type(),
                    "processor" << rank << " patch " << patch.name()
                        << " does not match serial patch name/type at index "
                        << serialPatchi
                );
            }
        }

        bitSet localFaces(mesh.nFaces());
        const labelUList& procOwner = procMesh.faceOwner();
        const labelUList& procNeighbour = procMesh.faceNeighbour();
        forAll(faceAddressing, localFace)
        {
            const label encoded = faceAddressing[localFace];
            AUDIT_CHECK
            (
                encoded != 0 && encoded != labelMin,
                "processor" << rank << " faceProcAddressing[" << localFace
                    << "] is invalid: " << encoded
            );
            const bool positive = encoded > 0;
            const label globalFace =
                (positive ? encoded : -encoded) - 1;
            AUDIT_CHECK
            (
                globalFace >= 0 && globalFace < mesh.nFaces(),
                "processor" << rank << " faceProcAddressing[" << localFace
                    << "] is outside the serial face range: " << encoded
            );
            AUDIT_CHECK
            (
                !localFaces.test(globalFace),
                "processor" << rank << " maps multiple local faces to serial face "
                    << globalFace
            );
            localFaces.set(globalFace);

            const unsigned int appearances = faceAppearances.get(globalFace);
            AUDIT_CHECK
            (
                appearances < 2u,
                "serial face " << globalFace << " appears more than twice"
            );
            faceAppearances.set(globalFace, appearances + 1u);
            if (positive)
            {
                AUDIT_CHECK
                (
                    !positiveFaces.test(globalFace),
                    "serial face " << globalFace
                        << " repeats positive orientation"
                );
                positiveFaces.set(globalFace);
            }
            else
            {
                AUDIT_CHECK
                (
                    !negativeFaces.test(globalFace),
                    "serial face " << globalFace
                        << " repeats negative orientation"
                );
                negativeFaces.set(globalFace);
            }

            const bool localInternal = localFace < procMesh.nInternalFaces();
            label localPatchi = -1;
            const processorPolyPatch* processorPatch = nullptr;
            if (!localInternal)
            {
                localPatchi = procBoundary.whichPatch(localFace);
                AUDIT_CHECK
                (
                    localPatchi >= 0,
                    "processor" << rank << " boundary face " << localFace
                        << " belongs to no patch"
                );
                processorPatch =
                    isA<processorPolyPatch>(procBoundary[localPatchi]);
            }

            AUDIT_CHECK
            (
                cyclicMatch
                (
                    procMesh.faces()[localFace],
                    pointAddressing,
                    mesh.faces()[globalFace],
                    positive
                ),
                "processor" << rank << " local face " << localFace
                    << " point cycle does not match serial face " << globalFace
                    << " with its addressing sign"
            );

            const label globalLocalOwner = cellAddressing[procOwner[localFace]];
            if (globalFace < mesh.nInternalFaces())
            {
                const label ownerRank = cellRank[serialOwner[globalFace]];
                const label neighbourRank = cellRank[serialNeighbour[globalFace]];
                if (ownerRank == neighbourRank)
                {
                    AUDIT_CHECK
                    (
                        rank == ownerRank && localInternal,
                        "unsplit serial internal face " << globalFace
                            << " is not one internal face on owner rank " << ownerRank
                    );
                    const label globalLocalNeighbour =
                        cellAddressing[procNeighbour[localFace]];
                    AUDIT_CHECK
                    (
                        positive
                          ? (globalLocalOwner == serialOwner[globalFace]
                          && globalLocalNeighbour == serialNeighbour[globalFace])
                          : (globalLocalOwner == serialNeighbour[globalFace]
                          && globalLocalNeighbour == serialOwner[globalFace]),
                        "processor" << rank << " internal face " << localFace
                            << " owner/neighbour cells disagree with serial face "
                            << globalFace << " and its addressing sign"
                    );
                }
                else
                {
                    AUDIT_CHECK
                    (
                        !localInternal && processorPatch,
                        "split serial internal face " << globalFace
                            << " is not represented by a processor patch"
                    );
                    const label expectedOther =
                        rank == ownerRank ? neighbourRank
                      : rank == neighbourRank ? ownerRank
                      : -1;
                    AUDIT_CHECK
                    (
                        expectedOther >= 0
                     && processorPatch->neighbProcNo() == expectedOther,
                        "processor" << rank << " split face " << globalFace
                            << " is on the wrong bilateral processor patch"
                    );
                    AUDIT_CHECK
                    (
                        globalLocalOwner
                         == (positive
                              ? serialOwner[globalFace]
                              : serialNeighbour[globalFace]),
                        "processor" << rank << " split face " << globalFace
                            << " local owner disagrees with its addressing sign"
                    );
                }
            }
            else
            {
                AUDIT_CHECK
                (
                    rank == cellRank[serialOwner[globalFace]]
                 && !localInternal && !processorPatch,
                    "serial boundary face " << globalFace
                        << " is not one nonprocessor boundary face on its owner rank"
                );
                AUDIT_CHECK
                (
                    globalLocalOwner == serialOwner[globalFace],
                    "processor" << rank << " boundary face " << localFace
                        << " owner does not match serial boundary face " << globalFace
                );
                const label serialPatchi = serialBoundary.whichPatch(globalFace);
                AUDIT_CHECK
                (
                    serialPatchi >= 0
                 && boundaryAddressing[localPatchi] == serialPatchi,
                    "processor" << rank << " boundary face " << localFace
                        << " maps to the wrong serial boundary patch"
                );
            }
        }

        SubdomainRecord record;
        record.rank = rank;
        record.cellCount = procMesh.nCells();
        const fileName procPrefix("processor" + Foam::name(rank));
        for (std::size_t i = 0; i < meshNames.size(); ++i)
        {
            record.mesh[i] = makeLocator
            (
                casePath,
                procPrefix/fileName("constant")/polyMesh::meshSubDir/meshNames[i]
            );
        }
        for (std::size_t i = 0; i < addressNames.size(); ++i)
        {
            record.addressing[i] = makeLocator
            (
                casePath,
                procPrefix/fileName("constant")/polyMesh::meshSubDir/addressNames[i]
            );
        }
        subdomains.push_back(std::move(record));

        processorMesh.clear();
        processorTime.clear();
    }

    AUDIT_CHECK
    (
        globalPoints.all(),
        "pointProcAddressing union contains " << globalPoints.count()
            << " points but serial mesh contains " << mesh.nPoints()
    );
    for (label globalFace = 0; globalFace < mesh.nFaces(); ++globalFace)
    {
        const bool split =
            globalFace < mesh.nInternalFaces()
         && cellRank[serialOwner[globalFace]]
         != cellRank[serialNeighbour[globalFace]];
        const unsigned int expected = split ? 2u : 1u;
        AUDIT_CHECK
        (
            faceAppearances.get(globalFace) == expected,
            "serial face " << globalFace << " appears "
                << faceAppearances.get(globalFace) << " times; expected " << expected
        );
        AUDIT_CHECK
        (
            !split
         || (positiveFaces.test(globalFace) && negativeFaces.test(globalFace)),
            "split serial internal face " << globalFace
                << " does not have opposite addressing signs"
        );
    }
    for (const auto& item : interfaces)
    {
        AUDIT_CHECK
        (
            item.second.lowerSeen && item.second.upperSeen
         && item.second.nFaces > 0,
            "processor interface " << item.first.first << '-'
                << item.first.second << " is not present exactly once on both sides"
        );
    }

    fileName outputPath(args.get<fileName>("output"));
    if (!outputPath.isAbsolute())
    {
        outputPath = casePath/outputPath;
    }
    outputPath.clean();
    AUDIT_CHECK(!outputPath.empty(), "-output resolved to an empty path");
    AUDIT_CHECK
    (
        outputPath.type(false, false) == fileName::UNDEFINED,
        "refusing to overwrite existing output: " << outputPath
    );
    AUDIT_CHECK
    (
        mkDir(outputPath.path()),
        "cannot create output directory: " << outputPath.path()
    );
    const fileName temporary
    (
        outputPath + ".tmp-" + Foam::name(pid())
    );
    AUDIT_CHECK
    (
        temporary.type(false, false) == fileName::UNDEFINED,
        "temporary output already exists: " << temporary
    );

    {
        OFstream output(temporary);
        AUDIT_CHECK(output.good(), "cannot open temporary output: " << temporary);
        output << "{\"schema_version\":\"partition-observed/v1\","
               << "\"serial_mesh\":";
        writeNamedLocators(output, serialLocators);
        output << ",\"subdomains\":[";
        for (std::size_t i = 0; i < subdomains.size(); ++i)
        {
            if (i) output << ',';
            const SubdomainRecord& record = subdomains[i];
            output << "{\"rank\":" << record.rank
                   << ",\"cell_count\":" << record.cellCount
                   << ",\"mesh\":";
            writeNamedLocators(output, record.mesh);
            output << ",\"addressing\":";
            writeAddressLocators(output, record.addressing);
            output << '}';
        }
        output << "],\"interfaces\":[";
        bool firstInterface = true;
        for (const auto& item : interfaces)
        {
            if (!firstInterface) output << ',';
            firstInterface = false;
            output << "{\"lower_rank\":" << item.first.first
                   << ",\"upper_rank\":" << item.first.second
                   << ",\"n_faces\":" << item.second.nFaces << '}';
        }
        output << "]}" << nl;
        AUDIT_CHECK(output.good(), "failed while writing output: " << temporary);
    }
    AUDIT_CHECK
    (
        temporary.type(false, false) == fileName::FILE,
        "temporary output is not a regular file: " << temporary
    );
    AUDIT_CHECK
    (
        mv(temporary, outputPath, false),
        "cannot atomically publish output " << outputPath
    );

    Info<< "Verified " << nRanks << " processor meshes; wrote "
        << outputPath << nl << endl;
    return 0;
}

#undef AUDIT_CHECK
