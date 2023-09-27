from gurobipy import GRB, Model, Column
from gurobipy import quicksum 
from CPGen import solve_game_schedule_with_ortools

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
P = [
    [1, 0, 0, 0, 2, 3],
    [1, 1, 1, 0, 3, 2],
    [2, 1, 0, 3, 2, 2],
    [2, 0, 1, 3, 3, 3]
#     , [1, 0, 2, 0, 0, 3]
]


    

# Diccionario de listas
# Dado un t te devuelve los indices de P tal que P es un single tournament de t
P_t = dict() 
for t in T:
    P_t[t] = set()
    for p in range(len(P)):
        if sum(P[p][s] == t for s in S) == n - 1:
            P_t[t].add(p)
            
            
# P_i es una es una lista que tiene el costo del path i 
pi = dict()
for t in T:
    for p in P_t[t]:
        pattern = P[p]
        suma = D[t][pattern[0]]
        for s in S[:len(S) - 1]:
            suma += D[pattern[s]][pattern[s + 1]]
        suma += D[pattern[-1]][t]
        pi[p] = suma
        
# {patrones tales que t juega como home contra algun otro equipo j en el slot s}
home_t_s = dict()
for t in T:
    for s in S:
        home_t_s[t, s] = set()
        for j in T:
            if j != t:
                # t juega como home contra j en el slot s
                for p in P_t[j]:
                    if P[p][s] == t:
                        home_t_s[t, s].add(p)
        print(f"home_{t}_{s}", home_t_s[t, s])

# {patrones tales que t juega como away contra algun otro equipo j en el slot s}
away_t_s = dict()
for t in T:
    for s in S:
        away_t_s[t, s] = set()
        for p in P_t[t]:
            if P[p][s] != t:
                away_t_s[t, s].add(p)
        print(f"away_{t}_{s}", away_t_s[t, s])

# Variable binaria que indica si se toma el path i o no
x = [maestro.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=1, name=f'x_{i}') for i in range(len(P))]


constraints = dict()

for t in T: 
    for s in S:
        constraints[t, s] = maestro.addConstr(
            (quicksum(x[i] for i in home_t_s[t, s]) + quicksum(x[i] for i in away_t_s[t, s]) == 1),
            name=f"R_{t}_{s}"
        )
        
limit_iteraciones = 5
for iteracion in range(limit_iteraciones):
    maestro.update()
    maestro.optimize()

    # dual_vars = maestro.getAttr('Pi', maestro.getConstrs())
    dual_vars = []
    for t in T:
        lista_t = []
        for s in S:
            lista_t.append(maestro.getConstrByName(constraints[t, s].getAttr('ConstrName')).Pi)
        dual_vars.append(lista_t)
    print(dual_vars)
    
    for i in T:
        # home, nb_teams, nb_slots, distance, rc, ILB
        pattern = solve_game_schedule_with_ortools(i, n, 2 * n - 2, D, dual_vars)
        print(pattern)
        if pattern['estado'] != "Infactible" and pattern['objective'] < 0:
            print(pattern['pattern'])
            patron = pattern['pattern']
            columna = [0 for s in S for t in T]
            for s, t in enumerate(patron):
                if t - 1 != i:
                    # Lo anado en la restriccion t,s
                    columna[(t - 1) * len(S) + s] = 1
                    
                    # Lo anado en la restriccion i,s
                    columna[i * len(S) + s] = 1
            Column(columna, maestro.getConstrs())
            x.append(maestro.addVar(vtype=GRB.CONTINUOUS, name=f'x_{i}_{len(P)}'))
            P_t[i].add(len(P))
            pi[len(P)] = pattern['objective']
            P.append(pattern['pattern'])
            

# t is oponent in slot s
# t is away in slot s

