def matrix_print(matrix):
    print(" " * 4, end="")
    for i in range(len(matrix[0])):
        print("{:<4}".format(i), end="")
    print()
    
    for i in range(len(matrix)):
        print("{:<4}".format(i), end="")
        for j in range(len(matrix[0])):
            print("{:<4}".format(matrix[i][j]), end="")
        print()
