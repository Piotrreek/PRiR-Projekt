# Navigate to the script's directory
Set-Location -Path $PSScriptRoot

# Paths
$exe = "check_points_openmp.exe"
$src = "main/check_points_openmp.c"
$outCsv = "out/results.opm.csv"

# Clean previous results
if (Test-Path $outCsv) {
    Remove-Item $outCsv
}

# Ensure output folder exists
$outDir = "out"
if (!(Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}

# Compile with GCC and OpenMP
Write-Host "Compiling $src..."
$compileCmd = "gcc -fopenmp -o $exe $src"
Invoke-Expression $compileCmd

if (!(Test-Path $exe)) {
    Write-Host "Compilation failed!"
    exit 1
}

# Run with multiple thread counts
$threadCounts = @(1, 2, 4, 8)
foreach ($threads in $threadCounts) {
    Write-Host "Running with $threads thread(s)..."
    & .\$exe $threads
}

# Paths
$exe = "check_points_mpi.exe"
$src = "main/check_points_mpi.c"
$outCsv = "out/results.mpi.csv"

# Clean previous results
if (Test-Path $outCsv) {
    Remove-Item $outCsv
}

# Compile with GCC and OpenMP
Write-Host "Compiling $src..."
$source = "D:\Studia\PRiR-Projekt\src\main\check_points_mpi.c"
$include = "D:\Studia\PRiR-Projekt\MS_MPI\SDK\Include\"
$lib = "D:\Studia\PRiR-Projekt\MS_MPI\SDK\Lib\x64\"
$output = "D:\Studia\PRiR-Projekt\src\check_points_mpi.exe"

$compileCmd = "gcc -g `"$source`" -I`"$include`" -L`"$lib`" -lmsmpi -o `"$output`""
Invoke-Expression $compileCmd

Invoke-Expression $compileCmd

if (!(Test-Path $exe)) {
    Write-Host "Compilation failed!"
    exit 1
}

# Run with multiple thread counts
$threadCounts = @(1, 2, 4, 8)
foreach ($threads in $threadCounts) {
    Write-Host "Running with $threads thread(s)..."
    & mpiexec -n $threads .\$exe
}

# OpenMP
Invoke-Expression "python3 plots/plot_efficiency_and_speedup.py out/results.opm.csv --prefix `"openmp_`" --label `"Number of threads`""
Invoke-Expression "python3 plots/plot_time_thread.py out/results.opm.csv --prefix `"openmp_`" --label `"Number of threads`" --title `"OpenMP thread scaling`""

# MPI
Invoke-Expression "python3 plots/plot_efficiency_and_speedup.py out/results.mpi.csv --prefix `"mpi_`" --label `"Number of processes`""
Invoke-Expression "python3 plots/plot_time_thread.py out/results.mpi.csv --prefix `"mpi_`" --label `"Number of processes`" --title `"MPI process scaling`""

Write-Host " All runs completed."
