#define _GNU_SOURCE
#include <immintrin.h>
#include <omp.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <math.h>

static cpu_set_t allowed;
static int cpus[CPU_SETSIZE], packages[CPU_SETSIZE], cores[CPU_SETSIZE], ncores;
static char l3groups[CPU_SETSIZE][512];
static volatile double sink;

static int sysint(int cpu,const char *name) {
 char path[512];int v=-1;snprintf(path,sizeof(path),"/sys/devices/system/cpu/cpu%d/%s",cpu,name);
 FILE*f=fopen(path,"r");if(f){if(fscanf(f,"%d",&v)!=1)v=-1;fclose(f);}return v;
}
static void pin(int cpu) {
 cpu_set_t mask;CPU_ZERO(&mask);CPU_SET(cpu,&mask);
 if(sched_setaffinity(0,sizeof(mask),&mask)){perror("sched_setaffinity");exit(2);}
}
static void topology(void) {
 if(sched_getaffinity(0,sizeof(allowed),&allowed)){perror("sched_getaffinity");exit(2);}
 for(int cpu=0;cpu<CPU_SETSIZE;cpu++)if(CPU_ISSET(cpu,&allowed)) {
  int pkg=sysint(cpu,"topology/physical_package_id"),core=sysint(cpu,"topology/core_id"),seen=0;
  if(pkg<0||core<0){fprintf(stderr,"Unreadable topology\n");exit(2);}
  for(int j=0;j<ncores;j++)if(packages[j]==pkg&&cores[j]==core)seen=1;
  if(seen)continue;
  cpus[ncores]=cpu;packages[ncores]=pkg;cores[ncores]=core;
  char path[512];snprintf(path,sizeof(path),"/sys/devices/system/cpu/cpu%d/cache/index3/shared_cpu_list",cpu);
  FILE*f=fopen(path,"r");if(!f||!fgets(l3groups[ncores],512,f)){fprintf(stderr,"Unreadable L3 sharing\n");exit(2);}
  fclose(f);l3groups[ncores][strcspn(l3groups[ncores],"\n")]=0;ncores++;
 }
}

// Eight independent AVX2 sums hide add latency. The memory clobber forces actual
// loads on every pass. This counts useful read bytes, not hardware bus traffic.
__attribute__((noinline,noclone))
static double read_kernel(const double *a,size_t n,uint64_t reps) {
 __m256d s0=_mm256_setzero_pd(),s1=s0,s2=s0,s3=s0,s4=s0,s5=s0,s6=s0,s7=s0;
 for(uint64_t r=0;r<reps;r++) {
  __asm__ __volatile__("":::"memory");
  for(size_t i=0;i<n;i+=32) {
   s0=_mm256_add_pd(s0,_mm256_load_pd(a+i));s1=_mm256_add_pd(s1,_mm256_load_pd(a+i+4));
   s2=_mm256_add_pd(s2,_mm256_load_pd(a+i+8));s3=_mm256_add_pd(s3,_mm256_load_pd(a+i+12));
   s4=_mm256_add_pd(s4,_mm256_load_pd(a+i+16));s5=_mm256_add_pd(s5,_mm256_load_pd(a+i+20));
   s6=_mm256_add_pd(s6,_mm256_load_pd(a+i+24));s7=_mm256_add_pd(s7,_mm256_load_pd(a+i+28));
  }
 }
 s0=_mm256_add_pd(s0,s1);s2=_mm256_add_pd(s2,s3);s4=_mm256_add_pd(s4,s5);s6=_mm256_add_pd(s6,s7);
 s0=_mm256_add_pd(_mm256_add_pd(s0,s2),_mm256_add_pd(s4,s6));
 double result[4];_mm256_storeu_pd(result,s0);return result[0]+result[1]+result[2]+result[3];
}

