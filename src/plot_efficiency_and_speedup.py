import pandas as pd
import matplotlib.pyplot as plt

# Tylko te wątki są używane w C
used_threads = [1, 2, 4, 8, 12]

# Wczytaj dane z results.csv
df = pd.read_csv("results.csv", names=["threads", "size", "time"])
df = df[df["threads"].isin(used_threads)]

# Upewnij się, że liczby są typu float/int
df["threads"] = df["threads"].astype(int)
df["size"] = df["size"].astype(int)
df["time"] = df["time"].astype(float)

# Oblicz speedup i efficiency
speedup_data = []
efficiency_data = []

min_size = df["size"].min()

def size_label(size):
    factor = int(round(size / min_size))
    return f"{factor}W" if factor > 1 else "W"

for size in sorted(df["size"].unique()):
    df_size = df[df["size"] == size]
    time_dict = dict(zip(df_size["threads"], df_size["time"]))
    if 1 not in time_dict:
        continue  # bez wzorca nie obliczymy speedupu

    base_time = time_dict[1]
    label = size_label(size)

    for t in used_threads:
        if t in time_dict:
            sp = base_time / time_dict[t]
            eff = sp / t
            speedup_data.append({"threads": t, "label": label, "speedup": sp})
            efficiency_data.append({"threads": t, "label": label, "efficiency": eff})

# Konwertuj do DataFrame
speedup_df = pd.DataFrame(speedup_data)
efficiency_df = pd.DataFrame(efficiency_data)

# --- WYKRES PRZYSPIESZENIA ---
plt.figure()
for label in speedup_df["label"].unique():
    subset = speedup_df[speedup_df["label"] == label]
    plt.plot(subset["threads"], subset["speedup"], marker='o', label=label)

plt.plot(used_threads, used_threads, linestyle='--', color='lightblue', label="perfect")
plt.xlabel("Liczba wątków")
plt.ylabel("Przyspieszenie S(p) = T(1)/T(p)")
plt.title("Przyspieszenie względem liczby wątków")
plt.legend(title="Rozmiar zadania")
plt.grid(True)
plt.savefig("speedup_combined.png")

# --- WYKRES EFEKTYWNOŚCI ---
plt.figure()
for label in efficiency_df["label"].unique():
    subset = efficiency_df[efficiency_df["label"] == label]
    plt.plot(subset["threads"], subset["efficiency"], marker='o', label=label)

plt.plot(used_threads, [1.0] * len(used_threads), linestyle='--', color='lightblue', label="perfect")
plt.xlabel("Liczba wątków")
plt.ylabel("Efektywność S(p)/p")
plt.title("Efektywność względem liczby wątków")
plt.legend(title="Rozmiar zadania")
plt.grid(True)
plt.savefig("efficiency_combined.png")

plt.show()
