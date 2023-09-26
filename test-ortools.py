from ortools.sat.python import cp_model


def solve_game_schedule(n):
    # Create a CP model.
    model = cp_model.CpModel()

    # Define the ranges for teams and slots.
    teams = list(range(n))
    slots = list(range(1, n))

    # Define the opponent variable matrix.
    opponent = {}
    for i in teams:
        for t in slots:
            opponent[(i, t)] = model.NewIntVar(0, n - 1, f'opponent_{i}_{t}')

    # No team plays itself constraint.
    for i in teams:
        for t in slots:
            model.Add(opponent[(i, t)] != i)

    # Every team plays one game per slot constraint (one-factor constraint).
    for t in slots:
        model.AddAllDifferent([opponent[(i, t)] for i in teams])

    # Every team plays every other team constraint (all-different constraint).
    for i in teams:
        model.AddAllDifferent([opponent[(i, t)] for t in slots])

    # Create a solver.
    solver = cp_model.CpSolver()

    # Solve the model.
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL:
        print('Optimal solution found:')
        for i in teams:
            print(f'Team {i} plays against opponents:')
            for t in slots:
                opponent_id = solver.Value(opponent[(i, t)])
                print(f'  Slot {t}: Team {opponent_id}')
    else:
        print('The problem does not have an optimal solution.')


# Define the number of teams (n) here.
n = 6

# Solve the game scheduling problem for the given number of teams.
solve_game_schedule(n)