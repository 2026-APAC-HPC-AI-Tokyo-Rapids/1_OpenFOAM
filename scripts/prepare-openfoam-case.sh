#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
    echo "usage: $0 SOURCE_CASE TARGET_CASE BLOCK_MESH DECOMPOSE_PAR" >&2
    exit 64
fi

SOURCE_CASE=$1
TARGET_CASE=$2
BLOCK_MESH=$3
DECOMPOSE_PAR=$4
CACHE_ROOT="${HOME}/../share/openfoam-case-cache"
NUMBER_OF_SUBDOMAINS=120

[[ -d "${SOURCE_CASE}" ]] || { echo "source case not found: ${SOURCE_CASE}" >&2; exit 66; }
[[ ! -e "${TARGET_CASE}" ]] || { echo "target case already exists: ${TARGET_CASE}" >&2; exit 73; }
[[ -x "${BLOCK_MESH}" ]] || { echo "blockMesh is not executable: ${BLOCK_MESH}" >&2; exit 69; }
[[ -x "${DECOMPOSE_PAR}" ]] || { echo "decomposePar is not executable: ${DECOMPOSE_PAR}" >&2; exit 69; }

SCRIPT_SHA256=$(sha256sum "$0" | awk '{print $1}')
CACHE_DIR="${CACHE_ROOT}/${SCRIPT_SHA256}"
LOCK_FILE="${CACHE_ROOT}/.${SCRIPT_SHA256}.lock"
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

    cat > "${case_dir}/system/decomposeParDict.6" <<'DECOMPOSE_PAR_DICT'
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      decomposeParDict;
}

numberOfSubdomains 120;
method scotch;
DECOMPOSE_PAR_DICT
}

cache_valid() {
    [[ -f "${CACHE_DIR}/READY" ]] &&
        [[ $(<"${CACHE_DIR}/READY") == "${SCRIPT_SHA256}" ]] &&
        [[ -d "${CACHE_DIR}/case/constant/polyMesh" ]] &&
        [[ -d "${CACHE_DIR}/case/processor0" ]] &&
        [[ -d "${CACHE_DIR}/case/processor$((NUMBER_OF_SUBDOMAINS - 1))" ]]
}

exec 9>"${LOCK_FILE}"
flock 9
cache_hit=true
if ! cache_valid; then
    cache_hit=false
    TEMP_DIR="${CACHE_DIR}.tmp.$$"
    trap 'rm -rf "${TEMP_DIR:-}"' EXIT
    rm -rf "${TEMP_DIR}"
    mkdir -p "${TEMP_DIR}/case/logs"
    cp -a "${SOURCE_CASE}/." "${TEMP_DIR}/case/"
    write_generation_files "${TEMP_DIR}/case"
    (
        cd "${TEMP_DIR}/case"
        "${BLOCK_MESH}" -fileHandler uncollated > logs/blockMesh.log 2>&1
        "${DECOMPOSE_PAR}" -fileHandler uncollated \
            -decomposeParDict system/decomposeParDict.6 -force \
            > logs/decomposePar.log 2>&1
    )
    printf '%s\n' "${SCRIPT_SHA256}" > "${TEMP_DIR}/READY"
    jq -n --arg prepare_script_sha256 "${SCRIPT_SHA256}" \
        '{schema_version:"openfoam-case-cache/v1",prepare_script_sha256:$prepare_script_sha256,number_of_subdomains:120,method:"scotch",file_handler:"uncollated"}' \
        > "${TEMP_DIR}/manifest.json"
    find "${TEMP_DIR}/case" -type f -exec chmod a-w {} +
    find "${TEMP_DIR}/case" -type d -exec chmod a-w {} +
    if [[ -e "${CACHE_DIR}" ]]; then
        rm -rf "${TEMP_DIR}"
        cache_valid || { echo "invalid cache entry: ${CACHE_DIR}" >&2; exit 65; }
        cache_hit=true
    else
        mv "${TEMP_DIR}" "${CACHE_DIR}"
    fi
    trap - EXIT
fi
flock -u 9

ln -s "${CACHE_DIR}/case" "${TARGET_CASE}"
printf 'cache_hit=%s\nprepare_script_sha256=%s\ncache_dir=%s\n' \
    "${cache_hit}" "${SCRIPT_SHA256}" "${CACHE_DIR}"
