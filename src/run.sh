#!/usr/bin/env bash
set -e

if [[ ! -d "point_lists" ]]; then
    python3 points/generate_points.py
fi

if [[ $OSTYPE == "darwin"* ]]; then
    make -f Makefile.mac
    make -f Makefile.mac benchmark
else
    echo "Implement Makefile for other distros lol"
    exit 1
fi

if [[ ! -d "../.venv" ]]; then
    echo "Create virtual environment"
    exit 1
fi

source ../.venv/bin/activate

# OpenMP
python3 plots/plot_efficiency_and_speedup.py out/results.opm.csv --prefix "openmp_" --label "Number of threads"
python3 plots/plot_time_thread.py out/results.opm.csv --prefix "openmp_" --label "Number of threads" --title "OpenMP thread scaling"

# MPI
python3 plots/plot_efficiency_and_speedup.py out/results.mpi.csv --prefix "mpi_" --label "Number of processes"
python3 plots/plot_time_thread.py out/results.mpi.csv --prefix "mpi_" --label "Number of processes" --title "MPI process scaling"
