from inst_gen.instance_loader import TTPInstanceLoader
from ttp_master import TTPMaster
from ColGenIP_CP.cpgenerator import CPPatternGenerator
from ColGenIP_IP.MIP_col_gen import MIPPatternGenerator
from TTP_MILP import TTP
from CP.cpsolver import CPSolver


POBLATE = False
N = [4, 6, 8, 10]
quant = 5

loader = TTPInstanceLoader()

if POBLATE:
    for n in N:
        loader.poblate(n, quant)
else:
    loader.load_all(N)



