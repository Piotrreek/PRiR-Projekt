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
    double a, b, c, d, e, f;
} Coeffs;

double f(double x, Coeffs coeffs)
{
    return coeffs.a * x * x * x * x * x + coeffs.b * x * x * x * x + coeffs.c * x * x * x + coeffs.d * x * x + coeffs.e * x + coeffs.f;
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
            perror("Cannot open file");
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

    // Synchronize all processes before timing computation
    MPI_Barrier(MPI_COMM_WORLD);

    // Start timing - ONLY measuring computation time
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

    // End computation timing
    double end_time = MPI_Wtime();
    double computation_time = end_time - start_time;

    // Collect computation times from all processes
    double max_time;
    MPI_Reduce(&computation_time, &max_time, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    // Now, after timing, reduce the match count
    int total_matches;
    MPI_Reduce(&local_matches, &total_matches, 1, MPI_INT, MPI_SUM, 0, MPI_COMM_WORLD);

    // Root process handles output
    if (rank == 0)
    {
        printf("Processes: %d | File: %s | Matches: %d / %d | Computation Time: %lf sec\n",
               size, filename, total_matches, total_count, max_time);

        FILE *result = fopen("out/results.mpi.csv", "a");
        fprintf(result, "%d,%d,%lf\n", size, total_count, max_time);
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
        FILE *coeff_file = fopen("points/point_lists/coeffs.json", "r");
        if (!coeff_file)
        {
            perror("Missing coeffs.json file");
            MPI_Abort(MPI_COMM_WORLD, 1);
            return 1;
        }

        fscanf(coeff_file, "{ \"a\": %lf, \"b\": %lf, \"c\": %lf, \"d\": %lf, \"e\": %lf, \"f\": %lf }", &coeffs.a, &coeffs.b, &coeffs.c, &coeffs.d, &coeffs.e, &coeffs.f);
        fclose(coeff_file);
    }

    // Broadcast coefficients to all processes
    MPI_Bcast(&coeffs, 6, MPI_DOUBLE, 0, MPI_COMM_WORLD);

    // Root process reads sizes and broadcasts each size
    if (rank == 0)
    {
        FILE *sizes_file = fopen("points/point_lists/sizes.txt", "r");
        if (!sizes_file)
        {
            perror("Missing sizes.txt file");
            MPI_Abort(MPI_COMM_WORLD, 1);
            return 1;
        }

        int file_size;
        while (fscanf(sizes_file, "%d", &file_size) == 1)
        {
            // Broadcast the file size (non-negative value means continue)
            MPI_Bcast(&file_size, 1, MPI_INT, 0, MPI_COMM_WORLD);

            char filename[100];
            sprintf(filename, "points/point_lists/points_%d.txt", file_size);

            // Process file with all available processes
            process_file(filename, coeffs);

            // Add barrier to ensure clean separation between file processing
            MPI_Barrier(MPI_COMM_WORLD);
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
            sprintf(filename, "points/point_lists/points_%d.txt", file_size);

            // Process file with all available processes
            process_file(filename, coeffs);

            // Match the barrier in the root process
            MPI_Barrier(MPI_COMM_WORLD);
        }
    }

    MPI_Finalize();
    return 0;
}