import sys
import json


args = sys.argv

method = args[1]
n = int(args[2])
seed = int(args[3])
matrix = args[4]
timeout = int(args[5])

matrix = [[int(x) for x in line.split(',')] for line in matrix.split(';')]

if method == 'MIP':
    from TTP_MILP import TTP
    answer = TTP(n, matrix, 1, 3, timeout=timeout)

elif method == 'CP':
    from cpsolver import CPSolver
    answer = CPSolver(n, matrix, 1, 3, timeout=timeout)

elif method == 'IP Gen Col IP':
    from ttp_master import TTPMaster
    from ColGenIP_IP.MIP_col_gen import MIPPatternGenerator

    p_s = None
    if n > 4:
        from cpsolver import CPSolver
        p_s = CPSolver
    solver = TTPMaster(n, matrix, 1, 3, MIPPatternGenerator, pattern_setter=p_s)
    answer = solver.solve(timeout=timeout)

elif method == 'IP Gen Col CP':
    from ttp_master import TTPMaster
    from ColGenIP_CP.cpgenerator import CPPatternGenerator

    p_s = None
    if n > 4:
        from cpsolver import CPSolver
        p_s = CPSolver
    solver = TTPMaster(n, matrix, 1, 3, CPPatternGenerator, pattern_setter=p_s)
    answer = solver.solve(timeout=timeout)

print()
print(json.dumps(answer), end='')
