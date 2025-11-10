class BytecodeGenerator:
    """Generador de bytecode binario tipo stack."""

    BIN_OP_MAP = {
        "+": "ADD",
        "-": "SUB",
        "*": "MUL",
        "/": "DIV",
        "%": "MOD",
    }

    OPCODES = {
        "PUSH_CONST": "00000001",
        "LOAD_VAR": "00000010",
        "STORE_VAR": "00000011",
        "ADD": "00000100",
        "SUB": "00000101",
        "MUL": "00000110",
        "DIV": "00000111",
        "MOD": "00001000",
        "CALL": "00001001",
        "POP": "00001010",
        "COMMENT": "11111111",
    }

    OPERAND_BITS = 24

    def __init__(self):
        self.instructions = []
        self.symbol_ids = {}
        self.next_symbol_id = 1

    def generate(self, ast_root, binary=True):
        self.instructions = []
        self.symbol_ids = {}
        self.next_symbol_id = 1
        if ast_root:
            self._visit(ast_root)
        if binary:
            return self._to_binary()
        return self.instructions

    def _emit(self, opcode, operand=None):
        self.instructions.append((opcode, operand))

    def _emit_comment(self, text):
        self.instructions.append(("COMMENT", text))

    def _visit(self, node):
        method = getattr(self, f"_visit_{node.tipo}", self._visit_generic)
        return method(node)

    def _visit_generic(self, node):
        for child in node.hijos:
            self._visit(child)

    def _visit_Program(self, node):
        for child in node.hijos:
            self._visit(child)

    def _visit_Block(self, node):
        for child in node.hijos:
            self._visit(child)

    def _visit_FunctionDeclaration(self, node):
        name = node.hijos[0].valor if node.hijos else "anon"
        self._emit_comment(f"Function {name}")
        if len(node.hijos) > 1:
            self._visit(node.hijos[1])
        self._emit_comment(f"EndFunction {name}")

    def _visit_VariableDeclaration(self, node):
        identifier = node.hijos[0].valor if node.hijos else "tmp"
        if len(node.hijos) > 1 and node.hijos[1].hijos:
            self._visit(node.hijos[1].hijos[0])
        else:
            self._emit("PUSH_CONST", "undefined")
        self._emit("STORE_VAR", identifier)

    def _visit_ExpressionStatement(self, node):
        for child in node.hijos:
            self._visit(child)
        self._emit("POP")

    def _visit_NumberLiteral(self, node):
        self._emit("PUSH_CONST", node.valor)

    def _visit_StringLiteral(self, node):
        self._emit("PUSH_CONST", node.valor)

    def _visit_Identifier(self, node):
        self._emit("LOAD_VAR", node.valor)

    def _visit_BinaryExpression(self, node):
        if len(node.hijos) < 2:
            return
        self._visit(node.hijos[0])
        self._visit(node.hijos[1])
        instr = self.BIN_OP_MAP.get(node.valor)
        if instr:
            self._emit(instr)

    def _visit_CallExpression(self, node):
        if not node.hijos:
            return
        args_node = node.hijos[1] if len(node.hijos) > 1 else None
        arg_count = 0
        if args_node:
            for arg in args_node.hijos:
                self._visit(arg)
                arg_count += 1
        target = self._format_call_target(node.hijos[0])
        operand = f"{target}:{arg_count}"
        self._emit("CALL", operand)

    def _format_call_target(self, node):
        if node.tipo == "Identifier":
            return node.valor
        if node.tipo == "MemberExpression":
            return ".".join(self._collect_member_parts(node))
        return "anon"

    def _collect_member_parts(self, node):
        parts = []
        current = node
        while current and current.tipo == "MemberExpression":
            member = current.hijos[1].valor if len(current.hijos) > 1 else ""
            parts.insert(0, member)
            current = current.hijos[0] if current.hijos else None
        if current and current.tipo == "Identifier":
            parts.insert(0, current.valor)
        return parts

    def _to_binary(self):
        lines = []
        for opcode, operand in self.instructions:
            opcode_bits = self.OPCODES.get(opcode, self.OPCODES["COMMENT"])
            operand_bits = self._operand_bits(operand)
            lines.append(f"{opcode_bits} {operand_bits}")
        return lines

    def _operand_bits(self, operand):
        if operand is None:
            return "0" * self.OPERAND_BITS
        if isinstance(operand, (int, float)):
            value = int(float(operand))
            return format(value & ((1 << self.OPERAND_BITS) - 1), f"0{self.OPERAND_BITS}b")
        key = str(operand)
        symbol_id = self.symbol_ids.setdefault(key, self.next_symbol_id)
        if symbol_id == self.next_symbol_id:
            self.next_symbol_id += 1
        return format(symbol_id, f"0{self.OPERAND_BITS}b")
