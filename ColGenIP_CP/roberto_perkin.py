from gurobipy import GRB, Model, Column
from gurobipy import quicksum 
from cpgenerator_heuristic import CPPatternGeneratorH
from time import time
from threading import Thread
from ttpsolver_IPCP import TTPSolverIPCP
from inst_gen.generator import generate_distance_matrix

model = Model()

n = 4
dist = generate_distance_matrix(n)
relaxed_solver = TTPSolverIPCP(n, dist)

relaxed_solver.solve(600)
# for len(pattern)

