#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 8 || $# -gt 9 || ( $# -eq 9 && $9 != --require-cache ) ]]; then
    echo "usage: $0 SOURCE_CASE TARGET_CASE BASE_PREPARE BLOCK_MESH DECOMPOSE_PAR RENUMBER_MESH MPIEXEC PROFILE [--require-cache]" >&2
    exit 64
fi

SOURCE_CASE=$1
TARGET_CASE=$2
BASE_PREPARE=$3
BLOCK_MESH=$4
DECOMPOSE_PAR=$5
RENUMBER_MESH=$6
MPIEXEC=$7
PROFILE=$8
REQUIRE_CACHE=${9:-}
NUMBER_OF_SUBDOMAINS=448
CACHE_ROOT="${HOME}/../share/openfoam-case-cache"

case "${PROFILE}" in
    renumber-cuthill-4n448|renumber-block32768-4n448) ;;
    *) echo "unsupported renumber profile: ${PROFILE}" >&2; exit 64 ;;
esac
[[ -d "${SOURCE_CASE}" ]] || { echo "source case not found: ${SOURCE_CASE}" >&2; exit 66; }
[[ ! -e "${TARGET_CASE}" ]] || { echo "target case already exists: ${TARGET_CASE}" >&2; exit 73; }
for executable in "${BASE_PREPARE}" "${BLOCK_MESH}" "${DECOMPOSE_PAR}" "${RENUMBER_MESH}" "${MPIEXEC}"
do
    [[ -x "${executable}" ]] || { echo "required executable is unavailable: ${executable}" >&2; exit 69; }
done

mkdir -p "${CACHE_ROOT}"
BASE_WORK=$(mktemp -d "${CACHE_ROOT}/renumber-base.XXXXXXXXXX")
TEMP_DIR=
cleanup() {
    rm -rf -- "${BASE_WORK}"
    [[ -z "${TEMP_DIR}" ]] || rm -rf -- "${TEMP_DIR}"
}
trap cleanup EXIT
base_prepare_argv=(
    "${BASE_PREPARE}" "${SOURCE_CASE}" "${BASE_WORK}/case"
    "${BLOCK_MESH}" "${DECOMPOSE_PAR}" "${NUMBER_OF_SUBDOMAINS}"
)
[[ "${REQUIRE_CACHE}" != --require-cache ]] || base_prepare_argv+=(--require-cache)
"${base_prepare_argv[@]}" > "${BASE_WORK}/base-prepare.log"
BASE_CASE=$(readlink -f -- "${BASE_WORK}/case")
BASE_CACHE_DIR=$(dirname -- "${BASE_CASE}")
BASE_CACHE_ID=$(<"${BASE_CACHE_DIR}/READY")

SCRIPT_SHA256=$(sha256sum "$0" | awk '{print $1}')
RENUMBER_MESH_SHA256=$(sha256sum "${RENUMBER_MESH}" | awk '{print $1}')
MPIEXEC_SHA256=$(sha256sum "${MPIEXEC}" | awk '{print $1}')
CACHE_IDENTITY=$(
    printf '%s\n' \
        "prepare=${SCRIPT_SHA256}" \
        "base_cache=${BASE_CACHE_ID}" \
        "renumberMesh=${RENUMBER_MESH_SHA256}" \
        "mpiexec=${MPIEXEC_SHA256}" \
        "profile=${PROFILE}" \
        "subdomains=${NUMBER_OF_SUBDOMAINS}" \
        'fileHandler=uncollated' |
        sha256sum | awk '{print $1}'
)
CACHE_DIR="${CACHE_ROOT}/${CACHE_IDENTITY}"

cache_valid() {
    [[ -f "${CACHE_DIR}/READY" ]] &&
        [[ $(<"${CACHE_DIR}/READY") == "${CACHE_IDENTITY}" ]] &&
        [[ -s "${CACHE_DIR}/case/logs/renumberMesh.log" ]] &&
        [[ -d "${CACHE_DIR}/case/processor0/constant/polyMesh" ]] &&
        [[ -d "${CACHE_DIR}/case/processor447/constant/polyMesh" ]]
}