static double timed(double**arrays,size_t n,uint64_t reps,int nt,int*selected,double*checksum) {
 double start=0,end=0,sum=0;
 #pragma omp parallel num_threads(nt) reduction(+:sum) shared(start,end)
 {
  int tid=omp_get_thread_num();pin(selected[tid]);
  #pragma omp barrier
  #pragma omp master
  start=omp_get_wtime();
  #pragma omp barrier
  sum+=read_kernel(arrays[tid],n,reps);
  #pragma omp barrier
  #pragma omp master
  end=omp_get_wtime();
 }
 if(sched_setaffinity(0,sizeof(allowed),&allowed)){perror("restore affinity");exit(2);}
 double expected=(double)n*(double)reps*(double)nt;
 if(fabs(sum-expected)>expected*1e-12){fprintf(stderr,"Checksum failure %.17g expected %.17g\n",sum,expected);exit(3);}
 sink=sum;*checksum=sum;return end-start;
}

__attribute__((noinline,noclone))
static double fma_kernel(uint64_t reps) {
 const __m256d a=_mm256_set1_pd(1.0000000001),b=_mm256_set1_pd(1e-10);
 __m256d s0=_mm256_set1_pd(.1),s1=_mm256_set1_pd(.2),s2=_mm256_set1_pd(.3),s3=_mm256_set1_pd(.4);
 __m256d s4=_mm256_set1_pd(.5),s5=_mm256_set1_pd(.6),s6=_mm256_set1_pd(.7),s7=_mm256_set1_pd(.8);
 __m256d s8=_mm256_set1_pd(.9),s9=_mm256_set1_pd(1.),s10=_mm256_set1_pd(1.1),s11=_mm256_set1_pd(1.2);
 for(uint64_t r=0;r<reps;r++) {
  s0=_mm256_fmadd_pd(s0,a,b);s1=_mm256_fmadd_pd(s1,a,b);s2=_mm256_fmadd_pd(s2,a,b);s3=_mm256_fmadd_pd(s3,a,b);
  s4=_mm256_fmadd_pd(s4,a,b);s5=_mm256_fmadd_pd(s5,a,b);s6=_mm256_fmadd_pd(s6,a,b);s7=_mm256_fmadd_pd(s7,a,b);
  s8=_mm256_fmadd_pd(s8,a,b);s9=_mm256_fmadd_pd(s9,a,b);s10=_mm256_fmadd_pd(s10,a,b);s11=_mm256_fmadd_pd(s11,a,b);
 }
 s0=_mm256_add_pd(s0,s1);s2=_mm256_add_pd(s2,s3);s4=_mm256_add_pd(s4,s5);s6=_mm256_add_pd(s6,s7);s8=_mm256_add_pd(s8,s9);s10=_mm256_add_pd(s10,s11);
 s0=_mm256_add_pd(_mm256_add_pd(s0,s2),_mm256_add_pd(s4,s6));s0=_mm256_add_pd(s0,_mm256_add_pd(s8,s10));
 double result[4];_mm256_storeu_pd(result,s0);return result[0]+result[1]+result[2]+result[3];
}

static double timed_fma(uint64_t reps,int nt,int*selected,double*checksum) {
 double start=0,end=0,sum=0;
 #pragma omp parallel num_threads(nt) reduction(+:sum) shared(start,end)
 {
  pin(selected[omp_get_thread_num()]);
  #pragma omp barrier
  #pragma omp master
  start=omp_get_wtime();
  #pragma omp barrier
  sum+=fma_kernel(reps);
  #pragma omp barrier
  #pragma omp master
  end=omp_get_wtime();
 }
 sched_setaffinity(0,sizeof(allowed),&allowed);
 const double a=1.0000000001,b=1e-10;double expected=0,scale=pow(a,(double)reps),offset=b/(a-1);
 for(int i=1;i<=12;i++)expected+=4*nt*((i*.1+offset)*scale-offset);
 if(!isfinite(sum)||fabs(sum-expected)>expected*1e-5){fprintf(stderr,"FMA checksum failure %.17g expected %.17g\n",sum,expected);exit(3);}
 sink=sum;*checksum=sum;return end-start;
}

