#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 6 || $# -gt 7 || ( $# -eq 7 && $7 != --require-cache ) ]]; then
    echo "usage: $0 SOURCE_CASE TARGET_CASE BLOCK_MESH DECOMPOSE_PAR SUBDOMAINS CACHE_ROOT [--require-cache]" >&2
    exit 64
fi

SOURCE_CASE=$1
TARGET_CASE=$2
BLOCK_MESH=$3
DECOMPOSE_PAR=$4
NUMBER_OF_SUBDOMAINS=$5
CACHE_ROOT=$6
REQUIRE_CACHE=${7:-}

[[ "${NUMBER_OF_SUBDOMAINS}" =~ ^[1-9][0-9]*$ ]] || {
    echo "subdomains must be a positive integer: ${NUMBER_OF_SUBDOMAINS}" >&2
    exit 64
}

SCRIPT_SHA256=$(sha256sum "$0" | awk '{print $1}')
SOURCE_IDENTITY=$(
    cd "${SOURCE_CASE}"
    find . -type f -print0 |
        sort -z |
        xargs -0 sha256sum |
        sha256sum |
        awk '{print $1}'
)
BLOCK_MESH_SHA256=$(sha256sum "${BLOCK_MESH}" | awk '{print $1}')
DECOMPOSE_PAR_SHA256=$(sha256sum "${DECOMPOSE_PAR}" | awk '{print $1}')
CACHE_IDENTITY=$(
    printf '%s\n' "prepare=${SCRIPT_SHA256}" "source=${SOURCE_IDENTITY}" "subdomains=${NUMBER_OF_SUBDOMAINS}" 'method=scotch' 'fileHandler=uncollated' |
        sha256sum |
        awk '{print $1}'
)
CACHE_DIR="${CACHE_ROOT}/${CACHE_IDENTITY}"
mkdir -p "${CACHE_ROOT}"

write_generation_files() {
    local case_dir=$1
    cat > "${case_dir}/system/blockMeshDict" <<'BLOCK_MESH_DICT'
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}

scale 0.1;
vertices
(
    (0 0 0) (1 0 0) (1 1 0) (0 1 0)
    (0 0 1) (1 0 1) (1 1 1) (0 1 1)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (400 400 400) simpleGrading (1 1 1)
);
edges ();
boundary
(
    movingWall
    {
        type wall;
        faces ((3 7 6 2));
    }
    fixedWalls
    {
        type wall;
        faces ((0 4 7 3) (2 6 5 1) (1 5 4 0) (0 3 2 1) (4 5 6 7));
    }
);
mergePatchPairs ();
BLOCK_MESH_DICT

    cat > "${case_dir}/system/decomposeParDict.6" <<DECOMPOSE_PAR_DICT
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      decomposeParDict;
}

numberOfSubdomains ${NUMBER_OF_SUBDOMAINS};
method scotch;
DECOMPOSE_PAR_DICT
}

cache_valid() {
    printf '%s\n' "${CACHE_IDENTITY}" | cmp -s - "${CACHE_DIR}/READY"
}

cache_hit=true
if ! cache_valid; then
    if [[ "${REQUIRE_CACHE}" == --require-cache ]]; then
        echo "required cache entry is absent or invalid: ${CACHE_DIR}" >&2
        exit 75
    fi
    cache_hit=false
    TEMP_DIR="${CACHE_DIR}.tmp.$$"
    trap 'rm -rf "${TEMP_DIR:-}"' EXIT
    chmod -R u+w "${CACHE_DIR}" 2>/dev/null || true
    rm -rf "${CACHE_DIR}" "${TEMP_DIR}"
    mkdir -p "${TEMP_DIR}/case/logs"
    cp -a "${SOURCE_CASE}/." "${TEMP_DIR}/case/"
    write_generation_files "${TEMP_DIR}/case"
    (
        cd "${TEMP_DIR}/case"
        "${BLOCK_MESH}" -fileHandler uncollated > logs/blockMesh.log 2>&1
        "${DECOMPOSE_PAR}" -fileHandler uncollated -decomposeParDict system/decomposeParDict.6 -force > logs/decomposePar.log 2>&1
    )
    printf '%s\n' "${CACHE_IDENTITY}" > "${TEMP_DIR}/READY"
    jq -n --arg cache_identity "${CACHE_IDENTITY}" --arg prepare_script_sha256 "${SCRIPT_SHA256}" --arg source_identity "${SOURCE_IDENTITY}" --arg block_mesh_sha256 "${BLOCK_MESH_SHA256}" --arg decompose_par_sha256 "${DECOMPOSE_PAR_SHA256}" --argjson number_of_subdomains "${NUMBER_OF_SUBDOMAINS}" '{schema_version:"openfoam-case-cache/v2",cache_identity:$cache_identity,prepare_script_sha256:$prepare_script_sha256,source_identity:$source_identity,block_mesh_sha256:$block_mesh_sha256,decompose_par_sha256:$decompose_par_sha256,number_of_subdomains:$number_of_subdomains,method:"scotch",file_handler:"uncollated"}' > "${TEMP_DIR}/manifest.json"
    find "${TEMP_DIR}/case" -type f -exec chmod a-w {} +
    find "${TEMP_DIR}/case" -type d -exec chmod a-w {} +
    mv "${TEMP_DIR}" "${CACHE_DIR}"
    trap - EXIT
fi

rm -rf "${TARGET_CASE}"
ln -s "${CACHE_DIR}/case" "${TARGET_CASE}"
printf 'cache_hit=%s\nprepare_script_sha256=%s\ncache_dir=%s\n' "${cache_hit}" "${SCRIPT_SHA256}" "${CACHE_DIR}"
