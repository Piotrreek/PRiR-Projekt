import random
import os
import json
import math

list_sizes = [100000, 200000, 400000, 800000, 1600000]
output_dir = "point_lists"
os.makedirs(output_dir, exist_ok=True)

# f(x) = ax^5 + bx^4 + cx^3 + dx^2 + ex + f
coeffs = {'a': 10, 'b': -2, 'c': 17, 'd': -4, 'e': 5, 'f': 1634534}

def f(x, coeffs):
    result = 0.0
    abs_x = abs(x)

    # Złożony wielomian z dodatkowymi warstwami
    result += coeffs['a'] * math.pow(x, 12) + math.sin(math.pow(x, 5))
    result += coeffs['b'] * math.pow(x, 10) + math.cos(math.pow(x, 3))
    result += coeffs['c'] * math.pow(x, 8)  + math.tan(math.pow(x, 2))
    result += coeffs['d'] * math.pow(x, 6)
    result += coeffs['e'] * math.pow(x, 4)
    result += coeffs['f']

    # Wiele złożonych operacji
    for i in range(5):
        inner = math.pow(abs_x + i, 1.0 + (i % 3) / 5.0)
        result += (
            math.sin(inner**3) * math.cos(inner**2) * math.tan(inner) +
            math.log1p(inner) +
            math.sqrt(inner + 1.0) +
            math.exp(inner / 1000.0) +
            math.sinh(inner / 1000.0) +
            math.tanh(inner / 1000.0)
        )
    
    # Obliczenia zależne od znaku x
    if x > 0:
        result += math.atan(math.sqrt(x + 1))
    else:
        result += math.acos(math.tanh(abs_x))

    # Wymuszenie ciężkich funkcji z dużymi potęgami
    for i in range(1, 10):
        result += math.pow(abs_x + i, 1.0 / (2 * i + 1))

    # Pseudo-losowe komponenty deterministyczne
    noise = 0.0
    for i in range(1000):
        noise += math.sin(i * x * 0.0001) * math.cos(i * x * 0.0002)

    result += noise / 100.0

    return result

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


