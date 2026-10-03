#!/usr/bin/env bash

aspire2a_load_toolchain() {
  local selected=${1:?ASPIRE-2A toolchain is required}

  module purge
  case "${selected}" in
    gnu)
      module load PrgEnv-gnu/8.3.3 craype-x86-milan aocl/4.0.0-gcc11.2
      aspire2a_wm_compiler=Gcc
      aspire2a_cc=gcc
      aspire2a_cxx=g++
      aspire2a_aocl_module=aocl/4.0.0-gcc11.2
      ;;
    aocc)
      module load aocc/5.0 PrgEnv-aocc/8.3.3 craype-x86-milan aocl/5.1.0-aocc5.0
      aspire2a_wm_compiler=Amd
      aspire2a_cc=clang
      aspire2a_cxx=clang++
      aspire2a_aocl_module=aocl/5.1.0-aocc5.0
      ;;
    *)
      printf 'unsupported ASPIRE-2A toolchain: %s\n' "${selected}" >&2
      return 64
      ;;
  esac

  module swap craype-network-ofi "${aspire2a_network_module:?ASPIRE-2A network module is required}"
  module swap cray-mpich "${aspire2a_mpi_module:?ASPIRE-2A Cray MPICH module is required}"
  aspire2a_mpi_launcher=mpiexec
  aspire2a_wm_mplib=CRAY-MPICH
  aspire2a_mpi_transport=ucx
  aspire2a_mpi_library_root="${CRAY_MPICH_DIR}/lib"
  aspire2a_ucx_info=$(command -v ucx_info)
  aspire2a_ucx_version=$("${aspire2a_ucx_info}" -v | sed -n 's/^# Library version: //p')
  aspire2a_aocl_libm="${AOCL_ROOT}/lib/libalm.so"
  aspire2a_aocl_libmem="${AOCL_ROOT}/lib/libaocl-libmem.so"
  command -v "${aspire2a_cc}" >/dev/null
  command -v "${aspire2a_cxx}" >/dev/null
  command -v "${aspire2a_mpi_launcher}" >/dev/null
  test -n "${AOCL_ROOT:?AOCL module did not set AOCL_ROOT}"
  test -r "${aspire2a_aocl_libm}"
  test -r "${aspire2a_aocl_libmem}"
  test -n "${CRAY_MPICH_VERSION:?PrgEnv did not load Cray MPICH}"
  test -n "${aspire2a_ucx_version}"
  test "${CRAYPE_NETWORK_TARGET:?Cray PE network target is required}" = ucx
  module -t list 2>&1 | grep -Fxq "${aspire2a_network_module}"
  module -t list 2>&1 | grep -Fxq "${aspire2a_mpi_module}"
}