static void measure_fma(int trial,int nt,int*selected) {
 uint64_t reps=1000000;double seconds,checksum;
 do {
  seconds=timed_fma(reps,nt,selected,&checksum);
  if(seconds<.035)reps=(uint64_t)ceil(reps*fmin(16.0,fmax(2.0,.05/fmax(seconds,1e-9))));
 }while(seconds<.035);
 reps=(uint64_t)fmax(1,ceil(reps*.20/seconds));seconds=timed_fma(reps,nt,selected,&checksum);
 printf("%d,all,FP64_FMA,%d,0,%llu,%.9f,0,%.17g,%.3f\n",trial,nt,(unsigned long long)reps,seconds,checksum,96.*reps*nt/seconds/1e9);fflush(stdout);
}

static void measure(const char *level,size_t bytes,const char *mode,int trial,int nt,int*selected) {
 size_t n=bytes/sizeof(double);double**arrays=calloc(nt,sizeof(*arrays));
 if(!arrays){perror("calloc");exit(2);}
 #pragma omp parallel num_threads(nt)
 {
  int tid=omp_get_thread_num();pin(selected[tid]);
  if(posix_memalign((void**)&arrays[tid],2*1024*1024,bytes)){fprintf(stderr,"allocation failed\n");exit(2);}
  if(bytes>=2*1024*1024 && madvise(arrays[tid],bytes,MADV_HUGEPAGE)){perror("madvise");exit(2);}
  for(size_t i=0;i<n;i++)arrays[tid][i]=1.0;
 }
 sched_setaffinity(0,sizeof(allowed),&allowed);
 double checksum;timed(arrays,n,1,nt,selected,&checksum);
 uint64_t reps=1;double seconds;
 do {
  seconds=timed(arrays,n,reps,nt,selected,&checksum);
  if(seconds<.035){double multiplier=fmin(16.0,fmax(2.0,.05/fmax(seconds,1e-9)));reps=(uint64_t)ceil(reps*multiplier);}
 }while(seconds<.035);
 reps=(uint64_t)fmax(1,ceil((double)reps*.20/seconds));
 seconds=timed(arrays,n,reps,nt,selected,&checksum);
 double useful=(double)bytes*(double)reps*(double)nt;
 printf("%d,%s,%s,%d,%zu,%llu,%.9f,%.3f,%.17g,0\n",trial,mode,level,nt,bytes,(unsigned long long)reps,seconds,useful/seconds/1e9,checksum);fflush(stdout);
 for(int t=0;t<nt;t++){free(arrays[t]);}
 free(arrays);
}

int main(int argc,char**argv) {
 if(argc!=3){fprintf(stderr,"usage: cache_read all|one_per_l3 TRIAL\n");return 2;}
 omp_set_dynamic(0);topology();
 if(ncores!=128){fprintf(stderr,"Expected 128 physical cores, found %d\n",ncores);return 2;}
 int selected[CPU_SETSIZE],nt=0;
 for(int i=0;i<ncores;i++) {
  int used=0;
  if(!strcmp(argv[1],"one_per_l3")){
   for(int j=0;j<i;j++){if(!strcmp(l3groups[i],l3groups[j]))used=1;}
  }else if(strcmp(argv[1],"all")){fprintf(stderr,"unknown mode\n");return 2;}
  if(!used)selected[nt++]=cpus[i];
 }
 fprintf(stderr,"mode=%s physical_cores=%d selected=%d cpu_ids=",argv[1],ncores,nt);
 for(int i=0;i<nt;i++){fprintf(stderr,"%s%d",i?":":"",selected[i]);}
 fprintf(stderr,"\n");
 printf("trial,placement,level,threads,bytes_per_thread,passes,seconds,useful_read_GBps,checksum,FP64_GFLOPs\n");
 struct{const char*name;size_t bytes;}levels[]={{"L1_resident",16*1024},{"L2_resident",256*1024},{"L3_resident",2*1024*1024},{"DRAM",256UL*1024*1024}};
 for(int j=0;j<4;j++){int idx=(j+atoi(argv[2])-1)%4;measure(levels[idx].name,levels[idx].bytes,argv[1],atoi(argv[2]),nt,selected);}
 if(!strcmp(argv[1],"all"))measure_fma(atoi(argv[2]),nt,selected);
 return 0;
}
