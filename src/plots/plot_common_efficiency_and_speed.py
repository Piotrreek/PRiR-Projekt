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

        mpi_baseline = mpi_16w[mpi_16w["units"] == 1]["time"].iloc[0] if len(mpi_16w[mpi_16w["units"] == 1]) > 0 else None
        omp_baseline = omp_16w[omp_16w["units"] == 1]["time"].iloc[0] if len(omp_16w[omp_16w["units"] == 1]) > 0 else None
        hybrid_baseline = hybrid_16w[(hybrid_16w["procs"] == 1) & (hybrid_16w["threads"] == 1)]["time"].iloc[0] if len(hybrid_16w[(hybrid_16w["procs"] == 1) & (hybrid_16w["threads"] == 1)]) > 0 else None

        print(f"Baselines - MPI: {mpi_baseline:.6f}s, OpenMP: {omp_baseline:.6f}s, Hybrid: {hybrid_baseline:.6f}s")

        plot_data = []

        if mpi_baseline is not None:
            for _, row in mpi_16w.iterrows():
                speedup = mpi_baseline / row["time"]
                efficiency = speedup / row["units"]
                plot_data.append({
                    "units": row["units"],
                    "speedup": speedup,
                    "efficiency": efficiency,
                    "type": "MPI",
                    "config": "N/A",
                    "time": row["time"]
                })

        if omp_baseline is not None:
            for _, row in omp_16w.iterrows():
                speedup = omp_baseline / row["time"]
                efficiency = speedup / row["units"]
                plot_data.append({
                    "units": row["units"],
                    "speedup": speedup,
                    "efficiency": efficiency,
                    "type": "OpenMP",
                    "config": "N/A",
                    "time": row["time"]
                })

        if hybrid_baseline is not None:
            hybrid_best = {}
            for _, row in hybrid_16w.iterrows():
                units = row["units"]
                time = row["time"]
                if units not in hybrid_best or time < hybrid_best[units]["time"]:
                    speedup = hybrid_baseline / time
                    efficiency = speedup / units
                    hybrid_best[units] = {
                        "units": units,
                        "speedup": speedup,
                        "efficiency": efficiency,
                        "type": "Hybrid",
                        "config": f"{row['procs']}p×{row['threads']}t",
                        "time": time
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
                plt.plot(data_sorted["units"], data_sorted["speedup"],
                         marker=markers[impl_type], color=colors[impl_type],
                         label=impl_type, linewidth=2, markersize=4)

        max_units = results_df["units"].max()
        plt.plot([1, max_units], [1, max_units],
                 linestyle='--', color='gray', alpha=0.7, label='Ideal')

        plt.xlabel("Number of Processing Units")
        plt.ylabel("Speedup S(p) = T(1)/T(p)")
        plt.title("Speedup Comparison for 16W Workload")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()

        speedup_file = "../out/speedup_16W.png"
        plt.savefig(speedup_file, dpi=300, bbox_inches='tight')
        print(f"Speedup plot saved to: {speedup_file}")

        plt.figure(figsize=(12, 6))

        for impl_type in ['MPI', 'OpenMP', 'Hybrid']:
            data = results_df[results_df["type"] == impl_type]
            if not data.empty:
                data_sorted = data.sort_values("units")
                plt.plot(data_sorted["units"], data_sorted["efficiency"],
                         marker=markers[impl_type], color=colors[impl_type],
                         label=impl_type, linewidth=2, markersize=4)

        plt.axhline(y=1.0, linestyle='--', color='gray', alpha=0.7, label='Ideal')

        plt.xlabel("Number of Processing Units")
        plt.ylabel("Efficiency E(p) = S(p)/p")
        plt.title("Efficiency Comparison for 16W Workload")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()

        efficiency_file = "../out/efficiency_16W.png"
        plt.savefig(efficiency_file, dpi=300, bbox_inches='tight')
        print(f"Efficiency plot saved to: {efficiency_file}")

        print("\n=== PERFORMANCE SUMMARY for 16W workload ===")
        print(f"{'Type':<12} {'Config':<12} {'Units':<6} {'Time (s)':<10} {'Speedup':<8} {'Efficiency':<10}")
        print("-" * 70)

        for _, row in results_df.sort_values(["type", "units"]).iterrows():
            config = row.get('config', 'N/A')
            print(f"{row['type']:<12} {config:<12} {row['units']:<6} {row['time']:<10.6f} {row['speedup']:<8.2f} {row['efficiency']:<10.3f}")

        best_speedup = results_df.loc[results_df["speedup"].idxmax()]
        best_efficiency = results_df.loc[results_df["efficiency"].idxmax()]

        print(f"\nBest speedup: {best_speedup['type']} with {best_speedup['units']} units -> {best_speedup['speedup']:.2f}x")
        print(f"Best efficiency: {best_efficiency['type']} with {best_efficiency['units']} units -> {best_efficiency['efficiency']:.3f}")

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