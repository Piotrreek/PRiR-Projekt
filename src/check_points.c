#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include <math.h>

#define TOLERANCE 1e-3

typedef struct {
    double a, b, c, d;
} Coeffs;

double f(double x, Coeffs coeffs) {
    return coeffs.a*x*x*x + coeffs.b*x*x + coeffs.c*x + coeffs.d;
}

int count_valid_points(const char* filename, Coeffs coeffs, int threads) {
    FILE* file = fopen(filename, "r");
    if (!file) {
        perror("Nie można otworzyć pliku");
        return -1;
    }

    double* xs = malloc(sizeof(double) * 64000000);
    double* ys = malloc(sizeof(double) * 64000000);
    int count = 0;

    while (fscanf(file, "%lf,%lf", &xs[count], &ys[count]) == 2) {
        count++;
    }
    fclose(file);

    int match_count = 0;

    omp_set_num_threads(threads);

    double start = omp_get_wtime();

    #pragma omp parallel for reduction(+:match_count)
    for (int i = 0; i < count; i++) {
        double expected = f(xs[i], coeffs);
        if (fabs(expected - ys[i]) < TOLERANCE) {
            match_count++;
        }
    }

    double end = omp_get_wtime();
    printf("Threads: %d | File: %s | Matches: %d / %d | Time: %f sec\n", threads, filename, match_count, count, end - start);

    FILE* result = fopen("results.csv", "a");
    fprintf(result, "%d,%d,%f\n", threads, count, end - start);
    fclose(result);

    free(xs);
    free(ys);
    return match_count;
}

int main() {
    // Nadpisujemy plik wynikowy
    FILE* result = fopen("results.csv", "w");
    fclose(result);

    FILE* coeff_file = fopen("point_lists/coeffs.json", "r");
    if (!coeff_file) {
        perror("Brak pliku coeffs.json");
        return 1;
    }

    Coeffs coeffs;
    fscanf(coeff_file, "{ \"a\": %lf, \"b\": %lf, \"c\": %lf, \"d\": %lf }", &coeffs.a, &coeffs.b, &coeffs.c, &coeffs.d);
    fclose(coeff_file);

    FILE* sizes_file = fopen("point_lists/sizes.txt", "r");
    if (!sizes_file) {
        perror("Brak pliku sizes.txt");
        return 1;
    }

    int size;
    // Lista liczby wątków do testowania
    int thread_counts[] = {1, 2, 4, 8, 12};
    int num_threads = sizeof(thread_counts) / sizeof(thread_counts[0]);

    while (fscanf(sizes_file, "%d", &size) == 1) {
        char filename[100];
        sprintf(filename, "point_lists/points_%d.txt", size);

        for (int i = 0; i < num_threads; i++) {
            count_valid_points(filename, coeffs, thread_counts[i]);
        }
    }

    fclose(sizes_file);
    return 0;
}
