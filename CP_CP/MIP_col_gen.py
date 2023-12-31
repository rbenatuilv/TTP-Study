from gurobipy import GRB, Model, Column
from gurobipy import quicksum 

class MIPPatternGenerator:
    def __init__(self, n_teams: int, lower: int, upper: int, ):
        self.N = n_teams
        self.teams = range(n_teams)
        self.duplicated_teams = range(n_teams)
        self.slots = range(2 * n_teams - 2)
        self.lower = lower
        self.upper = upper
    
    def initialize_variables(self, model, home):
        self.home_play = model.addVars(self.teams, self.slots, vtype=GRB.BINARY, name='x')
        self.away_play = model.addVars(self.teams, self.slots, vtype=GRB.BINARY, name='x')
        self.y = model.addVars(self.teams, self.teams, self.slots, vtype=GRB.BINARY, name='y')
        
    def initilize_constraints(self, model, home, D):
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
        
        model.setObjective(
            quicksum(self.away_play[j, 1] * D[home][j] for j in self.teams) 
            + quicksum(self.y[i, j, s] * D[i][j] for i in self.teams for j in self.teams for s in range(2 * self.N - 2))
            + quicksum(self.away_play[j, 2 * self.N - 3] * D[j][home] for j in self.teams)        
            , GRB.MINIMIZE
        )

        model.update()
   
    
    def single_solve(self, home, distances):
        model = Model()
        self.initialize_variables(model, home)
        self.initilize_constraints(model, home, distances)
        model.optimize()
        ans = dict()
        if model.status == GRB.OPTIMAL:
            ans['status'] = 'Feasible'
            HAPattern = []
            for s in self.slots:
                for j in self.teams:
                    if self.away_play[j, s].X:
                        HAPattern.append(j)
                    elif self.home_play[j, s].X:
                        HAPattern.append(home)
            ans['pattern'] = HAPattern
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

    generator = MIPPatternGenerator(n, 1, 3)

    home = 4
    patts = []
    iters = 1

    start = time.time()
    for _ in range(iters):
        ans = generator.single_solve(home, distances)
        print(ans)
        print("yahoooo")

    end = time.time()

    print(end - start)
