import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def main():
    mpi_file = "../out/results.mpi.csv"
    omp_file = "../out/results.opm.csv"
    hybrid_file = "../out/results.hybrid.csv"

    target_size = 1600000
    min_size = 100000

    print(f"Analyzing results for workload size: {target_size} (16W)")

    try:
        mpi_df = pd.read_csv(mpi_file, names=["units", "size", "time"])
        mpi_16w = mpi_df[mpi_df["size"] == target_size].copy()
        mpi_16w["type"] = "MPI"

        omp_df = pd.read_csv(omp_file, names=["units", "size", "time"])
        omp_16w = omp_df[omp_df["size"] == target_size].copy()
        omp_16w["type"] = "OpenMP"

        hybrid_df = pd.read_csv(hybrid_file, names=["procs", "threads", "size", "time"])
        hybrid_16w = hybrid_df[hybrid_df["size"] == target_size].copy()
        hybrid_16w["units"] = hybrid_16w["procs"] * hybrid_16w["threads"]
        hybrid_16w["type"] = "Hybrid"

        print(f"MPI data points for 16W: {len(mpi_16w)}")
        print(f"OpenMP data points for 16W: {len(omp_16w)}")
        print(f"Hybrid data points for 16W: {len(hybrid_16w)}")

        plot_data = []

        for _, row in mpi_16w.iterrows():
            plot_data.append({
                "units": row["units"],
                "time": row["time"],
                "type": "MPI",
                "config": "N/A"
            })

        for _, row in omp_16w.iterrows():
            plot_data.append({
                "units": row["units"],
                "time": row["time"],
                "type": "OpenMP",
                "config": "N/A"
            })

        hybrid_best = {}
        for _, row in hybrid_16w.iterrows():
            units = row["units"]
            time = row["time"]
            if units not in hybrid_best or time < hybrid_best[units]["time"]:
                hybrid_best[units] = {
                    "units": units,
                    "time": time,
                    "type": "Hybrid",
                    "config": f"{row['procs']}p×{row['threads']}t"
                }
        for entry in hybrid_best.values():
            plot_data.append(entry)

        results_df = pd.DataFrame(plot_data)

        if results_df.empty:
            print("No data to plot!")
            return 1

        results_df = results_df.sort_values("units")

        print(f"Total data points to plot: {len(results_df)}")

        plt.figure(figsize=(12, 6))

        colors = {'MPI': 'blue', 'OpenMP': 'red', 'Hybrid': 'green'}
        markers = {'MPI': 'o', 'OpenMP': 's', 'Hybrid': 'o'}

        for impl_type in ['MPI', 'OpenMP', 'Hybrid']:
            data = results_df[results_df["type"] == impl_type]
            if not data.empty:
                data_sorted = data.sort_values("units")
                plt.plot(data_sorted["units"], data_sorted["time"],
                         marker=markers[impl_type], color=colors[impl_type],
                         label=impl_type, linewidth=2, markersize=4)

        max_units = results_df["units"].max()
        if 1 in results_df["units"].values:
            base_time = results_df[results_df["units"] == 1]["time"].iloc[0]
            x_range = np.linspace(1, max_units, 100)
            ideal_times = [base_time/x for x in x_range]
            plt.plot(x_range, ideal_times, linestyle='--', color='gray', alpha=0.7, label='Ideal')

        plt.xlabel("Number of Processing Units")
        plt.ylabel("Execution time [s]")
        plt.title("Execution Time vs Processing Units for 16W Workload")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()

        time_file = "../out/time_16W.png"
        plt.savefig(time_file, dpi=300, bbox_inches='tight')
        print(f"Time plot saved to: {time_file}")

        print("\n=== TIME SUMMARY for 16W workload ===")
        print(f"{'Type':<12} {'Config':<12} {'Units':<6} {'Time (s)':<10}")
        print("-" * 50)

        for _, row in results_df.sort_values(["type", "units"]).iterrows():
            config = row.get('config', 'N/A')
            print(f"{row['type']:<12} {config:<12} {row['units']:<6} {row['time']:<10.6f}")

        best_time = results_df.loc[results_df["time"].idxmin()]

        print(f"\nBest time: {best_time['type']} with {best_time['units']} units -> {best_time['time']:.6f}s")

        return 0

    except FileNotFoundError as e:
        print(f"Error: Could not find file {e.filename}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())