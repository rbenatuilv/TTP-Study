import subprocess
import os


def run_solver(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    return command, stdout, stderr, process.returncode


def create_file(n, tester, directory):
    path = os.path.join(directory, f'results_{tester}', f'results_N_{n}.csv')
    with open(path, 'w') as file:
        file.write('seed;pattern;best fractionary solution;best integer solution;status;time\n')


def write_sol(n, seed, tester, info, loader):
    loader.save_info(n, seed, tester, info, to_csv=True)


def create_error_file():
    with open('errors_log.txt', 'w') as file:
        file.write('')


def write_error(n, seed, tester, error):
    with open('errors_log.txt', 'a') as file:
        file.write(f'N = {n}, seed = {seed}, tester = {tester}\n')
        file.write(f'{error}\n\n')


if __name__ == '__main__':
    import concurrent.futures
    from inst_gen.instance_loader import TTPInstanceLoader
    import json

    loader = TTPInstanceLoader()

    N = [4, 6, 8, 10]
    methods = ['MIP', 'CP', 'IP Gen Col IP', 'IP Gen Col CP']
    TIMEOUT = 7200

    POBLATE = False
    quant = 5
    
    if POBLATE:
        for n in N:
            loader.poblate(n, quant)
    else:
        loader.load_all(N)

    seeds = {n: [seed for seed in loader.instances[n]] for n in N}
    matrices = {n: {seed: loader.text_matrix(n, seed) for seed in seeds[n]} for n in N}

    for n in N:
        for method in methods:
            create_file(n, method, loader.directory)

    create_error_file()

    commands = [
        ['python', 'parallel_solve.py', method, str(n), str(seed), str(matrices[n][seed]), str(TIMEOUT)] 
        for n in N for seed in seeds[n] for method in methods
    ]

    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Submitting tasks to the executor
        futures = [executor.submit(run_solver, cmd) for cmd in commands]

        # Gathering results as they become available
        for future in concurrent.futures.as_completed(futures):
            command, stdout, stderr, returncode = future.result()
            print(f'N = {command[3]}, seed = {command[4]}, tester = {command[2]}')
            print('Return code:', returncode, '\n')

            if returncode != 0:
                write_error(int(command[3]), int(command[4]), command[2], stderr)

            else:
                out = json.loads(stdout.split('\n')[-1])
                write_sol(int(command[3]), int(command[4]), command[2], out, loader)
