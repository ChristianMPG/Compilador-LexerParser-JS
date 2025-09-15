class Token:
    def __init__(self, tipo, valor, linea, columna):
        # Inicializa el tipo de token, su valor, y posición en el código fuente
        pass

    def __str__(self):
        # Retorna una representación legible del token
        pass


class Lexer:
    def __init__(self, codigo_fuente):
        # Recibe el código fuente como cadena
        pass

    def definir_patrones(self):
        # Define los patrones regex para cada tipo de token
        pass

    def analizar(self):
        # Aplica los patrones regex al código fuente para generar la lista de tokens
        pass

    def mostrar_tokens(self):
        # Imprime o retorna la lista de tokens generados
        pass
