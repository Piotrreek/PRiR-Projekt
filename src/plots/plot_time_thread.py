import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
import sys
import numpy as np

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Plot execution time vs parallel units (threads/processes) from results file")
    parser.add_argument("results_file", help="Path to the results CSV file")
    parser.add_argument("--hybrid", action="store_true", help="Process as hybrid results (format: procs,threads,size,time)")
    parser.add_argument("--prefix", help="Prefix for output filename", default="")
    parser.add_argument("--suffix", help="Suffix for output filename", default="")
    parser.add_argument("--label", help="Label for the x-axis (e.g., 'Threads', 'Processes', 'Total Units')",
                        default="Parallel units")
    parser.add_argument("--title", help="Plot title", default="Execution time vs parallel units")
    parser.add_argument("--by-config", action="store_true",
                        help="For hybrid data, plot all process-thread combinations")

    # Parse arguments
    args = parser.parse_args()
    results_file = args.results_file
    prefix = args.prefix
    suffix = args.suffix
    x_label = args.label
    plot_title = args.title
    is_hybrid = args.hybrid
    by_config = args.by_config

    print(f"Using results file: {results_file}")
    if is_hybrid:
        print("Processing as hybrid results (procs,threads,size,time)")
    else:
        print("Processing as standard results (units,size,time)")
    print(f"Output prefix: '{prefix}', suffix: '{suffix}'")

    try:
        # Load data
        if is_hybrid:
            df = pd.read_csv(results_file, names=["procs", "threads", "size", "time"])
            # Calculate total units (processes × threads)
            df["units"] = df["procs"] * df["threads"]
            print("Calculated total units from processes and threads per process")
        else:
            df = pd.read_csv(results_file, names=["units", "size", "time"])

        # Data type conversion and cleaning
        df["size"] = pd.to_numeric(df["size"], errors="coerce")
        df["time"] = pd.to_numeric(df["time"], errors="coerce")
        if is_hybrid:
            df["procs"] = pd.to_numeric(df["procs"], errors="coerce")
            df["threads"] = pd.to_numeric(df["threads"], errors="coerce")
        df["units"] = pd.to_numeric(df["units"], errors="coerce")
        df = df.dropna()

        # Calculate minimum size for better labeling
        min_size = df["size"].min()

        def size_label(size):
            factor = int(round(size / min_size))
            return f"{factor}W" if factor > 1 else "W"

        # Output directory extraction from results file path
        output_dir = os.path.dirname(results_file)
        if not output_dir:
            output_dir = "."

        # --- EXECUTION TIME vs PARALLEL UNITS CHART ---
        plt.figure(figsize=(12, 7))

        if is_hybrid and by_config:
            # For hybrid data with detailed configuration view
            # Create unique labels for each size and proc×thread combination
            unique_sizes = sorted(df["size"].unique())
            colors = plt.cm.tab10(np.linspace(0, 1, len(unique_sizes)))
            color_map = dict(zip(unique_sizes, colors))

            for size in unique_sizes:
                size_df = df[df["size"] == size]
                for _, row in size_df.iterrows():
                    # Create label with both size and configuration
                    config_label = f"{size_label(size)} ({row['procs']}p×{row['threads']}t)"
                    plt.scatter(row["units"], row["time"],
                                color=color_map[size],
                                marker='o', s=80, label=config_label)

            # Add best-fit curves for each problem size to show trend
            for size in unique_sizes:
                size_df = df[df["size"] == size]
                # Sort by unit count for proper line drawing
                size_df = size_df.sort_values("units")
                plt.plot(size_df["units"], size_df["time"],
                         color=color_map[size], linestyle='--',
                         label=f"{size_label(size)} trend")

        elif is_hybrid:
            # Hybrid data but grouped by total unit count
            for size in sorted(df["size"].unique()):
                subset = df[df["size"] == size]
                # Group by total units and average the times
                avg_times = subset.groupby("units")["time"].mean()
                plt.plot(avg_times.index, avg_times.values, marker='o',
                         label=f"{size_label(size)} (avg)")

                # Add scatter points to show individual configurations
                for _, row in subset.iterrows():
                    config_label = f"{row['procs']}p×{row['threads']}t"
                    plt.scatter(row["units"], row["time"], alpha=0.6, s=40)

        else:
            # Standard processing for non-hybrid data
            for size in sorted(df["size"].unique()):
                subset = df[df["size"] == size]
                avg_times = subset.groupby("units")["time"].mean()
                plt.plot(avg_times.index, avg_times.values, marker='o', label=size_label(size))

        plt.xlabel(x_label)
        plt.ylabel("Execution time [s]")
        plt.title(plot_title)

        if is_hybrid and by_config:
            # For detailed config view, put legend outside plot
            plt.legend(title="Configuration", loc='upper left', bbox_to_anchor=(1, 1))
        else:
            plt.legend(title="Problem size")

        plt.grid(True)

        # Add ideal scaling curve (1/x) if appropriate
        if not is_hybrid or not by_config:
            # Find a reference point (1 unit) for each problem size
            for size in sorted(df["size"].unique()):
                subset = df[df["size"] == size]
                if 1 in subset["units"].values:
                    base_time = subset[subset["units"] == 1]["time"].iloc[0]
                    x_range = np.linspace(1, df["units"].max(), 100)
                    ideal_times = [base_time/x for x in x_range]
                    plt.plot(x_range, ideal_times, linestyle=':', color='lightblue',
                             label=f"{size_label(size)} ideal" if size == min_size else "_nolegend_")

        # Create output filename with prefix/suffix
        base_name = "time_vs_units"
        if is_hybrid:
            base_name += "_hybrid"
            if by_config:
                base_name += "_detailed"

        output_file = f"{output_dir}/{prefix}{base_name}{suffix}.png"
        plt.tight_layout()
        plt.savefig(output_file)

        print(f"Plot saved to {output_file}")

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