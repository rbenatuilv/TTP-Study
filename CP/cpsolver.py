from ortools.sat.python import cp_model
from inst_gen.generator import generate_distance_matrix


N = 4
S = 2 * N - 2
L = 1
U = 3
teams = range(N)
teams_duplicated = range(2 * N)
slots = range(1, 2 * N - 1)

distancia = generate_distance_matrix(N)

model = cp_model.CpModel()

opponent = {(t, s): model.NewIntVar(0, 2 * N - 1, f'opponent_{t}_{s}') 
            for t in teams for s in slots}

is_home = {(t, s): model.NewBoolVar(f'is_home_{t}_{s}') 
            for t in teams for s in slots}

auxiliar = {(t, j, s): model.NewBoolVar(f'auxiliar_{t}_{j}_{s}')
            for t in teams for j in teams_duplicated for s in slots}


# R1: Un equipo no juega contra sigo mismo
for t in teams:
    for s in slots:
        model.Add(opponent[t, s] != t)
        model.Add(opponent[t, s] != N + t)


# R2: Cada equipo juega contra diferente equipos en los slots
for t in teams:
    model.AddAllDifferent([opponent[t, s] for s in slots])


# Notacion: opponent[t, s] <= N - 1 <-> is_home[t, s] = 1
# R3: Relación entre variables para definir is_home
for t in teams:
    for s in slots:
        model.Add(opponent[t, s] <= N - 1).OnlyEnforceIf(is_home[t, s])
        model.Add(opponent[t, s] >= N).OnlyEnforceIf(is_home[t, s].Not())
        # model.Add(opponent[t, s] <= N - 1 + N * (1 - is_home[t, s]))
        # model.Add(N * (1 - is_home[t, s]) <= opponent[t, s])


# R4: Relación de variables entre auxiliar y opponent
for t in teams:
    for s in slots:
        for j in teams_duplicated:
            model.Add(opponent[t, s] == j).OnlyEnforceIf(auxiliar[t, j, s])
            model.Add(opponent[t, s] != j).OnlyEnforceIf(auxiliar[t, j, s].Not())

for t in teams:
    for s in slots:
        for j in teams_duplicated:
            # R5.1: Si el equipo t juega contra j como casa, entonces el equipo j juega como away contra t
            if j <= N - 1:
                model.Add(opponent[j, s] == N + t).OnlyEnforceIf(auxiliar[t, j, s])
                model.Add(auxiliar[j, t + N, s] == 1).OnlyEnforceIf(auxiliar[t, j, s])
            # R5.2: Si el equipo t juega contra j como away, entonces el equipo j juega como home contra t
            else:
                model.Add(opponent[j - N, s] == t).OnlyEnforceIf(auxiliar[t, j, s])
                model.Add(auxiliar[j - N, t, s] == 1).OnlyEnforceIf(auxiliar[t, j, s])

# R6: Restricción de partidos consecutivos
for t in teams:
    for s in range(1, 2 * N - 1 - U):
        model.Add(sum(is_home[t, s + j] for j in range(U + 1)) <= U)
        model.Add(sum(1 - is_home[t, s + j] for j in range(U + 1)) <= U)
        model.Add(sum(is_home[t, s + j] for j in range(U + 1)) >= L)
        model.Add(sum(1 - is_home[t, s + j] for j in range(U + 1)) >= L)


travel = {(t, s): model.NewIntVar(0, 13800, f'travel_{t}_{s}') for s in slots for t in teams}
init_travel = {t: model.NewIntVar(0, 13800, f'travel_{t}') for t in teams}
last_travel = {t: model.NewIntVar(0, 13800, f'travel_{t}') for t in teams}

for t in teams:
    for j1 in teams_duplicated:
        if j1 <= N - 1:
            model.Add(init_travel[t] == 0).OnlyEnforceIf(auxiliar[t, j1, slots[0]])
            model.Add(last_travel[t] == 0).OnlyEnforceIf(auxiliar[t, j1, slots[-1]])
            
        else:
            model.Add(init_travel[t] == distancia[t][j1 - N]).OnlyEnforceIf(
                    auxiliar[t, j1, slots[0]])
            model.Add(last_travel[t] == distancia[t][j1 - N]).OnlyEnforceIf(
                    auxiliar[t, j1, slots[-1]])
            
    for s in slots[:len(slots) - 1]:
        for j1 in teams_duplicated:
            for j2 in teams_duplicated:
                # juego como casa en ambos partidos
                if j1 <= N - 1 and j2 <= N - 1: 
                    model.Add(travel[t, s] == 0).OnlyEnforceIf(
                            auxiliar[t, j1, s]).OnlyEnforceIf(auxiliar[t, j2, s + 1])
                # Debo ir de casa hacia j2
                elif j1 <= N - 1 and j2 >= N:
                    model.Add(travel[t, s] == distancia[t][j2 - N]).OnlyEnforceIf(
                            auxiliar[t, j1, s]).OnlyEnforceIf(auxiliar[t, j2, s + 1])
                # Debo ir de j1 a casa
                elif j1 >= N and j2 <= N - 1:
                    model.Add(travel[t, s] == distancia[j1 - N][t]).OnlyEnforceIf(
                            auxiliar[t, j1, s]).OnlyEnforceIf(auxiliar[t, j2, s + 1])
                # Debo ir de j1 a j2
                elif j1 >= N and j2 >= N:
                    model.Add(travel[t, s] == distancia[j1 - N][j2 - N]).OnlyEnforceIf(
                            auxiliar[t, j1, s]).OnlyEnforceIf(auxiliar[t, j2, s + 1])

funcion_objetivo = model.NewIntVar(0, 13800 * N, name='objective')

model.Add(
    funcion_objetivo == 
        sum(travel[t, s] for t in teams for s in slots) 
        + sum(init_travel[t] + last_travel[t] for t in teams)
)
model.Minimize(funcion_objetivo)

solver = cp_model.CpSolver()

status = solver.Solve(model)

if status == cp_model.OPTIMAL:
    for t in teams:
        pattern = []
        for s in slots:
            if solver.Value(opponent[t, s]) <= N - 1:
                pattern.append(t)
            else:
                pattern.append(solver.Value(opponent[t, s]) - N)
            # print(f'{t}, {solver.Value(opponent[t, s])}, {solver.Value(opponent[solver.Value(opponent[t, s]) % N, s]) % N}')
        print(pattern)
    print(solver.Value(funcion_objetivo))
else:
    print('No solution found.')