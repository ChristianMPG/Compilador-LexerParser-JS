class Compilador:
    def __init__(self, ruta_archivo):
        # Carga el archivo fuente y prepara los módulos léxico, sintáctico y semántico
        from lexer.lexer import Lexer
        from semantic.semantic import SemanticAnalyzer

        self.ruta_archivo = ruta_archivo
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            self.codigo_fuente = f.read()
        self.lexer = Lexer(self.codigo_fuente)
        self.tokens = []
        self.parser = None
        self.semantic = SemanticAnalyzer()

    def ejecutar(self):
        # Ejecuta el análisis completo y muestra tokens, AST, tabla de símbolos y errores
        from parser.parser import Parser

        self.tokens = self.lexer.analizar()
        for linea in self.lexer.mostrar_tokens():
            print(linea)

        self.parser = Parser(self.tokens)
        arbol = self.parser.parsear()

        print("\nAST:")
        self.parser.mostrar_arbol()

        errores_sintacticos = self.parser.detectar_errores()
        if errores_sintacticos:
            print("\nErrores sintácticos:")
            for e in errores_sintacticos:
                print(e)

        errores_semanticos = self.semantic.analyze(arbol)
        print("\nTabla de símbolos:")
        print(self.semantic.format_symbol_table())

        if errores_semanticos:
            print("\nErrores semánticos:")
            for e in errores_semanticos:
                print(e)


if __name__ == "__main__":
    Compilador("samples/ejemplo.js").ejecutar()