cache_hit=true
if ! cache_valid; then
    if [[ "${REQUIRE_CACHE}" == --require-cache ]]; then
        echo "required cache entry is absent or invalid: ${CACHE_DIR}" >&2
        exit 75
    fi
    cache_hit=false
    TEMP_DIR="${CACHE_DIR}.tmp.$$"
    rm -rf -- "${TEMP_DIR}"
    mkdir -p "${TEMP_DIR}/case"
    cp -a --reflink=auto "${BASE_CASE}/." "${TEMP_DIR}/case/"
    find "${TEMP_DIR}/case" -type d -exec chmod u+w {} +
    find "${TEMP_DIR}/case" -type f -exec chmod u+w {} +

    if [[ "${PROFILE}" == renumber-cuthill-4n448 ]]; then
        cat > "${TEMP_DIR}/case/system/renumberMeshDict" <<'RENUMBER_DICT'
FoamFile
{
    version 2.0;
    format ascii;
    class dictionary;
    object renumberMeshDict;
}
method CuthillMcKee;
writeMaps false;
RENUMBER_DICT
    else
        cat > "${TEMP_DIR}/case/system/renumberMeshDict" <<'RENUMBER_DICT'
FoamFile
{
    version 2.0;
    format ascii;
    class dictionary;
    object renumberMeshDict;
}
method CuthillMcKee;
writeMaps false;
blockSize 32768;
regionFaceOrder false;
blockCoeffs
{
    method scotch;
}
RENUMBER_DICT
    fi

    (
        cd "${TEMP_DIR}/case"
        "${MPIEXEC}" -np "${NUMBER_OF_SUBDOMAINS}" -ppn 112 \
            "${RENUMBER_MESH}" -constant -overwrite -parallel \
            -dict system/renumberMeshDict -fileHandler uncollated \
            > logs/renumberMesh.log 2>&1
    )
    printf '%s\n' "${CACHE_IDENTITY}" > "${TEMP_DIR}/READY"
    jq -n \
        --arg cache_identity "${CACHE_IDENTITY}" \
        --arg prepare_script_sha256 "${SCRIPT_SHA256}" \
        --arg base_cache_identity "${BASE_CACHE_ID}" \
        --arg renumber_mesh_sha256 "${RENUMBER_MESH_SHA256}" \
        --arg mpiexec_sha256 "${MPIEXEC_SHA256}" \
        --arg ordering_profile "${PROFILE}" \
        --argjson number_of_subdomains "${NUMBER_OF_SUBDOMAINS}" \
        '{schema_version:"openfoam-case-cache/v2",cache_identity:$cache_identity,prepare_script_sha256:$prepare_script_sha256,base_cache_identity:$base_cache_identity,renumber_mesh_sha256:$renumber_mesh_sha256,mpiexec_sha256:$mpiexec_sha256,number_of_subdomains:$number_of_subdomains,decomposition_profile:"scotch",ordering_profile:$ordering_profile,file_handler:"uncollated"}' \
        > "${TEMP_DIR}/manifest.json"
    find "${TEMP_DIR}/case" -type f -exec chmod a-w {} +
    find "${TEMP_DIR}/case" -type d -exec chmod a-w {} +
    if [[ -e "${CACHE_DIR}" ]]; then
        rm -rf -- "${TEMP_DIR}"
        TEMP_DIR=
        cache_valid || { echo "invalid cache entry: ${CACHE_DIR}" >&2; exit 65; }
        cache_hit=true
    else
        mv "${TEMP_DIR}" "${CACHE_DIR}"
        TEMP_DIR=
    fi
fi

ln -s "${CACHE_DIR}/case" "${TARGET_CASE}"
printf 'cache_hit=%s\nprepare_script_sha256=%s\ncache_dir=%s\n' \
    "${cache_hit}" "${SCRIPT_SHA256}" "${CACHE_DIR}"
