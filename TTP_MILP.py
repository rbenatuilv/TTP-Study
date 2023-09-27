from gurobipy import GRB, Model
from gurobipy import quicksum 

def TTP(n, D, L, U):
    T = range(n)
    S = range(2*n - 2)
    
    m = Model()
    
    x = m.addVars(T, T, S, vtype=GRB.BINARY, name='x')
    y = m.addVars(T, T, T, S, vtype=GRB.BINARY, name='y')
    z = m.addVars(T, T, S, vtype=GRB.BINARY, name='z')
    
    
    m.update()
    
    # R1 ningun equipo juega contrasigo mismo
    m.addConstrs(
        x[i, i, k] == 0 
        for i in T for k in S
    )
    
    # R2 Cada equipo juega un partido por slot
    m.addConstrs(
        quicksum(x[i, j, k] + x[j, i, k] for j in T) == 1
        for i in T for k in S
    )
    
    # R3 Cada equipo juega contra un equipo en casa y away
    m.addConstrs(
        quicksum(x[i, j, k] for k in S) == 1
        for i in T for j in T if i != j
    )
    
    # R4 Cada equipo juega a lo menos L partidos consecutivos y a lo más U partidos consecutivos
    m.addConstrs(
        quicksum(x[i, j, k + l] for l in range(U + 1) for j in T) <= U
        for i in T for k in range(2 * n - 2 - U)
    )
    
    # R4 Cada equipo juega a lo menos L partidos consecutivos y a lo más U partidos consecutivos
    m.addConstrs(
        quicksum(x[i, j, k + l] for l in range(U + 1) for j in T) >= L
        for i in T for k in range(2 * n - 2 - U)
    )
    
    # R5 No se pueden jugar dos equipos consecutivos
    m.addConstrs(
        (
            x[i, j, k] + x[j, i, k] + x[i, j, k + 1] + x[j, i, k + 1] <= 1
            for i in T for j in T for k in range(2 * n - 3)
        ),
        name="R5"
    )
    
    # R6 Variable auxiliar que indica si se juega en home
    m.addConstrs(
        z[i, i, k] == quicksum(x[j, i, k] for j in T) 
        for i in T for k in S
    )
    
    # R7 Auxiliar que indica si se juega como away
    m.addConstrs(
        z[i, j, k] == x[i, j, k] 
        for i in T for j in T for k in S if i != j
    )
    
    # R8 Definir si t debe ir a i
    m.addConstrs(
        y[t, i, j, k] >= z[t, i, k] + z[t, j, k + 1] - 1
        for t in T for i in T for j in T for k in range(2 * n - 3)
    )
    
    m.setObjective(
        quicksum(x[i, j, 1] * D[i][j] for i in T for j in T) 
        + quicksum(y[t, i, j, k] * D[i][j] for t in T for i in T for j in T for k in range(2 * n - 2))
        + quicksum(x[i, j, 2 * n - 3] * D[i][j] for i in T for j in T)        
        , GRB.MINIMIZE
    )
    
    m.optimize()
    # m.computeIIS()
    # m.write("model.ilp")

    print("Tiempo de ejecucion: ", m.Runtime)
    print("Valor objetivo: ", m.ObjVal)
    
    for i in T:
        lista = []
        for k in S:
            for j in T:
                if x[i, j, k].X != 0:
                    # lista.append(("away", j))
                    lista.append(j)
                if x[j, i, k].X != 0:
                    # lista.append(("home", j))
                    lista.append(i)
        print(lista)
    
    return 
    
    
if __name__ == "__main__":
    
    Distancia = [
        [0, 1, 2, 3],
        [1, 0, 3, 4],
        [2, 3, 0, 5],
        [3, 4, 5, 0]
    ]
    N = 4
    Left = 1
    Right = 3

    TTP(N,  Distancia, Left, Right)
    
    aux = [[0] * 4] * 3
    aux[1][1] = 1
    print(*aux, sep='\n')