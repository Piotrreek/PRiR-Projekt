#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include <math.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>

#define TOLERANCE 1e-3

typedef struct
{
    double a, b, c, d;
} Coeffs;

double f(double x, Coeffs coeffs)
{
    return coeffs.a * x * x * x + coeffs.b * x * x + coeffs.c * x + coeffs.d;
}

void process_file(const char *filename, Coeffs coeffs)
{
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    int total_count = 0;
    double *all_xs = NULL;
    double *all_ys = NULL;

    // Only root reads the file
    if (rank == 0)
    {
        FILE *file = fopen(filename, "r");
        if (!file)
        {
            perror("Nie można otworzyć pliku");
            MPI_Abort(MPI_COMM_WORLD, 1);
            return;
        }

        // Allocate temp arrays (we don't know count yet)
        double *temp_xs = malloc(sizeof(double) * 64000000);
        double *temp_ys = malloc(sizeof(double) * 64000000);

        // Read all points
        while (fscanf(file, "%lf,%lf", &temp_xs[total_count], &temp_ys[total_count]) == 2)
        {
            total_count++;
        }

        // Allocate arrays of exact size
        all_xs = malloc(sizeof(double) * total_count);
        all_ys = malloc(sizeof(double) * total_count);

        // Copy data to correctly sized arrays
        memcpy(all_xs, temp_xs, sizeof(double) * total_count);
        memcpy(all_ys, temp_ys, sizeof(double) * total_count);

        free(temp_xs);
        free(temp_ys);
        fclose(file);
    }

    // Broadcast total count to all processes
    MPI_Bcast(&total_count, 1, MPI_INT, 0, MPI_COMM_WORLD);

    // Calculate local counts and displacements
    int points_per_proc = total_count / size;
    int remainder = total_count % size;

    int *counts = malloc(sizeof(int) * size);
    int *displs = malloc(sizeof(int) * size);

    for (int i = 0; i < size; i++)
    {
        counts[i] = points_per_proc + (i < remainder ? 1 : 0);
        displs[i] = i * points_per_proc + (i < remainder ? i : remainder);
    }

    // Allocate arrays for local points
    int local_count = counts[rank];
    double *local_xs = malloc(sizeof(double) * local_count);
    double *local_ys = malloc(sizeof(double) * local_count);

    // Scatter the points
    MPI_Scatterv(all_xs, counts, displs, MPI_DOUBLE, local_xs, local_count, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Scatterv(all_ys, counts, displs, MPI_DOUBLE, local_ys, local_count, MPI_DOUBLE, 0, MPI_COMM_WORLD);

    // Start timing
    double start_time = MPI_Wtime();

    // Process local points
    int local_matches = 0;
    for (int i = 0; i < local_count; i++)
    {
        double expected = f(local_xs[i], coeffs);
        if (fabs(expected - local_ys[i]) < TOLERANCE)
        {
            local_matches++;
        }
    }

    // Reduce match count
    int total_matches;
    MPI_Reduce(&local_matches, &total_matches, 1, MPI_INT, MPI_SUM, 0, MPI_COMM_WORLD);

    // End timing
    double end_time = MPI_Wtime();
    double elapsed = end_time - start_time;

    // Root process handles output
    if (rank == 0)
    {
        printf("Processes: %d | File: %s | Matches: %d / %d | Time: %lf sec\n",
               size, filename, total_matches, total_count, elapsed);

        // Ensure output directory exists
        struct stat st = {0};
        if (stat("out", &st) == -1)
        {
            mkdir("out", 0777);
        }

        FILE *result = fopen("out/results.mpi.csv", "a");
        fprintf(result, "%d,%d,%lf\n", size, total_count, elapsed);
        fclose(result);

        // Free root's arrays
        free(all_xs);
        free(all_ys);
    }

    // Free local arrays
    free(local_xs);
    free(local_ys);
    free(counts);
    free(displs);
}

int main(int argc, char *argv[])
{
    // Initialize MPI
    MPI_Init(&argc, &argv);

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    Coeffs coeffs;

    // Root process reads coefficients
    if (rank == 0)
    {
        // Ensure output directory exists
        struct stat st = {0};
        if (stat("out", &st) == -1)
        {
            mkdir("out", 0777);
        }

        FILE *coeff_file = fopen("point_lists/coeffs.json", "r");
        if (!coeff_file)
        {
            perror("Brak pliku coeffs.json");
            MPI_Abort(MPI_COMM_WORLD, 1);
            return 1;
        }

        fscanf(coeff_file, "{ \"a\": %lf, \"b\": %lf, \"c\": %lf, \"d\": %lf }",
               &coeffs.a, &coeffs.b, &coeffs.c, &coeffs.d);
        fclose(coeff_file);
    }

    // Broadcast coefficients to all processes
    MPI_Bcast(&coeffs, 4, MPI_DOUBLE, 0, MPI_COMM_WORLD);

    // Root process reads sizes and broadcasts each size
    if (rank == 0)
    {
        FILE *sizes_file = fopen("point_lists/sizes.txt", "r");
        if (!sizes_file)
        {
            perror("Brak pliku sizes.txt");
            MPI_Abort(MPI_COMM_WORLD, 1);
            return 1;
        }

        int file_size;
        while (fscanf(sizes_file, "%d", &file_size) == 1)
        {
            // Broadcast the file size (non-negative value means continue)
            MPI_Bcast(&file_size, 1, MPI_INT, 0, MPI_COMM_WORLD);

            char filename[100];
            sprintf(filename, "point_lists/points_%d.txt", file_size);

            // Process file with all available processes
            process_file(filename, coeffs);
        }

        // Broadcast -1 to signal the end
        int end_signal = -1;
        MPI_Bcast(&end_signal, 1, MPI_INT, 0, MPI_COMM_WORLD);

        fclose(sizes_file);
    }
    else
    {
        // Non-root processes wait for file sizes to be broadcast
        int file_size;
        while (1)
        {
            MPI_Bcast(&file_size, 1, MPI_INT, 0, MPI_COMM_WORLD);

            // If received -1, we're done
            if (file_size < 0)
                break;

            char filename[100];
            sprintf(filename, "point_lists/points_%d.txt", file_size);

            // Process file with all available processes
            process_file(filename, coeffs);
        }
    }

    MPI_Finalize();
    return 0;
}