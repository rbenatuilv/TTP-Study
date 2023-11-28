from gurobipy import GRB, Model, Column
from gurobipy import quicksum 
from time import time
from threading import Thread


class TTPMaster:
    def __init__(self, n_teams: int, distances: list, lower: int, upper: int, satt1=None, satt2=None, patterns=[]):
        self.N = n_teams
        self.teams = range(n_teams)
        self.slots = range(2 * n_teams - 2)

        self.distances = distances
        self.patterns = patterns
        self.VERBOSE = False

        self.lower = lower
        self.upper = upper

        self.master = Model()
        self.master.Params.OutputFlag = 0
        
        if satt1 and satt2:
            self.sattelite1 = satt1(n_teams, lower, upper, distances)
            self.sattelite2 = satt2(n_teams, lower, upper, distances)

        elif satt1:
            self.sattelite1 = satt1(n_teams, lower, upper, distances)
            self.sattelite2 = None
        
        elif satt2:
            self.sattelite1 = satt2(n_teams, lower, upper, distances)
            self.sattelite2 = None

        else:
            print("No elegiste ningun problema satelite por lo que no se puede resolver")
            
        self.best_sol = {'objective': float('inf'), 'patterns': []}
        self.partial_sol = {'objective': float('inf'), 'patterns': [], 'vars': []}

        self.start_time = None
        self.elapsed_time = None

        self.optimal = False
        self.solved = False
        self.timeout = False
        self.iterations = 0

        if not self.patterns:
            self.set_initial_patterns()

        self.initialize()

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
            ans = self.sattelite1.single_gen_solve(i)
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
            ans = self.sattelite1.single_gen_solve(home)
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
        
        self.x.append(
            self.master.addVar(
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
                    # Comparing when having two sattelites
                    if self.sattelite1 and self.sattelite2:
                        dictionary1 = self.sattelite1.single_solve(t, duals['Asignacion'] + duals['R'])
                        dictionary2 = self.sattelite2.single_solve(t, duals['Asignacion'] + duals['R'])
                        if self.VERBOSE:
                            if dictionary1['status'] != dictionary2['status']:
                                print("\n-----------------------------------------------\n")
                                print("No coinciden los status de los modelos")
                                print(f"Estado satt1: {dictionary1['status']}")
                                print(f"Estado satt2: {dictionary2['status']}")
                                print("\n-----------------------------------------------\n")
                                
                            
                            elif dictionary1['status'] == "Feasible" and dictionary1['obj_val'] * dictionary2['obj_val'] < 0:
                                print("\n-----------------------------------------------")
                                print("No coinciden los signos de los satelites")
                                print(f"Obj_val satt1: {dictionary1['obj_val']}")
                                print(f"Costo reducido satt1: {self.get_reduced_cost(dictionary1['pattern'], t, duals)}")
                                print(f"Obj_val satt2: {dictionary2['obj_val']}")
                                print(f"Costo reducido satt2: {self.get_reduced_cost(dictionary2['pattern'], t, duals)}")
                                print(F"Patron satt1: {dictionary1['pattern']}")
                                print(f"Patron satt2: {dictionary2['pattern']}")
                                print("-----------------------------------------------\n")
                            
                            elif dictionary1['status'] == "Feasible" and abs(dictionary1['obj_val'] - dictionary2['obj_val']) < 1e-4:
                                print("\n-----------------------------------------------")
                                print("Las respuestas si coinciden")
                                print(f"Obj_val satt1: {dictionary1['obj_val']}")
                                print(f"Obj_val satt2: {dictionary2['obj_val']}")
                                print(F"Patron satt1: {dictionary1['pattern']}")
                                print(f"Patron satt2: {dictionary2['pattern']}")
                                print("-----------------------------------------------\n")
                        
                        if dictionary2['status'] == "Feasible" and dictionary2['obj_val'] < 0:
                            optimal = False
                            self.patterns.append(dictionary2['pattern'])
                            self.add_column(dictionary2['pattern'], t)
                        elif dictionary2['status'] == "Infeasible":
                            optimal = False
                            
                    # Having only one sattelite
                    elif self.sattelite1:
                        dictionary = self.sattelite1.single_solve(t, duals['Asignacion'] + duals['R'])

                        if dictionary['status'] == "Feasible" and dictionary['obj_val'] < 0:
                            optimal = False
                            self.patterns.append(dictionary['pattern'])
                            self.add_column(dictionary['pattern'], t)
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
        tiempo_terminado = False
        if solve_thread.is_alive():
            print('\nTIMEOUT')
            tiempo_terminado = True
            self.master.terminate()

        integer_patterns, integer_solution = self.integer_solver(timeout=timeout)
        
        stop = time()
        self.elapsed_time = stop - self.start_time

        self.print_results()

        print(f'\nElapsed time: {self.elapsed_time}')
        
        
        ans = dict()
        ans['pattern'] = integer_patterns
        ans['best fractionary solution'] = self.partial_sol['objective']
        ans['best integer solution'] = integer_solution
        if tiempo_terminado:
            ans['status'] = 'Time Limit'
        else:
            ans['status'] = 'Optimal'
        ans['time'] = self.elapsed_time
        
        return ans
        
    def integer_solver(self, timeout=3600):
        model = Model()
        model.setParam('TimeLimit', timeout)
        model.Params.OutputFlag = 0
        
        x = [model.addVar(vtype=GRB.BINARY, name=f'x_{i}') 
                  for i in range(len(self.patterns))]
        
        self.create_aux_sets()
        self.set_costs()
        
        for t in self.teams: 
            for s in self.slots:
                model.addConstr(
                    (quicksum(x[i] for i in self.home_t_s[t, s]) 
                     + quicksum(x[i] for i in self.away_t_s[t, s]) == 1),
                    name=f"R_{t}_{s}"
                )

        for t in self.teams:
            model.addConstr(
                quicksum(x[i] for i in self.team_patterns[t]) == 1,
                f"Asignacion_{t}"
            )
        
        model.update()
        
        model.setObjective(
            quicksum(x[i] * self.costs[i] for i in range(len(self.patterns)))
            , GRB.MINIMIZE
        )
        
        model.update()
        model.optimize()
        
        if model.status == GRB.OPTIMAL or model.status == GRB.TIME_LIMTI:
            print("SOLUCION ENTERA CON LAS COLUMNAS GENERADAS")
            print(model.ObjVal)
            patrones = []
            for i in range(len(self.patterns)):
                if x[i].X >= 0.5:
                    print(self.patterns[i])
                    patrones.append(self.patterns[i])
            return patrones, model.ObjVal
        return None, None
            
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
    from ColGenIP_CP.inst_gen.generator import generate_distance_matrix
    from ColGenIP_CP.cpgenerator import CPPatternGenerator
    from ColGenIP_IP.MIP_col_gen import MIPPatternGenerator
    
    n = 4
    dist = generate_distance_matrix(n)
    
    # __init__(self, n_teams: int, lower: int, upper: int, distances: list):
    sattelite_MIP = MIPPatternGenerator
    
    # 
    sattelite_CP = CPPatternGenerator
    
    #  __init__(self, n_teams: int, distances: list, lower: int, upper: int, satt, patterns=[]):
    # ttp_solver = TTPMaster(n, dist, 1, 3, satt1=sattelite_MIP, satt2=sattelite_CP)
    # ttp_solver = TTPMaster(n, dist, 1, 3, satt1=sattelite_MIP)
    ttp_solver = TTPMaster(n, dist, 1, 3, satt2=sattelite_CP)
    ttp_solver.solve(timeout=600)
    # ttp_solver.integer_solver()
