import random


def generate_distance_matrix(n, seed=0):
    random.seed(seed)
    points = []
    for i in range(n):
        points.append((random.randint(0, 100), random.randint(0, 100)))

    distance_matrix = []
    for i in range(n):
        distance_matrix.append([])
        for j in range(n):
            distance_matrix[i].append(round(((points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2) ** 0.5))

    return distance_matrix


if __name__ == '__main__':
    import print_aux as pa
    n = 6

    matrix = generate_distance_matrix(n)

    print("Distance matrix:")
    pa.matrix_print(matrix)
