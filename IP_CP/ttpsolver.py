from gurobipy import GRB, Model, Column
from gurobipy import quicksum 
from cpgenerator import CPPatternGenerator


class TTPSolverIPCP:
    def __init__(self, n_teams: int, distances: list, lower: int, upper: int, patterns=[]):
        self.N = n_teams
        self.teams = range(n_teams)
        self.slots = range(2 * n_teams - 2)

        self.distances = distances
        self._patterns = patterns

        self.lower = lower
        self.upper = upper

        self.master = Model()
        self.master.Params.OutputFlag = 0
        self.sattelite = CPPatternGenerator(n_teams, lower, upper)

        self.best_sol = {'objective': float('inf'), 'patterns': []}

        if not self._patterns:
            self.set_initial_patterns()

        self.initialize()

    @property
    def patterns(self):
        return self._patterns
    
    @patterns.setter
    def patterns(self, value):
        self._patterns = value
        self.create_aux_sets()

    def initialize(self):
        self.create_aux_sets()
        self.set_vars()
        self.set_constrs()
        self.set_costs()
        self.set_objective()

    def create_aux_sets(self):
        self.set_team_patterns()
        self.set_home_patterns()
        self.set_away_patterns()

    def set_initial_patterns(self):
        self.patterns = []
        for i in self.teams:
            ans = self.sattelite.single_solve(i, [])
            if ans['status'] == 'Feasible':
                self.patterns.append(ans['pattern'])

    def set_team_patterns(self):
        p_t = dict() 
        for t in self.teams:
            p_t[t] = set()
            for p in range(len(self.patterns)):
                home_counts = sum(self.patterns[p][s] == t for s in self.slots)
                if  home_counts == self.N - 1:
                    p_t[t].add(p)

        self.team_patterns = p_t

    def set_home_patterns(self):
        home_t_s = dict()
        for t in self.teams:
            for s in self.slots:
                home_t_s[t, s] = set()
                for j in self.teams:
                    if j != t:
                        for p in self.team_patterns[j]:
                            if self.patterns[p][s] == t:
                                home_t_s[t, s].add(p)

        self.home_t_s = home_t_s

    def set_away_patterns(self):
        away_t_s = dict()
        for t in self.teams:
            for s in self.slots:
                away_t_s[t, s] = set()
                for p in self.team_patterns[t]:
                    if self.patterns[p][s] != t:
                        away_t_s[t, s].add(p)

        self.away_t_s = away_t_s

    def get_pattern_cost(self, team, pattern):
        cost = self.distances[team][pattern[0]]

        for s in self.slots[:len(self.slots) - 1]:
            cost += self.distances[pattern[s]][pattern[s + 1]]

        cost += self.distances[pattern[-1]][team]
        return cost

    def set_costs(self):
        self.costs = dict()
        for t in self.teams:
            for p in self.team_patterns[t]:
                self.costs[p] = self.get_pattern_cost(t, self.patterns[p])

    def set_vars(self):
        self.x = [self.master.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=1, name=f'x_{i}') 
                  for i in range(len(self.patterns))]

    def set_constrs(self):
        for t in self.teams: 
            for s in self.slots:
                self.master.addConstr(
                    (quicksum(self.x[i] for i in self.home_t_s[t, s]) 
                     + quicksum(self.x[i] for i in self.away_t_s[t, s]) == 1),
                    name=f"R_{t}_{s}"
                )

        for t in self.teams:
            self.master.addConstr(quicksum(self.x[i] 
                                           for i in self.team_patterns[t]) == 1,
                                           f"Asignacion_{t}")
    
    def set_objective(self):
        self.master.setObjective(quicksum(self.x[i] * self.costs[i] 
                                          for i in range(len(self.patterns))), 
                                          GRB.MINIMIZE)

    def pattern_hash(self, pattern):
        return sum(pattern[s] * 2 ** s for s in self.slots)

    def master_solve(self):
        self.master.update()
        self.master.optimize()

    def sattelite_solve(self, home, pool_size=10):
        patt_hashes = [self.pattern_hash(self.patterns[p]) for p in self.team_patterns[home]]
        gen_patts = []
        for _ in range(pool_size):
            ans = self.sattelite.single_solve(home, patt_hashes)
            if ans['status'] == 'Feasible':
                gen_patts.append(ans['pattern'])
                patt_hashes.append(ans['hash'])
        
        return gen_patts
    
    def get_master_duals(self):
        dual_vars = dict()
        dual_vars['Asignacion'] = [self.master.getConstrByName(f"Asignacion_{t}").Pi
                                   for t in self.teams]
        
        dual_vars['R'] = []

        for t in self.teams:
            for s in self.slots:
                dual_vars['R'].append(self.master.getConstrByName(f"R_{t}_{s}").Pi)
        return dual_vars
    
    def pattern_to_column(self, pattern, team):
        constrs1 = [0 for _ in self.teams]
        constrs1[team] = 1

        constrs2 = [0 for _ in self.slots for _ in self.teams]
        for s, t in enumerate(pattern):
            if t != team:
                constrs2[t * len(self.slots) + s] = 1
                constrs2[team * len(self.slots) + s] = 1

        return constrs1 + constrs2
    
    def add_column(self, pattern, team):
        column = self.pattern_to_column(pattern, team)
        
        self.x.append(self.master.addVar(obj=self.get_pattern_cost(team, pattern), 
                           column=Column(column, self.master.getConstrs()),
                           name=f'x_{len(self.x)}',
                           vtype=GRB.CONTINUOUS,
                           lb=0, ub=1)
                        )
        
        self.master.update()

    def get_reduced_cost(self, pattern, team, dual_vars):
        cost = self.get_pattern_cost(team, pattern)
        column = self.pattern_to_column(pattern, team)
        sum_duals = dual_vars['Asignacion'] + dual_vars['R']
        constrs = sum(column[i] * sum_duals[i] for i in range(len(column)))

        return cost - constrs

    def solve(self, iters=30):
        cont = 0
        while cont < iters or not self.best_sol['patterns']:
            self.master_solve()

            if self.master.status == GRB.OPTIMAL:
                print('Optimal solution found')

                # Check if the non-zero variables are all equal to one, and save the solution
                non_zero_vars = {var.VarName: var.X 
                                 for var in self.master.getVars() if var.X != 0}

                if all(var == 1.0 for var in non_zero_vars.values()) and self.master.objVal < self.best_sol['objective']:
                    self.best_sol['objective'] = self.master.objVal
                    self.best_sol['patterns'] = [self.patterns[int(var[2:])] for var in non_zero_vars.keys()]
                    print('\nINTEGER SOLUTION!\n')

                print('Checking for new patterns...')

                duals = self.get_master_duals()

                for t in self.teams:
                    gen_patts = self.sattelite_solve(t)
                    for p in gen_patts:
                        if self.get_reduced_cost(p, t, duals) < 0:
                            self.patterns.append(p)
                            self.add_column(p, t)

            if self.master.status == GRB.INFEASIBLE:
                print("Infeasible master problem")
                for t in self.teams:
                    gen_patts = self.sattelite_solve(t)
                    for p in gen_patts:
                        self.patterns.append(p)
                        self.add_column(p, t)
            cont += 1


if __name__ == '__main__':
    from inst_gen.generator import generate_distance_matrix

    n = 4
    dist = generate_distance_matrix(n)

    feas = [[3, 0, 0, 0, 1, 2],
            [1, 3, 0, 2, 1, 1],
            [1, 0, 3, 2, 2, 2],
            [3, 3, 3, 0, 2, 1]]

    ttp_solver = TTPSolverIPCP(n, dist, 1, 3)

    ttp_solver.solve()

    print(f"\nObjVal: {ttp_solver.best_sol['objective']}")
    print('Patterns:')
    for pat in ttp_solver.best_sol['patterns']:
        print(pat)

