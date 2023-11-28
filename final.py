from inst_gen.instance_loader import TTPInstanceLoader
from ttp_master import TTPMaster
from ColGenIP_CP.cpgenerator import CPPatternGenerator
from ColGenIP_IP.MIP_col_gen import MIPPatternGenerator
from TTP_MILP import TTP
from cpsolver import CPSolver


TIMEOUT = 3600
POBLATE = False
N = [4, 6, 8, 10]
quant = 5

loader = TTPInstanceLoader()

if POBLATE:
    for n in N:
        loader.poblate(n, quant)
else:
    loader.load_all(N)


methods = {
    "MIP": TTP, 
    "CP": CPSolver, 
    "IP Gen Col IP": (TTPMaster, MIPPatternGenerator), 
    "IP Gen Col CP": (TTPMaster, CPPatternGenerator)
}

for n in N:
    for seed in loader.instances[n]:
        print(f'N = {n}, seed = {seed}'.center(80, '-'))
        distance_matrix = loader.instances[n][seed]['matrix']
        loader.matrix_print(distance_matrix)
        print()
        
        for method in methods:
            print(f'{method}...')
            if method in ["CP", "MIP"]:
                ans = methods[method](n, distance_matrix, 1, 3, timeout=TIMEOUT)
            else:
                solver = methods[method][0](n, distance_matrix, 1, 3, methods[method][1])
                ans = solver.solve(timeout=TIMEOUT)

            loader.save_info(n, seed, method, ans)
            print('Done!\n')
 
    for method in methods:
        loader.write_results(n, method)



