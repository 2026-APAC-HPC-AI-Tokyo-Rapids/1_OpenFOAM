Presented slides: presentation/Tokyo Rapids with RIKEN Presentation.pptx (OpenFOAM: slides 5–28)

OpenFOAM Basic (the run to re-run)  
Platform: ASPIRE-2A  
Nodes and ranks: 4 nodes, 512 ranks  
Decomposition: scotch  
Seconds per step: 2.898 (mean of 5 jobs)  
steps: 150  
Cd at the last step: 0.29301591596528520  
Our first 4-node run on this platform, seconds per step: 3.650 (our Baseline: hierarchical, case defaults; slide 7)  
Bottleneck we found, one sentence: Ranks spent 42% of their time waiting in MPI for the slowest rank, because the CPU binding is lost at MPI_Init and hierarchical gives some ranks more work.  
Job id: 25827680.pbs101  
Script (path in this shared folder): openfoam/run/submit.sh 4  
Log (path in this shared folder): openfoam/results/4node/simpleFoam.log

OpenFOAM experiment: multiLevel decomposition  
What changed, one sentence: scotch replaced by multiLevel (4 2 4 16), with scotch at each level: nodes, sockets, NUMA domains, cores.  
Seconds per step, and Cd versus our Basic: 2.873 (mean of 4 jobs, −0.8%). Cd 0.29138777754153217 (−0.56%, decomposition only, so the Sanity check applies, F2)  
steps: 150  
Where the Cd comparison is: slide 35  
Job id: 25682211.pbs101  
Script (path in this shared folder): openfoam/run/submit.sh 4 bonus (with the Basic build)  
Log (path in this shared folder): openfoam/bonus/f3-baseline/4node/simpleFoam.log

OpenFOAM experiment: 14 source patches (Bonus)  
What changed, one sentence: 14 patches to the v2512 source, on top of multiLevel, that cut memory traffic without changing the computation.  
Seconds per step, and Cd versus our Basic: 2.360 (mean of 3 jobs, −18.6%). Cd 0.29138659643758436 (−0.56%, from multiLevel; −0.00041% against the same run without the patches, F3)  
steps: 150  
Where the Cd comparison is: slide 35, openfoam/bonus/README.md  
Job id: 25988381.pbs101  
Script (path in this shared folder): openfoam/run/submit.sh 4 bonus  
Log (path in this shared folder): openfoam/bonus/results/4node/simpleFoam.log

Highlights (OpenFOAM)
- hierarchical → scotch: 3.428 s/step (−6.1%). Slide 11.
- CPU and memory pinning: 2.917 s/step (−14.9%), SD between jobs 2.0% → 0.13%. Slide 13.
- scotch domains (2 4 16), our Basic: 2.898 s/step (−0.7%). Slide 15.
- scotch → multiLevel: 2.873 s/step (−0.8%). Slide 22.
- First four source patches, bit-identical: 2.603 s/step (−9.4%). Slides 23–26.
- Ten more source patches, Cd within 0.0005% (F3): 2.360 s/step (−9.3%), −18.6% from Basic. Slides 23–26.
- Memory bandwidth limit, found by moving the ranks since the counters are not readable: half the cores, the same time; half the memory channels, 2.2 times the time, as STREAM. Slide 20.
- Super-linear strong scaling from 1 to 4 nodes: 4.61 times for Basic, 4.34 times for the Bonus, because each rank's arrays fit in L3. Slides 27 and 95. openfoam/scaling/scaling.txt.
