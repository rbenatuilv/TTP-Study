from gurobipy import GRB, Model, Column
from gurobipy import quicksum 
from cpgenerator import CPPatternGenerator


class TTPSolverIPCP:
    def __init__(self, n_teams: int, distances: list, lower: int, upper: int):
        self.N = n_teams
        self.teams = range(n_teams)
        self.slots = range(2 * n_teams - 2)

        self.distances = distances

        self.lower = lower
        self.upper = upper

        self.master = Model()
        self.sattelite = CPPatternGenerator(n_teams, lower, upper)

    def initialize(self):
        self.create_aux_sets()
        self.set_vars()
        self.set_constrs()
        self.set_objective()

    def create_aux_sets(self):
        self.set_initial_patterns()
        self.set_team_patterns()
        self.set_home_patterns()
        self.set_away_patterns()

    def set_initial_patterns(self):
        self.patterns = []
        for i in self.teams:
            ans = self.sattelite.solve(i, [])
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

    