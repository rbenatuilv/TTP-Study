from ortools.sat.python import cp_model
import time


def solve_game_schedule_with_ortools(home, nb_teams, nb_slots, distance, rc, ILB):
    # Create a CP model.
    model = cp_model.CpModel()

    # Define the range for Teams and Slots.
    Teams = range(1, nb_teams + 1)
    Slots = range(1, nb_slots + 1)

    # Define the venue variables.
    venue = [model.NewIntVar(1, nb_teams, f'venue_{s}') for s in range(nb_slots + 2)]

    # Define the travel variables.
    travel = [model.NewIntVar(0, 1380, f'travel_{s}') for s in range(nb_slots + 1)]

    # Define Booleans
    home_venue = {s: model.NewBoolVar(f'is_home_venue_{s}') for s in Slots}
    for s in Slots:
        model.Add(venue[s] == home).OnlyEnforceIf(home_venue[s])
        model.Add(venue[s] != home).OnlyEnforceIf(home_venue[s].Not())

    bool_venues = {(i, s): model.NewBoolVar(f'bool_venues_{i}{s}') for i in Teams for s in range(nb_slots + 2)}
    for i in Teams:
        for s in range(nb_slots + 1):
            model.Add(venue[s] == i).OnlyEnforceIf(bool_venues[(i, s)])
            model.Add(venue[s] != i).OnlyEnforceIf(bool_venues[(i, s)].Not())

    bool_travel = {(i, j, s): model.NewBoolVar(f'bool_travel_{i}{j}{s}') for i in Teams for j in Teams for s in range(nb_slots + 1)}

    # Venue constraints
    model.Add(venue[0] == home)
    model.Add(venue[nb_slots + 1] == home)

    model.Add(2 * sum(home_venue[s] for s in Slots) == nb_slots)

    for s in range(1, nb_slots - 3):
        model.Add(sum(home_venue[s + j] for j in range(4)) <= 3)
        model.Add(sum(1 - home_venue[s + j] for j in range(4)) <= 3)

    for i in Teams:
        if i != home:
            model.Add(sum(bool_venues[(i, s)] for s in Slots) == 1)

    # Distance calculations
    for s in range(nb_slots + 1):
        for i in Teams:
            for j in Teams:
                model.Add(bool_venues[(i, s)] + bool_venues[(j, s + 1)] == 2).OnlyEnforceIf(bool_travel[(i, j, s)])
                model.Add(bool_venues[(i, s)] + bool_venues[(j, s + 1)] != 2).OnlyEnforceIf(bool_travel[(i, j, s)].Not())

                model.Add(travel[s] == distance[i - 1][j - 1]).OnlyEnforceIf(bool_travel[(i, j, s)])

    # Objective function
    model.Add(sum(travel[s] for s in range(nb_slots + 1)) <= ILB + 30)
    # model.Minimize(sum(travel[s] - bool_venues[(i, s)] * rc[i - 1][s - 1] for s in range(nb_slots + 1) for i in Teams))
    

    # Create a solver and solve the model.
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # Print the solution.
    if status == cp_model.OPTIMAL:
        print('Optimal solution found:')
        for s in Slots:
            print(f'Slot {s}: Team {solver.Value(venue[s])}')

    elif status == cp_model.INFEASIBLE:
        print('AAAAAAAAAAAAA')


home = 4
nb_teams = 6
nb_slots = 10
distance = [[0, 10, 20, 30, 30, 13], 
            [10, 0, 15, 25, 30, 15], 
            [20, 15, 0, 4, 12, 21], 
            [30, 25, 4, 0, 35, 10], 
            [30, 30, 12, 35, 0, 40],
            [13, 15, 21, 10, 40, 0]]  

rc = [[0.5, 0.8, 0.3, 0.1, 0.3, 0.2],
      [0.7, 0.4, 0.6, 0.8, 0.2, 0.1], 
      [0.2, 0.9, 0.1, 0.2, 0.4, 0.3], 
      [0.2, 0.9, 0.1, 0.2, 0.1, 0.5]] 

ILB = 90

ti = time.time()
solve_game_schedule_with_ortools(home, nb_teams, nb_slots, distance, rc, ILB)
print(time.time() - ti)
