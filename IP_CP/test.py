import gurobipy as gp
from gurobipy import GRB, Model, Column


model = Model()

aux_sets = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

x = [model.addVar(vtype=GRB.BINARY, name=f"x_{i}") for i in aux_sets]

model.addConstr(sum(x[i] for i in aux_sets) == 1, name="R_1")
model.setObjective(sum(x[i] * i for i in aux_sets), GRB.MINIMIZE)

model.update()

model.write("test1.lp")

x.append(model.addVar(obj=11, vtype=GRB.BINARY, name="x_11", column=Column([1], model.getConstrs())))

model.update()

model.write("test2.lp")