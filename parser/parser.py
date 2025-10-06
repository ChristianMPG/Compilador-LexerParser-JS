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
        self.tokens = tokens
        self.pos = 0
        self.errores = []
        self.arbol = None

    # Utilidades internas del parser
    def _actual(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def _avanzar(self):
        token = self._actual()
        self.pos += 1
        return token

    def _mirar(self, offset):
        idx = self.pos + offset
        if 0 <= idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def _coincide(self, tipo=None, valor=None):
        token = self._actual()
        if tipo is not None and token.tipo != tipo:
            return False
        if valor is not None and token.valor != valor:
            return False
        self._avanzar()
        return True

    def _esperar(self, tipo=None, valor=None, mensaje="Token inesperado"):
        token = self._actual()
        if (tipo is None or token.tipo == tipo) and (valor is None or token.valor == valor):
            return self._avanzar()
        self.errores.append(f"{mensaje} en linea {token.linea}, columna {token.columna}: se esperaba {tipo or valor} y se obtuvo {token.tipo}:{token.valor}")
        return self._avanzar()

    def _sincronizar(self):
        # Avanza hasta un límite de sentencia para evitar errores en cascada
        while self._actual().tipo != "EOF":
            tok = self._actual()
            if tok.tipo == "PUNCT" and tok.valor in {";", "}"}:
                break
            self._avanzar()

    def _esperar_punto_y_coma(self):
        # Exige ';', reporta y sincroniza si falta
        tok = self._actual()
        if tok.tipo == "PUNCT" and tok.valor == ";":
            self._avanzar()
        else:
            self.errores.append(f"Se esperaba ';' en linea {tok.linea}, columna {tok.columna}: se obtuvo {tok.tipo}:{tok.valor}")
            self._sincronizar()
            # Si hemos sincronizado y estamos en ';', consumirlo para continuar limpio
            if self._actual().tipo == "PUNCT" and self._actual().valor == ";":
                self._avanzar()

    def parsear(self):
        # Inicia el análisis sintáctico y construye el árbol sintáctico
        programa = NodoAST("Program")
        while self._actual().tipo != "EOF":
            nodo = None
            tok = self._actual()
            if tok.tipo == "KEYWORD" and tok.valor == "function":
                nodo = self.parsear_funcion()
            elif tok.tipo == "KEYWORD" and tok.valor in {"var", "let", "const"}:
                nodo = self.parsear_declaracion()
            else:
                # Detección de patrón de función sin 'function': IDENT ( ) { ... }
                if (
                    tok.tipo == "IDENT"
                    and self._mirar(1).tipo == "PUNCT" and self._mirar(1).valor == "("
                    and self._mirar(2).tipo == "PUNCT" and self._mirar(2).valor == ")"
                    and self._mirar(3).tipo == "PUNCT" and self._mirar(3).valor == "{"
                ):
                    self.errores.append(
                        f"Se esperaba 'function' antes del nombre de funcion en linea {tok.linea}, columna {tok.columna}"
                    )
                    nodo = self._parsear_funcion_sin_keyword()
                else:
                    # Como fallback, intentamos parsear una expresión simple seguida de ";"
                    expr = self.parsear_expresion()
                    self._esperar_punto_y_coma()
                    nodo = NodoAST("ExpressionStatement")
                    nodo.agregar_hijo(expr)
            programa.agregar_hijo(nodo)
        self.arbol = programa
        return programa

    def parsear_declaracion(self):
        # Analiza una declaración de variable (e.g., var x = 5;)
        kw = self._esperar("KEYWORD", None, "Se esperaba palabra clave de declaracion")
        ident = self._esperar("IDENT", None, "Se esperaba identificador de variable")
        decl = NodoAST("VariableDeclaration", kw.valor)
        id_node = NodoAST("Identifier", ident.valor)
        decl.agregar_hijo(id_node)
        if self._coincide("PUNCT", "="):
            expr = self.parsear_expresion()
            init_node = NodoAST("Initializer")
            init_node.agregar_hijo(expr)
            decl.agregar_hijo(init_node)
        self._esperar_punto_y_coma()
        return decl

    def parsear_expresion(self):
        # Analiza expresiones aritméticas (e.g., 5 + 2 * 3)
        # Debe manejar precedencia y asociatividad
        # Implementamos precedencia: llamadas/miembros > multiplicacion/division > suma/resta
        def parsear_primaria():
            tok = self._actual()
            if self._coincide("NUMBER"):
                return NodoAST("NumberLiteral", tok.valor)
            if self._coincide("STRING"):
                return NodoAST("StringLiteral", tok.valor)
            if self._coincide("IDENT"):
                return NodoAST("Identifier", tok.valor)
            if self._coincide("PUNCT", "("):
                expr = parsear_suma_resta()
                self._esperar("PUNCT", ")", "Se esperaba ')'")
                return expr
            # Fallback para tokens inesperados
            self.errores.append(f"Expresion primaria invalida en linea {tok.linea}, columna {tok.columna}: {tok.tipo}:{tok.valor}")
            self._avanzar()
            return NodoAST("Error")

        def parsear_unaria():
            tok = self._actual()
            if tok.tipo == "PUNCT" and tok.valor in {"+", "-", "!"}:
                op = self._avanzar()
                expr = parsear_unaria()
                nodo = NodoAST("UnaryExpression", op.valor)
                nodo.agregar_hijo(expr)
                return nodo
            return parsear_primaria()

        def parsear_postfijo():
            nodo = parsear_unaria()
            while True:
                tok = self._actual()
                # Acceso a miembro: expr . IDENT
                if tok.tipo == "PUNCT" and tok.valor == ".":
                    self._avanzar()
                    ident = self._esperar("IDENT", None, "Se esperaba identificador despues de '.'")
                    miembro = NodoAST("MemberExpression")
                    miembro.agregar_hijo(nodo)
                    miembro.agregar_hijo(NodoAST("Identifier", ident.valor))
                    nodo = miembro
                    continue
                # Llamada: expr ( args )
                if tok.tipo == "PUNCT" and tok.valor == "(":
                    self._avanzar()
                    call = NodoAST("CallExpression")
                    call.agregar_hijo(nodo)
                    args_parent = NodoAST("Arguments")
                    # Argumentos separados por comas
                    if not (self._actual().tipo == "PUNCT" and self._actual().valor == ")"):
                        arg = parsear_suma_resta()
                        args_parent.agregar_hijo(arg)
                        while self._actual().tipo == "PUNCT" and self._actual().valor == ",":
                            self._avanzar()
                            arg = parsear_suma_resta()
                            args_parent.agregar_hijo(arg)
                    self._esperar("PUNCT", ")", "Se esperaba ')'")
                    call.agregar_hijo(args_parent)
                    nodo = call
                    continue
                break
            return nodo

        def parsear_mul_div():
            nodo = parsear_postfijo()
            while True:
                tok = self._actual()
                if tok.tipo == "PUNCT" and tok.valor in {"*", "/", "%"}:
                    op = self._avanzar()
                    derecho = parsear_postfijo()
                    nuevo = NodoAST("BinaryExpression", op.valor)
                    nuevo.agregar_hijo(nodo)
                    nuevo.agregar_hijo(derecho)
                    nodo = nuevo
                else:
                    break
            return nodo

        def parsear_suma_resta():
            nodo = parsear_mul_div()
            while True:
                tok = self._actual()
                if tok.tipo == "PUNCT" and tok.valor in {"+", "-"}:
                    op = self._avanzar()
                    derecho = parsear_mul_div()
                    nuevo = NodoAST("BinaryExpression", op.valor)
                    nuevo.agregar_hijo(nodo)
                    nuevo.agregar_hijo(derecho)
                    nodo = nuevo
                else:
                    break
            return nodo

        return parsear_suma_resta()

    def parsear_funcion(self):
        # Analiza una declaración de función (e.g., function foo() { ... })
        self._esperar("KEYWORD", "function", "Se esperaba 'function'")
        nombre = self._esperar("IDENT", None, "Se esperaba nombre de funcion")
        self._esperar("PUNCT", "(", "Se esperaba '('")
        # Para simplificar, no parseamos parametros en este subconjunto
        self._esperar("PUNCT", ")", "Se esperaba ')'")
        self._esperar("PUNCT", "{", "Se esperaba '{'")
        bloque = self._parsear_bloque()
        func = NodoAST("FunctionDeclaration")
        func.agregar_hijo(NodoAST("Identifier", nombre.valor))
        func.agregar_hijo(bloque)
        return func

    def _parsear_funcion_sin_keyword(self):
        # Variante: parsea IDENT () { ... } reportando previamente el error de falta de 'function'
        nombre = self._esperar("IDENT", None, "Se esperaba nombre de funcion")
        self._esperar("PUNCT", "(", "Se esperaba '('")
        self._esperar("PUNCT", ")", "Se esperaba ')'")
        self._esperar("PUNCT", "{", "Se esperaba '{'")
        bloque = self._parsear_bloque()
        func = NodoAST("FunctionDeclaration")
        func.agregar_hijo(NodoAST("Identifier", nombre.valor))
        func.agregar_hijo(bloque)
        return func

    def _parsear_bloque(self):
        # Parsea sentencias hasta la '}' correspondiente y devuelve un NodoAST("Block") poblado
        bloque = NodoAST("Block")
        cerro_bloque = False
        while self._actual().tipo != "EOF":
            tok = self._actual()
            if tok.tipo == "PUNCT" and tok.valor == "}":
                self._avanzar()
                cerro_bloque = True
                break
            if tok.tipo == "KEYWORD" and tok.valor in {"var", "let", "const"}:
                stmt = self.parsear_declaracion()
                bloque.agregar_hijo(stmt)
                continue
            if tok.tipo == "KEYWORD" and tok.valor == "function":
                stmt = self.parsear_funcion()
                bloque.agregar_hijo(stmt)
                continue
            expr = self.parsear_expresion()
            self._esperar_punto_y_coma()
            stmt = NodoAST("ExpressionStatement")
            stmt.agregar_hijo(expr)
            bloque.agregar_hijo(stmt)
        if not cerro_bloque:
            tok = self._actual()
            self.errores.append(f"Se esperaba '}}' para cerrar bloque en linea {tok.linea}, columna {tok.columna}")
        return bloque

    def detectar_errores(self):
        # Detecta errores sintácticos y los almacena para mostrar al usuario
        return self.errores

    def mostrar_arbol(self):
        # Muestra el árbol sintáctico generado
        if self.arbol is None:
            self.parsear()
        self.arbol.mostrar()
