import random
import os
import json

list_sizes = [4000000, 8000000, 16000000, 32000000, 64000000]
output_dir = "point_lists"
os.makedirs(output_dir, exist_ok=True)

# f(x) = ax^3 + bx^2 + cx + d
coeffs = {'a': 1, 'b': -2, 'c': 3, 'd': -4}

def f(x, coeffs):
    return coeffs['a'] * x**3 + coeffs['b'] * x**2 + coeffs['c'] * x + coeffs['d']

# Wirte coefficients to file
with open(os.path.join(output_dir, "coeffs.json"), "w") as coeff_file:
    json.dump(coeffs, coeff_file)

for i, size in enumerate(list_sizes):
    points = []
    for _ in range(size):
        x = random.uniform(-1000, 1000)
        if random.random() < 0.5:  # 50% matches the function
            y = f(x, coeffs)
        else:
            y = f(x, coeffs) + random.uniform(-50, 50)
        points.append((x, y))
    
    file_path = os.path.join(output_dir, f"points_{size}.txt")
    with open(file_path, "w") as points_file:
        for x, y in points:
            points_file.write(f"{x},{y}\n")

with open(os.path.join(output_dir, "sizes.txt"), "w") as size_file:
    for size in list_sizes:
        size_file.write(f"{size}\n")


