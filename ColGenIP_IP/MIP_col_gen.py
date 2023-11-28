from gurobipy import GRB, Model, Column
from gurobipy import quicksum 
import time

class MIPPatternGenerator:
    def __init__(self, n_teams: int, lower: int, upper: int, distances: list):
        self.N = n_teams
        self.teams = range(n_teams)
        self.S = 2 * n_teams - 2
        self.slots = range(2 * n_teams - 2)
        self.lower = lower
        self.upper = upper
        self.D = distances
        self.LINEAR = False

        self.bases = []
        self.hashes_dict = {i: [] for i in self.teams}
        self.M = self.N ** self.S

    def initialize_variables(self, model, home):
        self.home_play = model.addVars(self.teams, self.slots, vtype=GRB.BINARY, name='home')
        self.away_play = model.addVars(self.teams, self.slots, vtype=GRB.BINARY, name='away')
        self.y = model.addVars(self.teams, self.teams, self.slots, vtype=GRB.BINARY, name='y')
        self.hash = model.addVar(vtype=GRB.INTEGER, name='hash')

        # aux_hash[i] = 1 <-> hash > self.hashes_dict[home] 
        self.aux_hash = {}
        for i, h in enumerate(self.hashes_dict[home]):
            self.aux_hash[i] = model.addVar(lb=0, ub=1,vtype=GRB.INTEGER, name=f'aux_hash_{h}')

        if self.hashes_dict[home]:
            self.M = max(self.hashes_dict[home]) + 1
        
    def initialize_constraints(self, model, home):
        # R1 ningun equipo juega contrasigo mismo
        model.addConstrs(
            self.home_play[home, s] + self.away_play[home, s] == 0 
            for s in self.slots
        )

        # R2 Cada equipo juega un partido por slot
        model.addConstrs(
            quicksum(self.home_play[j, s] + self.away_play[j, s] for j in self.teams) == 1
            for s in self.slots
        )
        
        # R3 Cada equipo juega contra un equipo en casa y away
        model.addConstrs(
            quicksum(self.home_play[j, s] for s in self.slots) == 1
            for j in self.teams if j != home
        )
        model.addConstrs(
            quicksum(self.away_play[j, s] for s in self.slots) == 1
            for j in self.teams if j != home
        )
        
        # R4 Cada equipo juega a lo menos L partidos consecutivos y a lo más U partidos consecutivos
        model.addConstrs(
            quicksum(self.home_play[j, s + l] for l in range(self.upper + 1) for j in self.teams) <= self.upper
            for s in range(2 * self.N - 2 - self.upper)
        )
        model.addConstrs(
            quicksum(self.away_play[j, s + l] for l in range(self.upper + 1) for j in self.teams) <= self.upper
            for s in range(2 * self.N - 2 - self.upper)
        )

        # R4 Cada equipo juega a lo menos L partidos consecutivos y a lo más U partidos consecutivos
        model.addConstrs(
            quicksum(self.home_play[j, s + l] for l in range(self.upper + 1) for j in self.teams) >= self.lower
            for s in range(2 * self.N - 2 - self.upper)
        )
        model.addConstrs(
            quicksum(self.away_play[j, s + l] for l in range(self.upper + 1) for j in self.teams) >= self.lower
            for s in range(2 * self.N - 2 - self.upper)
        )
        
        # R8 Definir si home debe ir de i a j
        # Home -> Away
        model.addConstrs(
            self.y[home, j, s] >= self.home_play[i, s] + self.away_play[j, s + 1] - 1
            for i in self.teams for j in self.teams for s in range(2 * self.N - 3)
        )
        # Away ->  Away
        model.addConstrs(
            self.y[i, j, s] >= self.away_play[i, s] + self.away_play[j, s + 1] - 1
            for i in self.teams for j in self.teams for s in range(2 * self.N - 3)
        )
        # Home -> Home
        model.addConstrs(
            self.y[home, home, s] >= self.home_play[i, s] + self.home_play[j, s + 1] - 1
            for i in self.teams for j in self.teams for s in range(2 * self.N - 3)
        )
        # Away -> Home
        model.addConstrs(
            self.y[i, home, s] >= self.away_play[i, s] + self.home_play[j, s + 1] - 1
            for i in self.teams for j in self.teams for s in range(2 * self.N - 3)
        )

        # Hashes
        model.addConstr(
            self.hash == quicksum(self.away_play[j, s] * (j + 1) * (self.N + 1) ** s for j in self.teams for s in self.slots)
        )
        for i, h in enumerate(self.hashes_dict[home]):
            if self.LINEAR:
                model.addConstr(self.hash <= h - 1 + self.M * self.aux_hash[i])
                model.addConstr(self.hash >= (h + 1) - self.M * (1 - self.aux_hash[i]))
            else:
                model.addConstr(self.hash * (1 - self.aux_hash[i]) -1e-12 <= h - 1)
                model.addConstr(self.hash >= (h + 1) * self.aux_hash[i] -1e-12)
            
        model.update()

    def initialize_objective(self, model, home, pi):

        model.setObjective(
            quicksum([self.D[i][j] * self.y[i, j, s] for i in self.teams for j in self.teams for s in self.slots]) 
            + quicksum([self.D[home][j] * self.away_play[j, self.slots[0]] for j in self.teams])  
            + quicksum([self.D[j][home] * self.away_play[j, self.slots[-1]] for j in self.teams])
            - quicksum((pi[self.N + home * len(self.slots) + s] 
                + pi[self.N + t * len(self.slots) + s]) * (self.away_play[t, s])
                for s in self.slots for t in self.teams
            ) 
            - pi[home]
            , GRB.MINIMIZE
        )

        model.update()

    def single_solve(self, home, pi):
        model = Model()
        model.setParam('OutputFlag', 0)
        start = time.time()
        self.initialize_variables(model, home)
        self.initialize_constraints(model, home)
        self.initialize_objective(model, home, pi)
        model.optimize()
        end = time.time()
        ans = dict()
        if model.status == GRB.OPTIMAL:
            ans['status'] = 'Feasible'
            HAPattern = []
            for s in self.slots:
                for j in self.teams:
                    if self.away_play[j, s].X > 0.5:
                        HAPattern.append(j)
                    elif self.home_play[j, s].X > 0.5:
                        HAPattern.append(home)

            ans['pattern'] = tuple(HAPattern)
            ans['obj_val'] = model.ObjVal
            ans['time'] = end - start

            if ans['obj_val'] < 0.5:
                self.hashes_dict[home].append(int(self.hash.X + 1e-12))
            
        elif model.status == GRB.INFEASIBLE:
            ans['status'] = 'Infeasible'
            self.hashes_dict[home] = []
            print('EEO')

        return ans
    
    def single_gen_solve(self, home):
        model = Model()
        model.setParam('OutputFlag', 0)
        self.initialize_variables(model, home)
        self.initialize_constraints(model, home)

        model.optimize()
        ans = dict()
        if model.status == GRB.OPTIMAL or model.status == GRB.SUBOPTIMAL or (model.status == GRB.TIME_LIMIT and model.solCount > 0):
            ans['status'] = 'Feasible'
            HAPattern = []
            
            for s in self.slots:
                for j in self.teams:
                    if self.away_play[j, s].X > 0.5:
                        HAPattern.append(j)
                    elif self.home_play[j, s].X > 0.5:
                        HAPattern.append(home)

            ans['pattern'] = tuple(HAPattern)
        
        else:
            ans['status'] = 'Infeasible'

        return ans


if __name__ == '__main__':
    from inst_gen.generator import generate_distance_matrix
    

    n = 4
    distances = generate_distance_matrix(n)
    ph = []

    generator = MIPPatternGenerator(n, 1, 3, distances)

    home = 0
    patts = []
    iters = 121
    
    patterns = set()
    
    start = time.time()
    for _ in range(iters):
        ans = generator.single_gen_solve(home)
        print(generator.hashes_dict[home][-1])
        print(ans)

    end = time.time()
    
    

    # print(end - start)
