import pandas as pd
import matplotlib.pyplot as plt
import argparse
import sys
import os

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Plot speedup and efficiency graphs from results file")
    parser.add_argument("results_file", help="Path to the results CSV file")
    parser.add_argument("--units", "-u", type=int, nargs="+", default=[1, 2, 4, 8, 12, 16],
                        help="Parallel unit numbers to include in the analysis (default: 1 2 4 8)")
    parser.add_argument("--prefix", help="Prefix for output filenames", default="")
    parser.add_argument("--suffix", help="Suffix for output filenames", default="")
    parser.add_argument("--label", help="Label for the x-axis (e.g., 'Threads', 'Processes', 'Units')", 
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
    
    print(f"Using results file: {results_file}")
    print(f"Analyzing unit counts: {used_units}")
    print(f"Output prefix: '{prefix}', suffix: '{suffix}'")
    
    try:
        # Load data from results CSV
        df = pd.read_csv(results_file, names=["units", "size", "time"])
        df = df[df["units"].isin(used_units)]
        
        # Ensure numbers are float/int types
        df["units"] = df["units"].astype(int)
        df["size"] = df["size"].astype(int)
        df["time"] = df["time"].astype(float)
        
        # Calculate speedup and efficiency
        speedup_data = []
        efficiency_data = []
        min_size = df["size"].min()
        
        def size_label(size):
            factor = int(round(size / min_size))
            return f"{factor}W" if factor > 1 else "W"
        
        for size in sorted(df["size"].unique()):
            df_size = df[df["size"] == size]
            time_dict = dict(zip(df_size["units"], df_size["time"]))
            
            if 1 not in time_dict:
                print(f"Warning: Size {size} doesn't have single-unit baseline. Skipping.")
                continue # without baseline we can't calculate speedup
                
            base_time = time_dict[1]
            label = size_label(size)
            
            for u in used_units:
                if u in time_dict:
                    sp = base_time / time_dict[u]
                    eff = sp / u
                    speedup_data.append({"units": u, "label": label, "speedup": sp})
                    efficiency_data.append({"units": u, "label": label, "efficiency": eff})
        
        # Convert to DataFrame
        speedup_df = pd.DataFrame(speedup_data)
        efficiency_df = pd.DataFrame(efficiency_data)
        
        # Output directory extraction from results file path
        output_dir = os.path.dirname(results_file)
        if not output_dir:
            output_dir = "."
        
        # --- SPEEDUP CHART ---
        plt.figure(figsize=(10, 6))
        for label in speedup_df["label"].unique():
            subset = speedup_df[speedup_df["label"] == label]
            plt.plot(subset["units"], subset["speedup"], marker='o', label=label)
        
        plt.plot(used_units, used_units, linestyle='--', color='lightblue', label="perfect")
        plt.xlabel(x_label)
        plt.ylabel("Speedup S(p) = T(1)/T(p)")
        plt.title(speedup_title)
        plt.legend(title="Problem size")
        plt.grid(True)
        speedup_file = f"{output_dir}/{prefix}speedup{suffix}.png"
        plt.savefig(speedup_file)
        
        # --- EFFICIENCY CHART ---
        plt.figure(figsize=(10, 6))
        for label in efficiency_df["label"].unique():
            subset = efficiency_df[efficiency_df["label"] == label]
            plt.plot(subset["units"], subset["efficiency"], marker='o', label=label)
        
        plt.plot(used_units, [1.0] * len(used_units), linestyle='--', color='lightblue', label="perfect")
        plt.xlabel(x_label)
        plt.ylabel("Efficiency S(p)/p")
        plt.title(efficiency_title)
        plt.legend(title="Problem size")
        plt.grid(True)
        efficiency_file = f"{output_dir}/{prefix}efficiency{suffix}.png"
        plt.savefig(efficiency_file)
        
        print(f"Plots saved to {speedup_file} and {efficiency_file}")
        
    except FileNotFoundError:
        print(f"Error: Could not find results file '{results_file}'")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())