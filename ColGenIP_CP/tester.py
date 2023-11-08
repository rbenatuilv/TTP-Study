def check_hash(pattern, home, n):
    hash_val = 0
    for i in range(len(pattern)):
        if pattern[i] != home:
            hash_val += pattern[i] * (n ** i)

    return hash_val


if __name__ == '__main__':
    p1 = (1, 5, 4, 4, 4, 0, 2, 3, 4, 4)

    hola = 933151.0

    print(check_hash(p1, 4, 6))

    lista = [
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    ]

    hola = [int(lista[i][j]) * i * (6 ** j) for j in range(len(lista[0])) for i in range(len(lista))]
    print(sum(hola))

    # for key in hola:
    #     print(key, hola[key])