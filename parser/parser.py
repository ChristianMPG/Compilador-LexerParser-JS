# Clase NodoAST
class NodoAST:
    def __init__(self, tipo, valor=None):
        self.tipo = tipo
        self.valor = valor
        self.hijos = []

    def agregar_hijo(self, nodo):
        self.hijos.append(nodo)

    def mostrar(self, nivel=0):
        print("  " * nivel + f"{self.tipo}: {self.valor if self.valor else ''}")
        for hijo in self.hijos:
            hijo.mostrar(nivel + 1)



# Clase Parser
class Parser:
    def __init__(self, tokens):
        # Recibe la lista de tokens generada por el lexer
        pass

    def parsear(self):
        # Inicia el análisis sintáctico y construye el árbol sintáctico
        pass

    def parsear_declaracion(self):
        # Analiza una declaración de variable (e.g., var x = 5;)
        pass

    def parsear_expresion(self):
        # Analiza expresiones aritméticas (e.g., 5 + 2 * 3)
        # Debe manejar precedencia y asociatividad
        pass

    def parsear_funcion(self):
        # Analiza una declaración de función (e.g., function foo() { ... })
        pass

    def detectar_errores(self):
        # Detecta errores sintácticos y los almacena para mostrar al usuario
        pass

    def mostrar_arbol(self):
        # Muestra el árbol sintáctico generado
        pass
