#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include <math.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>

#define TOLERANCE 1e-3

typedef struct
{
    double a, b, c, d, e, f;
} Coeffs;

double f(double x, Coeffs coeffs)
{
    return coeffs.a * x * x * x * x * x + coeffs.b * x * x * x * x + coeffs.c * x * x * x + coeffs.d * x * x + coeffs.e * x + coeffs.f;
}

int count_valid_points(const char *filename, Coeffs coeffs, int threads, double *xs, double *ys)
{
    FILE *file = fopen(filename, "r");
    if (!file)
    {
        perror("Nie można otworzyć pliku");
        return -1;
    }

    int count = 0;

    while (fscanf(file, "%lf,%lf", &xs[count], &ys[count]) == 2)
    {
        count++;
    }
    fclose(file);

    int match_count = 0;

    omp_set_num_threads(threads);

    double start = omp_get_wtime();

#pragma omp parallel for reduction(+ : match_count)
    for (int i = 0; i < count; i++)
    {
        double expected = f(xs[i], coeffs);
        if (fabs(expected - ys[i]) < TOLERANCE)
        {
            match_count++;
        }
    }

    double end = omp_get_wtime();
    printf("Threads: %d | File: %s | Matches: %d / %d | Time: %lf sec\n", threads, filename, match_count, count, end - start);

    FILE *result = fopen("out/results.opm.csv", "a");
    fprintf(result, "%d,%d,%lf\n", threads, count, end - start);
    fclose(result);

    return match_count;
}

int main(int argc, char *argv[])
{
    // Check if thread count was provided
    int thread_count = 1; // Default to 1 thread

    if (argc > 1)
    {
        thread_count = atoi(argv[1]);
        if (thread_count < 1)
        {
            printf("Invalid thread count: %s. Using 1 thread.\n", argv[1]);
            thread_count = 1;
        }
    }
    else
    {
        printf("No thread count specified. Using 1 thread.\n");
    }

    FILE *coeff_file = fopen("points/point_lists/coeffs.json", "r");
    if (!coeff_file)
    {
        perror("Brak pliku coeffs.json");
        return 1;
    }

    Coeffs coeffs;
    fscanf(coeff_file, "{ \"a\": %lf, \"b\": %lf, \"c\": %lf, \"d\": %lf, \"e\": %lf, \"f\": %lf }", &coeffs.a, &coeffs.b, &coeffs.c, &coeffs.d, &coeffs.e, &coeffs.f);
    fclose(coeff_file);

    FILE *sizes_file = fopen("points/point_lists/sizes.txt", "r");
    if (!sizes_file)
    {
        perror("Brak pliku sizes.txt");
        return 1;
    }

    int size;

    // Max size of points list
    double *xs = malloc(sizeof(double) * 64000000);
    double *ys = malloc(sizeof(double) * 64000000);

    while (fscanf(sizes_file, "%d", &size) == 1)
    {
        char filename[100];
        sprintf(filename, "points/point_lists/points_%d.txt", size);

        // Process the file with specified thread count
        count_valid_points(filename, coeffs, thread_count, xs, ys);
    }

    fclose(sizes_file);
    free(xs);
    free(ys);

    return 0;
}