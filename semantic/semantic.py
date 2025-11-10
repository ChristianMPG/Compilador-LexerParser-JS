
class Symbol:
    def __init__(self, name, kind, data_type="unknown", mutable=True, node=None, scope=None, members=None):
        self.name = name
        self.kind = kind
        self.data_type = data_type
        self.mutable = mutable
        self.node = node
        self.scope = scope
        self.members = members or {}

    @property
    def scope_name(self):
        if self.scope:
            return self.scope.scope_name
        return "?"


class SymbolTable:
    def __init__(self, scope_name="global", parent=None):
        self.scope_name = scope_name
        self.parent = parent
        self.symbols = {}
        self.children = []

    def define(self, symbol):
        if symbol.name in self.symbols:
            return False
        symbol.scope = self
        self.symbols[symbol.name] = symbol
        return True

    def resolve(self, name):
        scope = self
        while scope:
            if name in scope.symbols:
                return scope.symbols[name]
            scope = scope.parent
        return None

    def create_child(self, scope_name):
        child = SymbolTable(scope_name, parent=self)
        self.children.append(child)
        return child


class SemanticAnalyzer:
    NUMERIC_OPS = {"-", "*", "/", "%"}

    def __init__(self):
        self.errors = []
        self.global_scope = SymbolTable("global")
        self._all_scopes = [self.global_scope]
        self._builtin_members = {
            "console": {
                "log": "function",
                "warn": "function",
                "error": "function",
            }
        }
        self._builtins = [
            Symbol(
                name="console",
                kind="builtin",
                data_type="object",
                mutable=False,
                members=self._builtin_members["console"],
            ),
        ]

    def analyze(self, ast_root):
        self.errors = []
        self.global_scope = SymbolTable("global")
        self._all_scopes = [self.global_scope]
        self._register_builtins()
        if ast_root is None:
            self._error("No se proporciono un AST para analizar")
            return self.errors
        self._visit(ast_root, self.global_scope)
        return self.errors

    def get_scopes(self):
        return self._all_scopes

    def get_symbol_rows(self):
        rows = []
        for scope in self._all_scopes:
            for symbol in scope.symbols.values():
                rows.append(self._symbol_to_row(symbol))
        return rows

    def format_symbol_table(self):
        rows = self.get_symbol_rows()
        headers = ["Nombre", "Tipo", "Rol/Categoria", "Ambito", "Otros Atributos"]
        if not rows:
            return "Tabla de simbolos vacia."
        widths = {header: len(header) for header in headers}
        for row in rows:
            for header in headers:
                widths[header] = max(widths[header], len(row[header]))

        def render_line(row_dict):
            return " | ".join(row_dict[h].ljust(widths[h]) for h in headers)

        separator = "-+-".join("-" * widths[h] for h in headers)
        lines = [render_line({h: h for h in headers}), separator]
        lines.extend(render_line(row) for row in rows)
        return "\n".join(lines)

    def _visit(self, node, scope):
        if node is None:
            return None
        method = getattr(self, f"_visit_{node.tipo}", self._visit_generic)
        return method(node, scope)

    def _visit_generic(self, node, scope):
        last_type = None
        for child in node.hijos:
            last_type = self._visit(child, scope)
        return last_type

    def _visit_Program(self, node, scope):
        for child in node.hijos:
            self._visit(child, scope)

    def _visit_FunctionDeclaration(self, node, scope):
        if not node.hijos:
            return None
        name_node = node.hijos[0]
        block_node = node.hijos[1] if len(node.hijos) > 1 else None
        name = name_node.valor
        symbol = Symbol(name=name, kind="function", data_type="function", mutable=False, node=node)
        if not scope.define(symbol):
            self._error(f"La funcion '{name}' ya fue declarada en el ambito '{scope.scope_name}'", node)
        func_scope = scope.create_child(f"func:{name}")
        self._all_scopes.append(func_scope)
        if block_node:
            self._visit_block(block_node, func_scope, create_new_scope=False)

    def _visit_Block(self, node, scope):
        self._visit_block(node, scope, create_new_scope=True)

    def _visit_block(self, node, scope, create_new_scope=True):
        current_scope = scope.create_child("block") if create_new_scope else scope
        if create_new_scope:
            self._all_scopes.append(current_scope)
        for stmt in node.hijos:
            self._visit(stmt, current_scope)

    def _visit_VariableDeclaration(self, node, scope):
        if not node.hijos:
            return None
        identifier = node.hijos[0]
        if identifier.tipo != "Identifier" or not identifier.valor:
            return None
        var_name = identifier.valor
        keyword = node.valor or "var"
        init_node = node.hijos[1] if len(node.hijos) > 1 else None
        init_type = None
        if init_node and init_node.hijos:
            init_type = self._visit(init_node.hijos[0], scope)
        mutable = keyword != "const"
        symbol = Symbol(name=var_name, kind="variable", data_type=init_type or "unknown", mutable=mutable, node=node)
        if not scope.define(symbol):
            prev = scope.symbols[var_name]
            if prev.data_type != symbol.data_type and prev.data_type != "unknown":
                self._error(
                    f"La variable '{var_name}' ya declarada como '{prev.data_type}' no puede redeclararse con tipo '{symbol.data_type}'",
                    node,
                )
            else:
                self._error(f"La variable '{var_name}' ya fue declarada en el ambito '{scope.scope_name}'", node)
        return symbol.data_type

    def _visit_ExpressionStatement(self, node, scope):
        if node.hijos:
            return self._visit(node.hijos[0], scope)
        return None

    def _visit_BinaryExpression(self, node, scope):
        if len(node.hijos) < 2:
            return "unknown"
        left_type = self._visit(node.hijos[0], scope)
        right_type = self._visit(node.hijos[1], scope)
        op = node.valor
        if op == "/" and self._is_zero(node.hijos[1]):
            self._error("Division por cero detectada en tiempo de compilacion", node.hijos[1])
        if op in self.NUMERIC_OPS:
            if not self._is_numeric(left_type) or not self._is_numeric(right_type):
                self._error(
                    f"Operador '{op}' requiere operandos numericos, se recibieron '{left_type}' y '{right_type}'",
                    node,
                )
                return "error"
            return "number"
        if op == "+":
            if left_type == "string" and right_type == "string":
                return "string"
            if self._is_numeric(left_type) and self._is_numeric(right_type):
                return "number"
            self._error(
                f"No se puede sumar/concatenar tipos incompatibles '{left_type}' y '{right_type}'",
                node,
            )
            return "error"
        return "unknown"

    def _visit_UnaryExpression(self, node, scope):
        operand_type = self._visit(node.hijos[0], scope) if node.hijos else "unknown"
        op = node.valor
        if op in {"+", "-"} and not self._is_numeric(operand_type):
            self._error(f"El operador unario '{op}' solo acepta numeros, se recibio '{operand_type}'", node)
            return "error"
        if op == "!":
            return "boolean"
        return operand_type

    def _visit_NumberLiteral(self, node, scope):
        return "number"

    def _visit_StringLiteral(self, node, scope):
        return "string"

    def _visit_Identifier(self, node, scope):
        symbol = scope.resolve(node.valor)
        if symbol is None:
            self._error(f"El identificador '{node.valor}' no ha sido declarado", node)
            return "error"
        return symbol.data_type

    def _visit_CallExpression(self, node, scope):
        if not node.hijos:
            return "unknown"
        callee_type = self._visit(node.hijos[0], scope)
        args_node = node.hijos[1] if len(node.hijos) > 1 else None
        if args_node:
            self._visit_Arguments(args_node, scope)
        if callee_type not in {"function", "unknown", "error"}:
            self._error("Solo se pueden invocar funciones o referencias desconocidas", node)
        return "unknown"

    def _visit_Arguments(self, node, scope):
        for arg in node.hijos:
            self._visit(arg, scope)

    def _visit_MemberExpression(self, node, scope):
        if len(node.hijos) < 2:
            return "unknown"
        object_node, member_node = node.hijos[0], node.hijos[1]
        base_type = self._visit(object_node, scope)
        if base_type == "error":
            return "error"
        if member_node.tipo != "Identifier":
            self._error("Solo se admiten identificadores como miembros")
            return "error"
        member_name = member_node.valor
        base_symbol = None
        if object_node.tipo == "Identifier":
            base_symbol = scope.resolve(object_node.valor)
        if base_symbol and base_symbol.kind == "builtin":
            allowed = base_symbol.members
            if member_name not in allowed:
                self._error(f"El miembro '{member_name}' no existe en '{base_symbol.name}'", member_node)
                return "error"
            return allowed[member_name]
        return "unknown"

    def _symbol_to_row(self, symbol):
        kind_display = {
            "variable": "Variable",
            "function": "Funcion",
            "parameter": "Parametro",
            "builtin": "Builtin",
        }.get(symbol.kind, symbol.kind.capitalize())
        others = []
        if symbol.kind == "variable":
            others.append("Mutable" if symbol.mutable else "Constante")
        if symbol.kind == "function":
            others.append("Params: 0")
        if symbol.kind == "builtin" and symbol.members:
            members = ", ".join(sorted(symbol.members.keys()))
            others.append(f"Miembros: {members}")
        return {
            "Nombre": symbol.name,
            "Tipo": symbol.data_type,
            "Rol/Categoria": kind_display,
            "Ambito": symbol.scope_name,
            "Otros Atributos": ", ".join(others) if others else "-",
        }

    def _error(self, message, node=None):
        if node and getattr(node, "linea", None) is not None:
            message = f"{message} (linea {node.linea}, columna {node.columna})"
        self.errors.append(message)

    def _is_numeric(self, data_type):
        return data_type in {"number", "unknown"}

    def _constant_numeric_value(self, node):
        if node is None:
            return None
        if node.tipo == "NumberLiteral":
            try:
                return float(node.valor)
            except ValueError:
                return None
        if node.tipo == "UnaryExpression" and node.hijos:
            val = self._constant_numeric_value(node.hijos[0])
            if val is None:
                return None
            if node.valor == "-":
                return -val
            if node.valor == "+":
                return val
            return None
        if node.tipo == "BinaryExpression" and len(node.hijos) == 2:
            left = self._constant_numeric_value(node.hijos[0])
            right = self._constant_numeric_value(node.hijos[1])
            if left is None or right is None:
                return None
            try:
                if node.valor == "+":
                    return left + right
                if node.valor == "-":
                    return left - right
                if node.valor == "*":
                    return left * right
                if node.valor == "/":
                    return left / right if right != 0 else None
                if node.valor == "%":
                    return left % right if right != 0 else None
            except ZeroDivisionError:
                return None
        return None

    def _is_zero(self, node):
        value = self._constant_numeric_value(node)
        return value is not None and value == 0
    def _register_builtins(self):
        for symbol in self._builtins:
            builtin = Symbol(
                name=symbol.name,
                kind=symbol.kind,
                data_type=symbol.data_type,
                mutable=symbol.mutable,
                members=dict(symbol.members),
            )
            self.global_scope.define(builtin)
