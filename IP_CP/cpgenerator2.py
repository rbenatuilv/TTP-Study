from ortools.sat.python import cp_model


class CPPatternGenerator:
    def __init__(self, n_teams: int, lower: int, upper: int):
        self.N = n_teams
        self.S = 2 * n_teams - 2
        self.teams = range(n_teams)
        self.teams_duplicated = range(2 * n_teams)
        self.slots = range(1, 2 * n_teams - 1)

        self.lower = lower
        self.upper = upper

        self.solver = cp_model.CpSolver()

    def set_vars(self, home, model):
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
        
    def set_constrs(self, home, model, distancia):
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
                model.Add(self.init_travel == distancia[home][j1 - self.N]).OnlyEnforceIf(
                        self.auxiliar[j1, self.slots[0]])
                model.Add(self.last_travel == distancia[home][j1 - self.N]).OnlyEnforceIf(
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
                            model.Add(self.travel[s] == distancia[home][j2 - self.N]).OnlyEnforceIf(
                                    self.auxiliar[j1, s]).OnlyEnforceIf(self.auxiliar[j2, s + 1])
                        # Debo ir de j1 a casa
                        elif j1 >= self.N and j2 <= self.N - 1:
                            model.Add(self.travel[s] == distancia[j1 - self.N][home]).OnlyEnforceIf(
                                    self.auxiliar[j1, s]).OnlyEnforceIf(self.auxiliar[j2, s + 1])
                        # Debo ir de j1 a j2
                        elif j1 >= self.N and j2 >= self.N:
                            model.Add(self.travel[s] == distancia[j1 - self.N][j2 - self.N]).OnlyEnforceIf(
                                    self.auxiliar[j1, s]).OnlyEnforceIf(self.auxiliar[j2, s + 1])
        self.funcion_objetivo = model.NewIntVar(0, 13800 * self.N, name='objective')

        model.Add(
            self.funcion_objetivo == 
                sum(self.travel[s] for s in self.slots) + self.init_travel + self.last_travel
        )
        model.Minimize(self.funcion_objetivo)

    
    def initialize_model(self, home, distancia):
        model = cp_model.CpModel()
        self.set_vars(home, model)
        self.set_constrs(home, model, distancia)
        return model
    
    def single_solve(self, home, distancia):
        model = self.initialize_model(home, distancia)
        status = self.solver.Solve(model)
        ans = dict()
        if status == cp_model.OPTIMAL:
            ans['status'] = 'Feasible'
            ans['pattern'] = tuple([self.solver.Value(self.opponent[s]) for s in self.slots])
        else:
            ans['status'] = 'Infeasible'
            print('No solution found.')

        return ans


if __name__ == '__main__':
    from inst_gen.generator import generate_distance_matrix
    from inst_gen.print_aux import matrix_print
    import time

    n = 6
    distances = generate_distance_matrix(n)
    ph = []

    generator = CPPatternGenerator(n, 1, 3)

    home = 4
    patts = []
    iters = 10

    start = time.time()
    for _ in range(iters):
        ans = generator.single_solve(home, distances)
        print(ans)
        print("yahoooo")

    end = time.time()
    
    matrix_print(patts)

    print(end - start)
