import random
import os


class TTPInstanceLoader:
    def __init__(self, directory='instancesTTP', value_separator=','):
        self.instances = {}
        self.sep = value_separator
        self.directory = os.path.join(os.getcwd(), directory)

    def load(self, path):
        try:
            with open(path, 'r') as file:
                lines = [line.strip() for line in file.readlines()]
        except FileNotFoundError:
            print(f'File {path} not found.')
            return

        n = int(lines[0])
        matrix = [[int(x) for x in line.split(self.sep)]
                  for line in lines[1:]]

        seed = int(path.split('/')[-1].split('.')[0].split('_')[-1])

        self.instances[n] = {
            'seed': seed,
            'matrix': matrix
        }

        print(f'Instance N = {n} loaded with seed {seed}.\n')

        return matrix

    def single_create(self, n, seed, grid_size=100):
        random.seed(seed)
        points = []
        for i in range(n):
            points.append((random.randint(0, grid_size),
                           random.randint(0, grid_size)))

        distance_matrix = []
        for i in range(n):
            distance_matrix.append([])
            for j in range(n):
                dist = ((points[i][0] - points[j][0]) ** 2 +
                        (points[i][1] - points[j][1]) ** 2) ** 0.5
                distance_matrix[i].append(round(dist))

        self.instances[n] = {
            'seed': seed,
            'matrix': distance_matrix
        }

        print(f'Instance N = {n} created with seed {seed}.')
        try:
            os.mkdir(self.directory)
        except FileExistsError:
            pass

        try:
            os.mkdir(os.path.join(self.directory, f'N_{n}'))
        except FileExistsError:
            pass

        path = os.path.join(self.directory, f'N_{n}', f'N_{n}_{seed}.txt')
        with open(path, 'w') as file:
            file.write(f'{n}\n')
            for i in range(n):
                row = self.sep.join([str(x) for x in distance_matrix[i]])
                file.write(f'{row}\n')

        print('Instance saved.\n')

    def poblate(self, n, instances=20):
        for _ in range(instances):
            seed = random.randint(0, 1000)
            self.single_create(n, seed)

    def matrix_print(self, matrix):
        print(" " * 4, end="")
        for i in range(len(matrix[0])):
            print("{:<4}".format(i), end="")
        print()

        for i in range(len(matrix)):
            print("{:<4}".format(i), end="")
            for j in range(len(matrix[0])):
                print("{:<4}".format(matrix[i][j]), end="")
            print()


if __name__ == '__main__':
    loader = TTPInstanceLoader()
    N = [4, 6, 8, 10]
    for n in N:
        loader.poblate(n, 20)
