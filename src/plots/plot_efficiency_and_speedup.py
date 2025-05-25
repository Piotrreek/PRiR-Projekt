import pandas as pd
import matplotlib.pyplot as plt
import argparse
import sys
import os
import numpy as np

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Plot speedup and efficiency graphs from results file")
    parser.add_argument("results_file", help="Path to the results CSV file")
    parser.add_argument("--hybrid", action="store_true", help="Process as hybrid results (format: procs,threads,size,time)")
    parser.add_argument("--units", "-u", type=int, nargs="+", default=[1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                        help="Parallel unit numbers to include in the analysis (default: 1-16)")
    parser.add_argument("--prefix", help="Prefix for output filenames", default="")
    parser.add_argument("--suffix", help="Suffix for output filenames", default="")
    parser.add_argument("--label", help="Label for the x-axis (e.g., 'Threads', 'Processes', 'Total Units')",
                        default="Parallel units")
    parser.add_argument("--title-speedup", help="Title for speedup plot",
                        default="Speedup relative to parallel unit count")
    parser.add_argument("--title-efficiency", help="Title for efficiency plot",
                        default="Efficiency relative to parallel unit count")

    # Parse arguments
    args = parser.parse_args()

    # Use the arguments
    results_file = args.results_file
    used_units = args.units
    prefix = args.prefix
    suffix = args.suffix
    x_label = args.label
    speedup_title = args.title_speedup
    efficiency_title = args.title_efficiency
    is_hybrid = args.hybrid

    print(f"Using results file: {results_file}")
    if is_hybrid:
        print("Processing as hybrid results (procs,threads,size,time)")
    else:
        print("Processing as standard results (units,size,time)")
    print(f"Analyzing unit counts: {used_units}")
    print(f"Output prefix: '{prefix}', suffix: '{suffix}'")

    try:
        # Load data from results CSV with appropriate column names
        if is_hybrid:
            df = pd.read_csv(results_file, names=["procs", "threads", "size", "time"])
            # Calculate total units (processes × threads)
            df["units"] = df["procs"] * df["threads"]
            print("Calculated total units from processes and threads per process")
        else:
            df = pd.read_csv(results_file, names=["units", "size", "time"])

        # Filter units if needed
        if not is_hybrid:  # For hybrid data, we'll keep all combinations
            df = df[df["units"].isin(used_units)]
        else:
            # For hybrid data, we'll filter based on total units
            df = df[df["units"].isin(used_units)]

        # Ensure numbers are float/int types
        df["size"] = df["size"].astype(int)
        df["time"] = df["time"].astype(float)
        if is_hybrid:
            df["procs"] = df["procs"].astype(int)
            df["threads"] = df["threads"].astype(int)
        df["units"] = df["units"].astype(int)

        # Calculate speedup and efficiency
        speedup_data = []
        efficiency_data = []
        min_size = df["size"].min()

        def size_label(size):
            factor = int(round(size / min_size))
            return f"{factor}W" if factor > 1 else "W"

        for size in sorted(df["size"].unique()):
            df_size = df[df["size"] == size]

            # Find the baseline time (sequential execution)
            # For hybrid data, look for 1 proc × 1 thread, or the smallest total units
            if is_hybrid:
                baseline_row = df_size[(df_size["procs"] == 1) & (df_size["threads"] == 1)]
                if baseline_row.empty:
                    # Use the smallest total units as baseline
                    min_units = df_size["units"].min()
                    baseline_row = df_size[df_size["units"] == min_units].iloc[0]
                    print(f"Warning: Size {size} doesn't have 1×1 configuration. Using {min_units} units as baseline.")
                else:
                    baseline_row = baseline_row.iloc[0]
                base_time = baseline_row["time"]
                base_units = baseline_row["units"]
            else:
                # Standard processing - look for units=1
                if 1 not in df_size["units"].values:
                    print(f"Warning: Size {size} doesn't have single-unit baseline. Skipping.")
                    continue  # Without baseline we can't calculate speedup
                base_time = df_size[df_size["units"] == 1]["time"].iloc[0]
                base_units = 1

            label = size_label(size)

            # Calculate speedup and efficiency for each configuration
            for _, row in df_size.iterrows():
                units = row["units"]
                time = row["time"]

                # Skip any configurations with units not in used_units
                if units not in used_units:
                    continue

                # For hybrid data, create more descriptive labels
                if is_hybrid:
                    config_label = f"{label} ({row['procs']}p×{row['threads']}t)"
                else:
                    config_label = label

                sp = base_time / time
                eff = sp / (units / base_units)  # Adjust efficiency calculation for the base units

                speedup_data.append({
                    "units": units,
                    "label": config_label,
                    "speedup": sp,
                    "base_label": label,  # Store base label for grouping
                    "size": size,  # Store actual size value
                    "procs": row["procs"] if is_hybrid else None,
                    "threads": row["threads"] if is_hybrid else None
                })

                efficiency_data.append({
                    "units": units,
                    "label": config_label,
                    "efficiency": eff,
                    "base_label": label,  # Store base label for grouping
                    "size": size,  # Store actual size value
                    "procs": row["procs"] if is_hybrid else None,
                    "threads": row["threads"] if is_hybrid else None
                })

        # Convert to DataFrame
        speedup_df = pd.DataFrame(speedup_data)
        efficiency_df = pd.DataFrame(efficiency_data)

        # Check if we have any data to plot
        if speedup_df.empty:
            print("No data points to plot. Check if your units filter matches data in the file.")
            return 1

        # Output directory extraction from results file path
        output_dir = os.path.dirname(results_file)
        if not output_dir:
            output_dir = "."

        # --- SPEEDUP CHART ---
        plt.figure(figsize=(12, 7))

        # Define colors for different problem sizes
        unique_sizes = sorted(speedup_df["size"].unique())
        colors = plt.cm.tab10(np.linspace(0, 1, len(unique_sizes)))
        color_map = dict(zip(unique_sizes, colors))

        # For hybrid mode, group by problem size to simplify the plot
        if is_hybrid:
            # Group the data points by size for cleaner plotting
            for size in unique_sizes:
                size_data = speedup_df[speedup_df["size"] == size]
                size_label_str = size_label(size)

                # Sort by units to ensure proper line order
                size_data = size_data.sort_values("units")

                plt.plot(size_data["units"], size_data["speedup"],
                         marker='o', color=color_map[size], label=size_label_str)
        else:
            # Standard plot for non-hybrid data
            for label in speedup_df["base_label"].unique():
                subset = speedup_df[speedup_df["base_label"] == label]
                subset = subset.sort_values("units")  # Ensure points are connected in order
                plt.plot(subset["units"], subset["speedup"], marker='o', label=label)

        # Add perfect scaling line
        max_units = max(speedup_df["units"])
        plt.plot([0, max_units], [0, max_units], linestyle='--', color='lightgray', label="perfect")

        plt.xlabel(x_label)
        plt.ylabel("Speedup S(p) = T(1)/T(p)")
        plt.title(speedup_title)
        plt.legend(title="Problem size" if not is_hybrid else "Problem size",
                   loc='upper left', bbox_to_anchor=(1, 1))
        plt.grid(True)
        speedup_file = f"{output_dir}/{prefix}speedup{suffix}.png"
        plt.tight_layout()
        plt.savefig(speedup_file)

        # --- EFFICIENCY CHART ---
        plt.figure(figsize=(12, 7))

        # For hybrid mode, group by problem size to simplify the plot
        if is_hybrid:
            # Group the data points by size for cleaner plotting
            for size in unique_sizes:
                size_data = efficiency_df[efficiency_df["size"] == size]
                size_label_str = size_label(size)

                # Sort by units to ensure proper line order
                size_data = size_data.sort_values("units")

                plt.plot(size_data["units"], size_data["efficiency"],
                         marker='o', color=color_map[size], label=size_label_str)

        else:
            # Standard plot for non-hybrid data
            for label in efficiency_df["base_label"].unique():
                subset = efficiency_df[efficiency_df["base_label"] == label]
                subset = subset.sort_values("units")  # Ensure points are connected in order
                plt.plot(subset["units"], subset["efficiency"], marker='o', label=label)

        # Add perfect efficiency line
        plt.plot([0, max_units], [1.0, 1.0], linestyle='--', color='lightgray', label="perfect")

        plt.xlabel(x_label)
        plt.ylabel("Efficiency S(p)/p")
        plt.title(efficiency_title)
        plt.legend(title="Problem size",
                   loc='upper left', bbox_to_anchor=(1, 1))
        plt.grid(True)
        efficiency_file = f"{output_dir}/{prefix}efficiency{suffix}.png"
        plt.tight_layout()
        plt.savefig(efficiency_file)

        print(f"Plots saved to {speedup_file} and {efficiency_file}")

    except FileNotFoundError:
        print(f"Error: Could not find results file '{results_file}'")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())