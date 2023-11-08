from gurobipy import GRB, Model, Column
from gurobipy import quicksum 
from cpgenerator_heuristic import CPPatternGeneratorH
from MIP_col_gen import MIPPatternGenerator
from time import time
from threading import Thread


class TTPSolverIPIP:
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

        self.sattelite = MIPPatternGenerator(n_teams, lower, upper, distances)

        self.best_sol = {'objective': float('inf'), 'patterns': []}
        self.partial_sol = {'objective': float('inf'), 'patterns': [], 'vars': []}

        self.start_time = None
        self.elapsed_time = None

        self.optimal = False
        self.solved = False
        self.timeout = False
        self.iterations = 0

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
            ans = self.sattelite.single_heur_solve(i)
            if ans['status'] == 'Feasible':
                self.patterns.append(ans['pattern'])

    def set_team_patterns(self):
        p_t = dict() 
        for t in self.teams:
            p_t[t] = []
            for p in range(len(self.patterns)):
                home_counts = sum(self.patterns[p][s] == t 
                                  for s in self.slots)
                if  home_counts == self.N - 1:
                    p_t[t].append(p)

        self.team_patterns = p_t

    def set_home_patterns(self):
        home_t_s = dict()
        for t in self.teams:
            for s in self.slots:
                home_t_s[t, s] = []
                for j in self.teams:
                    if j != t:
                        for p in self.team_patterns[j]:
                            if self.patterns[p][s] == t:
                                home_t_s[t, s].append(p)

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
    def master_solve(self):
        self.master.update()
        self.master.optimize()

    def heur_sattelite_solve(self, home, pool_size=10):
        gen_patts = []
        for _ in range(pool_size):
            ans = self.sattelite.single_heur_solve(home)
            if ans['status'] == 'Feasible':
                gen_patts.append(ans['pattern'])
        
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
        
        self.x.append(self.master.addVar(
                           obj=self.get_pattern_cost(team, pattern), 
                           column=Column(column, self.master.getConstrs()),
                           name=f'x_{len(self.x)}',
                           vtype=GRB.CONTINUOUS,
                           lb=0, ub=1
                           )
                        )

        self.master.update()

    def get_reduced_cost(self, pattern, team, dual_vars):
        cost = self.get_pattern_cost(team, pattern)
        column = self.pattern_to_column(pattern, team)
        sum_duals = dual_vars['Asignacion'] + dual_vars['R']
        constrs = sum(column[i] * sum_duals[i] for i in range(len(column)))

        return cost - constrs

    def solve_alg(self):
        self.optimal = False
        self.iterations = 0
        self.start_time = time()

        while not self.optimal:
            self.master_solve()

            if self.master.status == GRB.OPTIMAL:
                self.solved = True
                print(f'Optimal solution found: ObjVal: {self.master.objVal}')
                non_zero_vars = {var.VarName: var.X 
                                 for var in self.master.getVars() if var.X != 0}

                if all(var == 1.0 for var in non_zero_vars.values()) and self.master.objVal < self.best_sol['objective']:
                    self.best_sol['objective'] = self.master.objVal
                    self.best_sol['patterns'] = [self.patterns[int(var[2:])] 
                                                 for var in non_zero_vars.keys()]
                    print('\nINTEGER SOLUTION!\n')

                else:
                    self.partial_sol['objective'] = self.master.objVal
                    self.partial_sol['patterns'] = {(var, val): self.patterns[int(var[2:])] 
                                                    for var, val in non_zero_vars.items()}

                duals = self.get_master_duals()                   
                
                optimal = True
                for t in self.teams:
                    dictionary = self.sattelite.single_solve(t, duals['Asignacion'] + duals['R'])
                    if dictionary['status'] == "Feasible" and dictionary['obj_val'] < 0:
                        optimal = False
                        self.patterns.append(dictionary['pattern'])
                        self.add_column(dictionary['pattern'], t)
                    
                    elif dictionary['status'] == "Feasible":
                        if dictionary['obj_val'] < 1:
                            print("casi negativo", dictionary['obj_val'])    

                    elif dictionary['status'] == "Infeasible":
                        optimal = False

                self.optimal = optimal

            if self.master.status == GRB.INFEASIBLE:
                print("Infeasible master problem")
                for t in self.teams:
                    gen_patts = self.heur_sattelite_solve(t)
                    for p in gen_patts:
                        self.patterns.append(p)
                        self.add_column(p, t)

            self.iterations += 1

    def solve(self, timeout=3600):

        solve_thread = Thread(target=self.solve_alg, daemon=True)
        solve_thread.start()

        solve_thread.join(timeout=timeout)
        if solve_thread.is_alive():
            print('\nTIMEOUT')
            self.master.terminate()

        stop = time()
        self.elapsed_time = stop - self.start_time

        self.print_results()

        print(f'\nElapsed time: {self.elapsed_time}')
            
    def print_results(self):
        if not self.solved:
            print('No solution found')
            return
        
        if self.optimal:
                print('\nOPTIMAL SOL!')
        else:
            print('\nSUB OPTIMAL SOL!')

        if self.best_sol['patterns']:
            print('\nInteger solution found:')
            print(f"\nObjVal: {self.best_sol['objective']}")
            print('Patterns:')
            for pat in self.best_sol['patterns']:
                print(pat)
        else:
            print('\nNo integer solution found.')

        if self.partial_sol['patterns']:
            print('\nPartial solution found:')
            print(f"\nObjVal: {self.partial_sol['objective']}")
            print('Patterns:')
            for key, pat in self.partial_sol['patterns'].items():
                print(key, pat)


if __name__ == '__main__':
    from inst_gen.generator import generate_distance_matrix

    n = 6
    dist = generate_distance_matrix(n)

    feas = [
        [3, 0, 0, 0, 1, 2],
        [1, 3, 0, 2, 1, 1],
        [1, 0, 3, 2, 2, 2],
        [3, 3, 3, 0, 2, 1],
        [3, 3, 3, 0, 2, 1],
        [3, 3, 3, 0, 2, 1]
    ]

    ttp_solver = TTPSolverIPIP(n, dist, 1, 3)

    ttp_solver.solve(timeout=120)
