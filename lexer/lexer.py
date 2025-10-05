class Token:
    def __init__(self, tipo, valor, linea, columna):
        # Inicializa el tipo de token, su valor, y posición en el código fuente
        self.tipo = tipo
        self.valor = valor
        self.linea = linea
        self.columna = columna

    def __str__(self):
        # Retorna una representación legible del token
        return f"Token(tipo={self.tipo}, valor={self.valor}, linea={self.linea}, columna={self.columna})"


class Lexer:
    def __init__(self, codigo_fuente):
        # Recibe el código fuente como cadena
        self.codigo_fuente = codigo_fuente
        self.longitud = len(codigo_fuente)
        self.indice = 0
        self.linea = 1
        self.columna = 1
        self.tokens = []
        self.patrones = self.definir_patrones()

    def definir_patrones(self):
        # Define los patrones regex para cada tipo de token
        import re
        # Nota: lenguaje objetivo JavaScript (subconjunto): palabras clave, identificadores,
        # números, strings, operadores y signos de puntuación comunes.
        patrones = {
            "WHITESPACE": re.compile(r"\s+"),
            "LINE_COMMENT": re.compile(r"//.*"),
            "BLOCK_COMMENT_START": re.compile(r"/\*"),
            "BLOCK_COMMENT_END": re.compile(r"\*/"),
            "STRING": re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\""),
            "NUMBER": re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"),
            "IDENT": re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*"),
            # Operadores multi-caracter primero para hacer backtracking mínimo en analizar()
            "OP": re.compile(r"===|!==|==|!=|<=|>=|&&|\|\||\+\+|--"),
            "PUNCT": re.compile(r"[=;:,(){}\[\].+\-*/%<>!]")
        }
        # Palabras clave soportadas
        self.palabras_clave = {
            "var", "let", "const", "function", "return", "if", "else", "while", "for",
            "true", "false", "null"
        }
        return patrones

    def analizar(self):
        # Aplica los patrones regex al código fuente para generar la lista de tokens
        import re
        while self.indice < self.longitud:
            inicio_linea = self.linea
            inicio_columna = self.columna

            # Espacios en blanco
            m = self.patrones["WHITESPACE"].match(self.codigo_fuente, self.indice)
            if m:
                texto = m.group(0)
                saltos = texto.count("\n")
                if saltos:
                    self.linea += saltos
                    self.columna = 1 + len(texto.rsplit("\n", 1)[-1])
                else:
                    self.columna += len(texto)
                self.indice = m.end()
                continue

            # Comentario de línea
            m = self.patrones["LINE_COMMENT"].match(self.codigo_fuente, self.indice)
            if m:
                texto = m.group(0)
                self.indice = m.end()
                self.columna += len(texto)
                continue

            # Comentario de bloque
            m = self.patrones["BLOCK_COMMENT_START"].match(self.codigo_fuente, self.indice)
            if m:
                self.indice = m.end()
                self.columna += 2
                fin = self.patrones["BLOCK_COMMENT_END"].search(self.codigo_fuente, self.indice)
                if not fin:
                    # Comentario de bloque no cerrado: consumimos hasta el final
                    resto = self.codigo_fuente[self.indice:]
                    self.linea += resto.count("\n")
                    if "\n" in resto:
                        self.columna = 1 + len(resto.rsplit("\n", 1)[-1])
                    else:
                        self.columna += len(resto)
                    self.indice = self.longitud
                    continue
                bloque = self.codigo_fuente[self.indice:fin.end()]
                saltos = bloque.count("\n")
                self.linea += saltos
                if saltos:
                    self.columna = 1 + len(bloque.rsplit("\n", 1)[-1])
                else:
                    self.columna += len(bloque)
                self.indice = fin.end()
                continue

            # Cadenas
            m = self.patrones["STRING"].match(self.codigo_fuente, self.indice)
            if m:
                valor = m.group(0)
                self.tokens.append(Token("STRING", valor, inicio_linea, inicio_columna))
                self.indice = m.end()
                avance = len(valor)
                self.columna += avance
                continue

            # Números
            m = self.patrones["NUMBER"].match(self.codigo_fuente, self.indice)
            if m:
                valor = m.group(0)
                self.tokens.append(Token("NUMBER", valor, inicio_linea, inicio_columna))
                self.indice = m.end()
                self.columna += len(valor)
                continue

            # Identificadores y palabras clave
            m = self.patrones["IDENT"].match(self.codigo_fuente, self.indice)
            if m:
                lexema = m.group(0)
                tipo = "KEYWORD" if lexema in self.palabras_clave else "IDENT"
                self.tokens.append(Token(tipo, lexema, inicio_linea, inicio_columna))
                self.indice = m.end()
                self.columna += len(lexema)
                continue

            # Operadores multi-caracter
            m = self.patrones["OP"].match(self.codigo_fuente, self.indice)
            if m:
                op = m.group(0)
                self.tokens.append(Token("OP", op, inicio_linea, inicio_columna))
                self.indice = m.end()
                self.columna += len(op)
                continue

            # Puntuación y operadores de un solo caracter
            m = self.patrones["PUNCT"].match(self.codigo_fuente, self.indice)
            if m:
                simbolo = m.group(0)
                self.tokens.append(Token("PUNCT", simbolo, inicio_linea, inicio_columna))
                self.indice = m.end()
                self.columna += len(simbolo)
                continue

            # Caracter inesperado
            caracter = self.codigo_fuente[self.indice]
            self.tokens.append(Token("ERROR", caracter, inicio_linea, inicio_columna))
            self.indice += 1
            self.columna += 1

        # Fin de archivo
        self.tokens.append(Token("EOF", "", self.linea, self.columna))
        return self.tokens

    def mostrar_tokens(self):
        # Imprime o retorna la lista de tokens generados
        return [str(t) for t in self.tokens]
