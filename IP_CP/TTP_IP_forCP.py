from gurobipy import GRB, Model
from gurobipy import quicksum 
from test2_ortools.py import solve_game_schedule_with_ortools

n = 4
T = range(n)
S = range(2 * n - 2)

D = [
    [0, 1, 2, 3],
    [1, 0, 3, 4],
    [2, 3, 0, 5],
    [3, 4, 5, 0]
]
Left = 1
Right = 3
    

oponentes_en_s = dict()
away_en_s = dict()

maestro = Model()
maestro.Params.OutputFlag = 0


# Conjunto de todos los paths posibles 
P = []

# pi es una es una lista que tiene el costo del path i  
pi = []

# Diccionario de listas
# Dado un t te devuelve los indices de P tal que P es un single tournament de t
P_t = dict() 
for i in T:
    P_t[i] = []
    


# Variable binaria que indica si se toma el path i o no
x = []


while True:
    maestro.update()
    maestro.optimize()
    
    # home, nb_teams, nb_slots, distance, rc, ILB
    
    
    for i in T:
        pattern = solve_game_schedule_with_ortools(i, n, 2 * n - 2, D, [], )
        if pattern['estado'] != "infactible" and pattern['objetivo'] < 0:
            P.append(pattern['pattern'])
            P_t[i].append(pattern['pattern'])
            pi.append(pattern['objective'])
            x.append(maestro.addVar(vtype=GRB.BINARY, name=f'x_{i}'))
            for s in S:
                for t in T:
                    
            

m.addConstrs()    




# t is oponent in slot s
# t is away in slot s

