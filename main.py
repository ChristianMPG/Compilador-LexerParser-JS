class Compilador:
    def __init__(self, ruta_archivo):
        # Carga el archivo fuente y prepara los módulos léxico y sintáctico
        from lexer.lexer import Lexer
        self.ruta_archivo = ruta_archivo
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            self.codigo_fuente = f.read()
        # Inicializa lexer con el código fuente
        self.lexer = Lexer(self.codigo_fuente)
        self.tokens = []
        self.parser = None

    def ejecutar(self):
        # Ejecuta el análisis léxico y sintáctico
        # Muestra tokens, árbol sintáctico y errores
        from parser.parser import Parser
        # Análisis léxico
        self.tokens = self.lexer.analizar()
        # Mostrar tokens
        for linea in self.lexer.mostrar_tokens():
            print(linea)
        # Análisis sintáctico
        self.parser = Parser(self.tokens)
        arbol = self.parser.parsear()
        # Mostrar árbol sintáctico
        print("\nAST:")
        self.parser.mostrar_arbol()
        # Mostrar errores si existen
        errores = self.parser.detectar_errores()
        if errores:
            print("\nErrores:")
            for e in errores:
                print(e)

if __name__ == "__main__":
    Compilador("samples/suma.js").ejecutar()
