from ortools.sat.python import cp_model


class CPPatternGenerator:
    def __init__(self, n_teams: int, lower: int, upper: int):
        self.N = n_teams
        self.S = 2 * n_teams - 2
        self.teams = range(n_teams)
        self.slots = range(1, 2 * n_teams - 1)

        self.lower = lower
        self.upper = upper

        self.solver = cp_model.CpSolver()

    def set_vars(self, home, model):
        # Define the venue variables.
        venue = [model.NewIntVar(0, self.N - 1, f'venue_{s}') 
                 for s in range(self.S + 2)]
        
        pat_hash = model.NewIntVar(0, 3 ** self.S, 'pat_hash')

        # Define Booleans
        home_venue = {s: model.NewBoolVar(f'is_home_venue_{s}') 
                      for s in self.slots}
        for s in self.slots:
            model.Add(venue[s] == home).OnlyEnforceIf(home_venue[s])
            model.Add(venue[s] != home).OnlyEnforceIf(home_venue[s].Not())

        bool_venues = {(i, s): model.NewBoolVar(f'bool_venues_{i}{s}') 
                       for i in self.teams for s in range(self.S + 2)}
        for i in self.teams:
            for s in range(self.S + 1):
                model.Add(venue[s] == i).OnlyEnforceIf(bool_venues[(i, s)])
                model.Add(venue[s] != i).OnlyEnforceIf(bool_venues[(i, s)].Not())
        
        self.venue = venue
        self.pat_hash = pat_hash
        self.home_venue = home_venue
        self.bool_venues = bool_venues

    def set_constrs(self, home, model, patt_hashes):
        # Hash constraints
        model.Add(self.pat_hash == sum(self.venue[s] * 2 ** (s - 1) for s in self.slots))
        for ph in patt_hashes:
            model.Add(self.pat_hash != ph)

        # Venue constraints
        model.Add(self.venue[0] == home)
        model.Add(self.venue[self.S + 1] == home)

        model.Add(2 * sum(self.home_venue[s] for s in self.slots) == self.S)

        for s in range(1, self.S - 3):
            model.Add(sum(self.home_venue[s + j] for j in range(4)) <= self.upper)
            model.Add(sum(1 - self.home_venue[s + j] for j in range(4)) <= self.upper)

            model.Add(sum(self.home_venue[s + j] for j in range(4)) >= self.lower)
            model.Add(sum(1 - self.home_venue[s + j] for j in range(4)) >= self.lower)

        for i in self.teams:
            if i != home:
                model.Add(sum(self.bool_venues[(i, s)] for s in self.slots) == 1)
    
    def initialize_model(self, home, patt_hashes):
        model = cp_model.CpModel()
        self.set_vars(home, model)
        self.set_constrs(home, model, patt_hashes)
        return model
    
    def single_solve(self, home, patt_hashes):
        model = self.initialize_model(home, patt_hashes)
        status = self.solver.Solve(model)
        ans = dict()
        if status == cp_model.OPTIMAL:
            ans['status'] = 'Feasible'
            ans['pattern'] = tuple([self.solver.Value(self.venue[s]) for s in self.slots])
            ans['hash'] = self.solver.Value(self.pat_hash)
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

    home = 2
    patts = []
    iters = 10

    start = time.time()
    for _ in range(iters):
        ans = generator.single_solve(home, ph)
        patts.append(ans['pattern'])
        ph.append(ans['hash'])

    end = time.time()
    
    matrix_print(patts)

    print(end - start)
