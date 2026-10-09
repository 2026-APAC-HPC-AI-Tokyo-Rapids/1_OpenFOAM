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
  aspire2a_mpi_transport=${CRAYPE_NETWORK_TARGET:?Cray PE network target is required}
  aspire2a_mpi_library_root="${CRAY_MPICH_DIR}/lib"
  case "${aspire2a_mpi_transport}" in
    ucx) aspire2a_transport_version="UCX_VERSION=$(ucx_info -v | sed -n 's/^# Library version: //p')" ;;
    ofi) aspire2a_transport_version="LIBFABRIC_VERSION=$(fi_info --version | sed -n 's/^libfabric: //p')" ;;
    *) printf 'unsupported Cray PE network target: %s\n' "${aspire2a_mpi_transport}" >&2; return 64 ;;
  esac
  aspire2a_aocl_libm="${AOCL_ROOT}/lib/libalm.so"
  aspire2a_aocl_libmem="${AOCL_ROOT}/lib/libaocl-libmem.so"
  command -v "${aspire2a_cc}" >/dev/null
  command -v "${aspire2a_cxx}" >/dev/null
  command -v "${aspire2a_mpi_launcher}" >/dev/null
  test -n "${AOCL_ROOT:?AOCL module did not set AOCL_ROOT}"
  test -r "${aspire2a_aocl_libm}"
  test -r "${aspire2a_aocl_libmem}"
  test -n "${CRAY_MPICH_VERSION:?PrgEnv did not load Cray MPICH}"
  [[ "${aspire2a_transport_version}" != *= ]]
  test "${aspire2a_network_module}" = "craype-network-${aspire2a_mpi_transport}"
  module -t list 2>&1 | grep -Fxq "${aspire2a_network_module}"
  module -t list 2>&1 | grep -Fxq "${aspire2a_mpi_module}"
}

# lddの出力が、選んだtransportのCray MPICHだけにlinkしていることを確かめる。
aspire2a_check_mpi_link() {
  local listing=${1:?ldd listing is required}
  grep -Fq "${aspire2a_mpi_library_root}/libmpi_" "${listing}"
  case "${aspire2a_mpi_transport}" in
    ucx)
      for ucx_library in libucp.so libucs.so libuct.so; do grep -Fq "${ucx_library}" "${listing}"; done
      if grep -q 'libfabric[.]so' "${listing}"; then printf 'UCX版が%sでlibfabricにlinkしています\n' "${listing}" >&2; return 1; fi
      ;;
    ofi)
      grep -q 'libfabric[.]so' "${listing}"
      if grep -q 'libucp[.]so' "${listing}"; then printf 'OFI版が%sでUCXにlinkしています\n' "${listing}" >&2; return 1; fi
      ;;
  esac
}
