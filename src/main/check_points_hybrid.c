#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
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

void process_file(const char *filename, Coeffs coeffs, int num_threads)
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
        
        if (!temp_xs || !temp_ys) {
            perror("Memory allocation failed");
            MPI_Abort(MPI_COMM_WORLD, 1);
            return;
        }

        // Read all points
        while (fscanf(file, "%lf,%lf", &temp_xs[total_count], &temp_ys[total_count]) == 2)
        {
            total_count++;
        }
        
        // Allocate arrays of exact size
        all_xs = malloc(sizeof(double) * total_count);
        all_ys = malloc(sizeof(double) * total_count);
        
        if (!all_xs || !all_ys) {
            perror("Memory allocation failed");
            MPI_Abort(MPI_COMM_WORLD, 1);
            return;
        }

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

    // Set number of OpenMP threads
    omp_set_num_threads(num_threads);
    
    // Start timing - ONLY measuring computation time
    double start_time = MPI_Wtime();

    // Process local points with OpenMP parallelism
    int local_matches = 0;
    
    #pragma omp parallel reduction(+:local_matches)
    {
        #pragma omp for schedule(dynamic)
        for (int i = 0; i < local_count; i++)
        {
            double expected = f(local_xs[i], coeffs);
            if (fabs(expected - local_ys[i]) < TOLERANCE)
            {
                local_matches++;
            }
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
        printf("Processes: %d | Threads/Process: %d | File: %s | Matches: %d / %d | Computation Time: %lf sec\n",
               size, num_threads, filename, total_matches, total_count, max_time);

        FILE *result = fopen("out/results.hybrid.csv", "a");
        fprintf(result, "%d,%d,%d,%lf\n", size, num_threads, total_count, max_time);
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
    // Initialize MPI with thread support
    int provided;
    MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);
    
    // Check if we have the required level of thread support
    if (provided < MPI_THREAD_FUNNELED) {
        printf("Warning: The MPI implementation does not provide the required thread level\n");
    }

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    // Check if thread count was provided
    int num_threads = omp_get_max_threads(); // Default to max available threads
    
    if (argc > 1)
    {
        num_threads = atoi(argv[1]);
        if (num_threads < 1)
        {
            if (rank == 0) {
                printf("Invalid thread count: %s. Using max available threads.\n", argv[1]);
            }
            num_threads = omp_get_max_threads();
        }
    }
    else if (rank == 0)
    {
        printf("No thread count specified. Using max available threads (%d).\n", num_threads);
    }

    Coeffs coeffs;

    // Root process reads coefficients
    if (rank == 0)
    {
        FILE *coeff_file = fopen("point_lists/coeffs.json", "r");
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
        FILE *sizes_file = fopen("point_lists/sizes.txt", "r");
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
            sprintf(filename, "point_lists/points_%d.txt", file_size);

            // Process file with all available processes and threads
            process_file(filename, coeffs, num_threads);

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
            sprintf(filename, "point_lists/points_%d.txt", file_size);

            // Process file with all available processes and threads
            process_file(filename, coeffs, num_threads);

            // Match the barrier in the root process
            MPI_Barrier(MPI_COMM_WORLD);
        }
    }

    MPI_Finalize();
    return 0;
}