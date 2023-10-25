from ortools.sat.python import cp_model


class CPPatternGenerator:
    def __init__(self, n_teams: int, lower: int, upper: int, distances: list):
        self.N = n_teams
        self.S = 2 * n_teams - 2
        self.teams = range(n_teams)
        self.teams_duplicated = range(2 * n_teams)
        self.slots = range(1, 2 * n_teams - 1)

        self.lower = lower
        self.upper = upper
        self.distances = distances

        self.solver = cp_model.CpSolver()

    def set_vars(self, model):
        # Define the venue variables.
        self.opponent = {s: model.NewIntVar(0, 2 * self.N - 1, f'opponent_{s}') 
                    for s in self.slots}
        
        self.auxiliar = {(j, s): model.NewBoolVar(f'auxiliar_{j}_{s}')
                    for j in self.teams_duplicated for s in self.slots}
        
        
        # Define Booleans
        self.is_home = {s: model.NewBoolVar(f'is_home_venue_{s}') 
                      for s in self.slots}
        
        self.travel = {s: model.NewIntVar(0, 13800, f'travel_{s}') for s in self.slots }
        self.init_travel = model.NewIntVar(0, 13800, f'travel_inicial')
        self.last_travel = model.NewIntVar(0, 13800, f'travel_final')
        
    def set_constrs(self, home, model):
        # R1: Un equipo no juega contra sigo mismo
        for s in self.slots:
            model.Add(self.opponent[s] != home)
            model.Add(self.opponent[s] != self.N + home)
        
        # R2: Un equipo juega contra todos los equipos 2 veces
        model.AddAllDifferent([self.opponent[s] for s in self.slots])

        # R3: Un equipo juega como home (opponent[s] <= N - 1) <-> is_home
        for s in self.slots:
            model.Add(self.opponent[s] <= self.N - 1).OnlyEnforceIf(self.is_home[s])
            model.Add(self.opponent[s] >= self.N).OnlyEnforceIf(self.is_home[s].Not())

        # R4: Relacion entre aux y opponent
        for s in self.slots:
            for j in self.teams_duplicated:
                model.Add(self.opponent[s] == j).OnlyEnforceIf(self.auxiliar[j, s])
                model.Add(self.opponent[s] != j).OnlyEnforceIf(self.auxiliar[j, s].Not())

        # R5: Restricción de partidos consecutivos
        for s in range(1, 2 * self.N - 1 - self.upper):
            model.Add(sum(self.is_home[s + j] for j in range(self.upper + 1)) <= self.upper)
            model.Add(sum(1 - self.is_home[s + j] for j in range(self.upper + 1)) <= self.upper)
            model.Add(sum(self.is_home[s + j] for j in range(self.upper + 1)) >= self.lower)
            model.Add(sum(1 - self.is_home[s + j] for j in range(self.upper + 1)) >= self.lower)

        for j1 in self.teams_duplicated:
            if j1 <= self.N - 1:
                model.Add(self.init_travel == 0).OnlyEnforceIf(self.auxiliar[j1, self.slots[0]])
                model.Add(self.last_travel == 0).OnlyEnforceIf(self.auxiliar[j1, self.slots[-1]])
            
            else:
                model.Add(self.init_travel == self.distances[home][j1 - self.N]).OnlyEnforceIf(
                        self.auxiliar[j1, self.slots[0]])
                model.Add(self.last_travel == self.distances[home][j1 - self.N]).OnlyEnforceIf(
                    self.auxiliar[j1, self.slots[-1]])
            
            for s in self.slots[:len(self.slots) - 1]:
                for j1 in self.teams_duplicated:
                    for j2 in self.teams_duplicated:
                        # juego como casa en ambos partidos
                        if j1 <= self.N - 1 and j2 <= self.N - 1: 
                            model.Add(self.travel[s] == 0).OnlyEnforceIf(
                                    self.auxiliar[j1, s]).OnlyEnforceIf(self.auxiliar[j2, s + 1])
                        # Debo ir de casa hacia j2
                        elif j1 <= self.N - 1 and j2 >= self.N:
                            model.Add(self.travel[s] == self.distances[home][j2 - self.N]).OnlyEnforceIf(
                                    self.auxiliar[j1, s]).OnlyEnforceIf(self.auxiliar[j2, s + 1])
                        # Debo ir de j1 a casa
                        elif j1 >= self.N and j2 <= self.N - 1:
                            model.Add(self.travel[s] == self.distances[j1 - self.N][home]).OnlyEnforceIf(
                                    self.auxiliar[j1, s]).OnlyEnforceIf(self.auxiliar[j2, s + 1])
                        # Debo ir de j1 a j2
                        elif j1 >= self.N and j2 >= self.N:
                            model.Add(self.travel[s] == self.distances[j1 - self.N][j2 - self.N]).OnlyEnforceIf(
                                    self.auxiliar[j1, s]).OnlyEnforceIf(self.auxiliar[j2, s + 1])
                            

    def set_objective(self, home, model, pi):

        self.pi_auxiliar = {(t, s): model.NewIntVar(0, 1, f'pi_auxiliar_{t}_{s}') for s in self.slots for t in self.teams_duplicated}

        for s in self.slots:
            for t in self.teams_duplicated:
                model.Add(self.pi_auxiliar[t, s] == 1).OnlyEnforceIf(self.is_home[s].Not()).OnlyEnforceIf(self.auxiliar[t, s])
                model.Add(self.pi_auxiliar[t, s] == 0).OnlyEnforceIf(self.is_home[s])
                model.Add(self.pi_auxiliar[t, s] == 0).OnlyEnforceIf(self.auxiliar[t, s].Not())

        model.Minimize(sum(self.travel[s] for s in self.slots) 
                        + self.init_travel + self.last_travel - 
                        sum((pi[self.N + home * len(self.slots) + (s - 1)] + 
                            pi[self.N + (t - self.N) * len(self.slots) + (s - 1)]) * self.pi_auxiliar[t, s]
                            for s in self.slots for t in self.teams_duplicated) - pi[home])

    
    def initialize_model(self, home, pi):
        model = cp_model.CpModel()
        self.set_vars(model)
        self.set_constrs(home, model)
        self.set_objective(home, model, pi)
        return model
    
    def single_solve(self, home, pi):
        model = self.initialize_model(home, pi)
        status = self.solver.Solve(model)
        ans = dict()
        if status == cp_model.OPTIMAL:
            ans['status'] = 'Feasible'
            ans['pattern'] = tuple([self.solver.Value(self.opponent[s]) for s in self.slots])
            ans['obj_val'] = self.solver.ObjectiveValue()
        else:
            ans['status'] = 'Infeasible'
            print('No solution found.')

        return ans


if __name__ == '__main__':
    from inst_gen.generator import generate_distance_matrix
    from inst_gen.print_aux import matrix_print
    import time

    n = 4
    distances = generate_distance_matrix(n)

    generator = CPPatternGenerator(n, 1, 3, distances)

    pis = [0.0, 39.66666666666657, 0.0, 132.5, 
           0.0, 19.611111111110986, -55.22222222222217, 4.2777777777777715, -4.361111111111114, 0.47222222222221655, 130.63888888888889, 173.3055555555556, 9.305555555555543, -12.861111111111114, -109.66666666666661, 107.83333333333339, 42.666666666666714, 0.0, 70.66666666666671, 92.83333333333339, 63.41666666666663, 75.91666666666663, 108.41666666666663, 64.75000000000001, 124.41666666666663, -24.4166666666667, 38.333333333333314, -19.5]

    home = 2
    iters = 10

    start = time.time()
    for _ in range(iters):
        ans = generator.single_solve(home, pis)
        print(ans)
        print("yahoooo")

    end = time.time()

    print(end - start)
