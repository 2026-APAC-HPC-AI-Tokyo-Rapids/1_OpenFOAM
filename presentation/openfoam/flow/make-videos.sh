#!/bin/bash
# Renders the flow visualization run (Issue #39) with ParaView and encodes the two videos.
#
#   make-videos.sh PARAVIEW_DIR RUN_DIR OUT_DIR MACHINE
#
# PARAVIEW_DIR is an unpacked ParaView-5.13.3-osmesa-MPI-Linux-Python3.10-x86_64 from paraview.org. RUN_DIR is the unpacked
# flow-visualization.tar.zst. MACHINE names where the run ran, for the footer (for example "Genkai, 4 nodes / 448 ranks").
# OUT_DIR gets the frames, stills/, flow-iterations.mp4 and flow-streamlines.mp4.
set -euo pipefail
paraview=$1
run=$2
out=$3
machine=$4
script_dir=$(cd "$(dirname "$0")" && pwd)

# The Mesa in lib/mesa renders without a display. The default lib/libOSMesa.so crashed in glewInit under WSL2.
env -u DISPLAY -u WAYLAND_DISPLAY LD_LIBRARY_PATH="${paraview}/lib/mesa" GALLIUM_DRIVER=llvmpipe "${paraview}/bin/pvbatch-real" --no-mpi "${script_dir}/render.py" "${run}" "${out}" "${machine}"

ffmpeg=$(uvx --from imageio-ffmpeg python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')
for name in iterations streamlines; do "${ffmpeg}" -loglevel error -y -framerate 30 -i "${out}/frames-${name}/%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 18 -preset slow -movflags +faststart "${out}/flow-${name}.mp4"; done
