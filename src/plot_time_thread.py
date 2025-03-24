import pandas as pd
import matplotlib.pyplot as plt

# Wczytaj dane
df = pd.read_csv("results.csv", names=["threads", "size", "time"])

# Konwersja typów i czyszczenie danych
df["threads"] = pd.to_numeric(df["threads"], errors="coerce")
df["size"] = pd.to_numeric(df["size"], errors="coerce")
df["time"] = pd.to_numeric(df["time"], errors="coerce")
df = df.dropna()

# --- WYKRES CZASU vs LICZBA WĄTKÓW ---
plt.figure()
for size in sorted(df["size"].unique()):
    subset = df[df["size"] == size]
    avg_times = subset.groupby("threads")["time"].mean()
    plt.plot(avg_times.index, avg_times.values, marker='o', label=f"size={size}")

plt.xlabel("Liczba wątków")
plt.ylabel("Czas wykonania [s]")
plt.title("Czas wykonania w zależności od liczby wątków")
plt.legend(title="Rozmiar listy")
plt.grid(True)
plt.savefig("czas_vs_threads.png")