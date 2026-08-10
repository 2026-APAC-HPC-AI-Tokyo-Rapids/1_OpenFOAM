/*---------------------------------------------------------------------------*\
  Native, constant-memory mesh topology source for experiment-metrics v2.
\*---------------------------------------------------------------------------*/

#include "argList.H"
#include "Time.H"
#include "fvMesh.H"
#include "OFstream.H"
#include "OSspecific.H"

using namespace Foam;

int main(int argc, char *argv[])
{
    argList::addNote("write the closed v2 mesh-topology source");
    argList::addOption("output", "file", "v2 topology JSON output");
    argList::addBoolOption
    (
        "constant",
        "read only the required constant/polyMesh topology"
    );
    #include "setRootCase.H"
    #include "createTime.H"

    if (!args.found("output"))
    {
        FatalErrorInFunction << "-output is required" << exit(FatalError);
    }
    if (!args.found("constant"))
    {
        FatalErrorInFunction << "-constant is required" << exit(FatalError);
    }

    fvMesh mesh
    (
        IOobject
        (
            polyMesh::defaultRegion,
            runTime.constant(),
            runTime,
            IOobject::MUST_READ
        ),
        false
    );
    mesh.init(true);

    fileName output(args.get<fileName>("output"));
    if (!output.isAbsolute())
    {
        output = args.path()/output;
    }
    output.clean();
    if (output.empty())
    {
        FatalErrorInFunction << "-output resolved to an empty path"
            << exit(FatalError);
    }
    if (output.type(false, false) != fileName::UNDEFINED)
    {
        FatalErrorInFunction << "refusing to overwrite existing output "
            << output << exit(FatalError);
    }
    if (!mkDir(output.path()))
    {
        FatalErrorInFunction << "cannot create output directory "
            << output.path() << exit(FatalError);
    }

    const fileName temporary(output + ".tmp-" + Foam::name(pid()));
    if (temporary.type(false, false) != fileName::UNDEFINED)
    {
        FatalErrorInFunction << "temporary output already exists "
            << temporary << exit(FatalError);
    }

    {
        OFstream stream(temporary);
        if (!stream.good())
        {
            FatalErrorInFunction << "cannot write " << temporary
                << exit(FatalError);
        }
        stream
            << "{\"schema_version\":\"mesh-topology/v1\","
            << "\"cells\":" << mesh.nCells() << ','
            << "\"faces\":" << mesh.nFaces() << ','
            << "\"points\":" << mesh.nPoints() << ','
            << "\"internal_faces\":" << mesh.nInternalFaces()
            << "}" << nl;
        if (!stream.good())
        {
            FatalErrorInFunction << "failed while writing " << temporary
                << exit(FatalError);
        }
    }
    if (temporary.type(false, false) != fileName::FILE)
    {
        FatalErrorInFunction << "temporary output is not a regular file "
            << temporary << exit(FatalError);
    }
    if (!mv(temporary, output, false))
    {
        FatalErrorInFunction << "cannot atomically publish " << output
            << exit(FatalError);
    }

    return 0;
}
