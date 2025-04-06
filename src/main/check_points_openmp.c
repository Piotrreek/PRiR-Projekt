#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include <math.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>
#include <time.h>

#define TOLERANCE 1e-3

typedef struct
{
    double a, b, c, d, e, f;
} Coeffs;

double f(double x, Coeffs coeffs) {
    double result = 0.0;
    double abs_x = fabs(x);

    // Złożony wielomian z dodatkowymi warstwami
    result += coeffs.a * pow(x, 12) + sin(pow(x, 5));
    result += coeffs.b * pow(x, 10) + cos(pow(x, 3));
    result += coeffs.c * pow(x, 8)  + tan(pow(x, 2));
    result += coeffs.d * pow(x, 6);
    result += coeffs.e * pow(x, 4);
    result += coeffs.f;

    // Wiele złożonych operacji
    for (int i = 0; i < 5; i++) {
        double inner = pow(abs_x + i, 1.0 + (i % 3) / 5.0);
        result +=
            sin(pow(inner, 3)) * cos(pow(inner, 2)) * tan(inner) +
            log1p(inner) +
            sqrt(inner + 1.0) +
            exp(inner / 1000.0) +
            sinh(inner / 1000.0) +
            tanh(inner / 1000.0);
    }

    // Obliczenia zależne od znaku x
    if (x > 0) {
        result += atan(sqrt(x + 1));
    } else {
        result += acos(tanh(fabs(x))); // unikamy domenowych błędów
    }

    // Wymuszenie ciężkich funkcji z dużymi potęgami
    for (int i = 1; i < 10; i++) {
        result += pow(abs_x + i, 1.0 / (2.0 * i + 1.0));
    }

    // Pseudo-losowe komponenty deterministyczne
    double noise = 0.0;
    for (int i = 0; i < 1000; i++) {
        noise += sin(i * x * 0.0001) * cos(i * x * 0.0002);
    }

    result += noise / 100.0;

    return result;
}

int count_valid_points(const char *filename, Coeffs coeffs, int threads, int size)
{
    FILE *file = fopen(filename, "r");
    if (!file)
    {
        perror("Nie można otworzyć pliku");
        return -1;
    }

    int count = 0;

    omp_set_num_threads(threads);
    
    double start = omp_get_wtime();

    double *xs = malloc(sizeof(double) * size);
    double *ys = malloc(sizeof(double) * size);

    while (fscanf(file, "%lf,%lf", &xs[count], &ys[count]) == 2)
    {
        count++;
    }

    fclose(file);

    int match_count = 0;

    #pragma omp parallel for reduction(+ : match_count) schedule(dynamic)
    for (int i = 0; i < count; i++){
        double expected = f(xs[i], coeffs);
        if (fabs(expected - ys[i]) < TOLERANCE)
        {
            match_count++;
        }
    }
    
    free(xs);
    free(ys);

    double end = omp_get_wtime();
    double time_spent = end - start;

    printf("Threads: %d | File: %s | Matches: %d / %d | Time: %lf sec\n", threads, filename, match_count, count, time_spent);

    FILE *result = fopen("out/results.opm.csv", "a");
    fprintf(result, "%d,%d,%lf\n", threads, count, time_spent);
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

    FILE *coeff_file = fopen("point_lists/coeffs.json", "r");
    if (!coeff_file)
    {
        perror("Brak pliku coeffs.json");
        return 1;
    }

    Coeffs coeffs;
    fscanf(coeff_file, "{ \"a\": %lf, \"b\": %lf, \"c\": %lf, \"d\": %lf, \"e\": %lf, \"f\": %lf }", &coeffs.a, &coeffs.b, &coeffs.c, &coeffs.d, &coeffs.e, &coeffs.f);
    fclose(coeff_file);

    FILE *sizes_file = fopen("point_lists/sizes.txt", "r");
    if (!sizes_file)
    {
        perror("Brak pliku sizes.txt");
        return 1;
    }

    int size;

    // Max size of points list

    while (fscanf(sizes_file, "%d", &size) == 1)
    {
        char filename[100];
        sprintf(filename, "point_lists/points_%d.txt", size);

        // Process the file with specified thread count
        count_valid_points(filename, coeffs, thread_count, size);
    }

    fclose(sizes_file);

    return 0;
}