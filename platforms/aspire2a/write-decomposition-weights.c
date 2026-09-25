// Construct a temporary OpenFOAM weightField from the official binary owner list.
// The mesh and the physical fields are not modified.
#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct patch {
    char name[128];
    char type[32];
    uint64_t start;
    uint64_t count;
    int selected;
};

static void fail(const char *message) {
    fprintf(stderr, "write-decomposition-weights: %s\n", message);
    exit(EXIT_FAILURE);
}

static int selected_patch(const char *name) {
    static const char *prefixes[] = {
        "WheelSupport", "BrakeDisc", "Tires", "Rims",
        "OCDADetailedUnderbody", "Powertrain", "ExhaustSystem", "EngineUndershield"
    };
    for (size_t i = 0; i < sizeof(prefixes) / sizeof(prefixes[0]); ++i) {
        if (strncmp(name, prefixes[i], strlen(prefixes[i])) == 0) return 1;
    }
    return 0;
}

static char *trim(char *line) {
    while (isspace((unsigned char)*line)) ++line;
    char *end = line + strlen(line);
    while (end > line && isspace((unsigned char)end[-1])) --end;
    *end = '\0';
    return line;
}

static size_t read_boundary(const char *path, struct patch *patches, size_t capacity) {
    FILE *in = fopen(path, "r");
    if (!in) fail("cannot open boundary");
    char line[1024];
    int in_list = 0, in_patch = 0;
    size_t count = 0;
    uint64_t expected_start = 0;
    while (fgets(line, sizeof(line), in)) {
        char *s = trim(line);
        if (!in_list) {
            if (strcmp(s, "(") == 0) in_list = 1;
            continue;
        }
        if (strcmp(s, ")") == 0) break;
        if (!in_patch) {
            if (*s == '\0' || *s == '{') { if (*s == '{') in_patch = 1; continue; }
            if (count >= capacity || strlen(s) >= sizeof(patches[count].name)) fail("too many patches or long patch name");
            memset(&patches[count], 0, sizeof(patches[count]));
            strcpy(patches[count].name, s);
            patches[count].selected = selected_patch(s);
            continue;
        }
        if (*s == '}') {
            if (!patches[count].type[0] || !patches[count].count) fail("incomplete patch");
            if (count && patches[count].start != expected_start) fail("non-contiguous boundary faces");
            expected_start = patches[count].start + patches[count].count;
            ++count;
            in_patch = 0;
        } else if (strncmp(s, "type ", 5) == 0 || strncmp(s, "type\t", 5) == 0) {
            if (sscanf(s, "type %31[^;];", patches[count].type) != 1) fail("invalid patch type");
        } else if (strncmp(s, "nFaces ", 7) == 0 || strncmp(s, "nFaces\t", 7) == 0) {
            if (sscanf(s, "nFaces %" SCNu64 ";", &patches[count].count) != 1) fail("invalid patch face count");
        } else if (strncmp(s, "startFace ", 10) == 0 || strncmp(s, "startFace\t", 10) == 0) {
            if (sscanf(s, "startFace %" SCNu64 ";", &patches[count].start) != 1) fail("invalid patch start");
        }
    }
    fclose(in);
    if (!in_list || in_patch || !count) fail("invalid boundary list");
    return count;
}

static void read_owner_header(FILE *in, uint64_t *cells, uint64_t *faces, off_t *offset) {
    char line[1024];
    int binary = 0, labels32 = 0, list_start = 0;
    while (fgets(line, sizeof(line), in)) {
        char *s = trim(line);
        if (strstr(s, "format") && strstr(s, "binary")) binary = 1;
        if (strstr(s, "arch") && strstr(s, "LSB;label=32")) labels32 = 1;
        char *p = strstr(s, "nCells:");
        if (p && sscanf(p, "nCells:%" SCNu64, cells) != 1) fail("invalid nCells header");
        if (isdigit((unsigned char)*s)) {
            char extra;
            if (sscanf(s, "%" SCNu64 " %c", faces, &extra) == 1) {
                if (!fgets(line, sizeof(line), in) || strcmp(trim(line), "(") != 0) fail("invalid owner list start");
                *offset = ftello(in);
                list_start = 1;
                break;
            }
        }
    }
    if (!binary || !labels32 || !list_start || !*cells || !*faces || *offset < 0) fail("unsupported owner format");
}

int main(int argc, char **argv) {
    if (argc != 4) fail("usage: write-decomposition-weights BOUNDARY OWNER OUTPUT");
    struct patch patches[128];
    size_t patch_count = read_boundary(argv[1], patches, 128);
    FILE *owner = fopen(argv[2], "rb");
    if (!owner) fail("cannot open owner");
    uint64_t cells = 0, faces = 0;
    off_t offset = -1;
    read_owner_header(owner, &cells, &faces, &offset);
    if (patches[patch_count - 1].start + patches[patch_count - 1].count != faces) fail("boundary/owner face counts differ");
    if (cells > SIZE_MAX) fail("cell count too large");
    unsigned char *weighted = calloc((size_t)cells, 1);
    if (!weighted) fail("cannot allocate cell marks");
    uint32_t buffer[16384];
    uint64_t selected_faces = 0, selected_cells = 0;
    size_t selected_patches = 0;
    for (size_t i = 0; i < patch_count; ++i) {
        if (!patches[i].selected) continue;
        ++selected_patches;
        selected_faces += patches[i].count;
        if (fseeko(owner, offset + (off_t)(patches[i].start * sizeof(uint32_t)), SEEK_SET)) fail("cannot seek owner range");
        for (uint64_t remaining = patches[i].count; remaining;) {
            size_t block = remaining < 16384 ? (size_t)remaining : 16384;
            if (fread(buffer, sizeof(uint32_t), block, owner) != block) fail("cannot read owner range");
            for (size_t j = 0; j < block; ++j) {
                if (buffer[j] >= cells) fail("owner cell index out of range");
                if (!weighted[buffer[j]]) { weighted[buffer[j]] = 1; ++selected_cells; }
            }
            remaining -= block;
        }
    }
    fclose(owner);
    if (!selected_patches || !selected_cells) fail("target patch cells not found");
    FILE *out = fopen(argv[3], "w");
    if (!out) fail("cannot create weight field");
    fprintf(out, "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class volScalarField;\n    location \"0\";\n    object costWeight;\n}\n");
    fprintf(out, "dimensions [0 0 0 0 0 0 0];\ninternalField nonuniform List<scalar>\n%" PRIu64 "\n(\n", cells);
    for (uint64_t i = 0; i < cells; ++i) fprintf(out, "%d\n", weighted[i] ? 3 : 1);
    fprintf(out, ")\n;\nboundaryField\n{\n");
    for (size_t i = 0; i < patch_count; ++i) {
        fprintf(out, "    %s\n    {\n", patches[i].name);
        if (strcmp(patches[i].type, "symmetry") == 0) fprintf(out, "        type symmetry;\n");
        else fprintf(out, "        type calculated;\n        value uniform 1;\n");
        fprintf(out, "    }\n");
    }
    fprintf(out, "}\n");
    if (fclose(out)) fail("cannot finish weight field");
    fprintf(stdout, "patches=%zu\nselected_patches=%zu\nselected_faces=%" PRIu64 "\ncells=%" PRIu64 "\nselected_cells=%" PRIu64 "\nselected_weight=3\nother_weight=1\n", patch_count, selected_patches, selected_faces, cells, selected_cells);
    free(weighted);
    return EXIT_SUCCESS;
}
