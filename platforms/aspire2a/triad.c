/* ノードのDRAM帯域をtriad（c[i] = a[i] + 3 b[i]）で測る（Issue #61）。STREAMと同じく1要素24 byte
 * （読み込み2、書き込み1）で数え、書き込み時の追加の読み込みは数えない。スレッドの配置はOMP_PLACESで与える。
 * 各スレッドが自分の受け持ちを最初に書くので、ページはそのスレッドのNUMAノードに置かれる。 */
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    const size_t n = (size_t)1 << 27; /* 1配列1 GiB、3配列でノードのL3（512 MiB）の6倍 */
    double *a = malloc(n * sizeof *a);
    double *b = malloc(n * sizeof *b);
    double *c = malloc(n * sizeof *c);
    if (a == NULL || b == NULL || c == NULL) {
        return 1;
    }
#pragma omp parallel for schedule(static)
    for (size_t i = 0; i < n; i++) {
        a[i] = 1.0;
        b[i] = 2.0;
        c[i] = 0.0;
    }
    double best = 1e30;
    for (int k = 0; k < 20; k++) {
        const double start = omp_get_wtime();
#pragma omp parallel for schedule(static)
        for (size_t i = 0; i < n; i++) {
            c[i] = a[i] + 3.0 * b[i];
        }
        const double elapsed = omp_get_wtime() - start;
        if (elapsed < best) {
            best = elapsed;
        }
    }
    printf("threads=%d best_GBps=%.1f check=%.1f\n", omp_get_max_threads(), 24.0 * (double)n / best / 1e9, c[n / 2]);
    free(a);
    free(b);
    free(c);
    return 0;
}
