import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
import sys

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Plot execution time vs parallel units (threads/processes) from results file")
    parser.add_argument("results_file", help="Path to the results CSV file")
    parser.add_argument("--prefix", help="Prefix for output filename", default="")
    parser.add_argument("--suffix", help="Suffix for output filename", default="")
    parser.add_argument("--label", help="Label for the x-axis (e.g., 'Threads', 'Processes', 'Units')", default="Parallel units")
    parser.add_argument("--title", help="Plot title", default="Execution time vs parallel units")
    
    # Parse arguments
    args = parser.parse_args()
    results_file = args.results_file
    prefix = args.prefix
    suffix = args.suffix
    x_label = args.label
    plot_title = args.title
    
    print(f"Using results file: {results_file}")
    print(f"Output prefix: '{prefix}', suffix: '{suffix}'")
    
    try:
        # Load data
        df = pd.read_csv(results_file, names=["units", "size", "time"])
        
        # Data type conversion and cleaning
        df["units"] = pd.to_numeric(df["units"], errors="coerce")
        df["size"] = pd.to_numeric(df["size"], errors="coerce")
        df["time"] = pd.to_numeric(df["time"], errors="coerce")
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
        plt.figure(figsize=(10, 6))
        for size in sorted(df["size"].unique()):
            subset = df[df["size"] == size]
            avg_times = subset.groupby("units")["time"].mean()
            plt.plot(avg_times.index, avg_times.values, marker='o', label=size_label(size))
        
        plt.xlabel(x_label)
        plt.ylabel("Execution time [s]")
        plt.title(plot_title)
        plt.legend(title="Problem size")
        plt.grid(True)
        
        # Create output filename with prefix/suffix
        base_name = "time_vs_units"
        output_file = f"{output_dir}/{prefix}{base_name}{suffix}.png"
        plt.savefig(output_file)
        
        print(f"Plot saved to {output_file}")
        
    except FileNotFoundError:
        print(f"Error: Could not find results file '{results_file}'")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())