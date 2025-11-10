from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.semantic import SemanticAnalyzer


SAMPLES_DIR = Path(__file__).parent / "samples"


def load_samples() -> Dict[str, Path]:
    return {path.name: path for path in sorted(SAMPLES_DIR.glob("*.js"))}


def build_ast_graph_dot(node):
    nodes = []
    edges = []

    def add_node(n):
        if n is None:
            return None
        node_id = f"node{id(n)}"
        value = "" if n.valor in (None, "") else str(n.valor)
        value = value.replace("\\", "\\\\").replace('"', '\\"')
        label = n.tipo if not value else f"{n.tipo}\\n{value}"
        nodes.append(f'{node_id} [label="{label}", shape=box, style="rounded,filled", fillcolor="#1f2a44", fontcolor="#f0f3ff"];')
        for child in n.hijos:
            child_id = add_node(child)
            if child_id:
                edges.append(f"{node_id} -> {child_id};")
        return node_id

    add_node(node)
    if not nodes:
        return ""
    dot = [
        "digraph AST {",
        'rankdir=TB;',
        'bgcolor="transparent";',
        *nodes,
        *edges,
        "}",
    ]
    return "\n".join(dot)


def run_compiler(source: str):
    lexer = Lexer(source)
    tokens = lexer.analizar()
    token_rows = [
        {"Tipo": t.tipo, "Valor": t.valor, "Linea": t.linea, "Columna": t.columna}
        for t in tokens
    ]

    parser = Parser(tokens)
    ast = parser.parsear()
    syntax_errors = parser.detectar_errores()

    semantic = SemanticAnalyzer()
    semantic_errors = semantic.analyze(ast)
    symbol_rows = semantic.get_symbol_rows()

    graph_dot = build_ast_graph_dot(parser.arbol) if parser.arbol else ""

    return {
        "token_rows": token_rows,
        "syntax_errors": syntax_errors,
        "semantic_errors": semantic_errors,
        "symbols": symbol_rows,
        "graph_dot": graph_dot,
    }


def _inject_styles():
    st.markdown(
        """
        <style>
            .main {
                background: radial-gradient(circle at top, #111b3a, #05070f);
                color: #f5f7ff;
            }
            h1, h2, h3, h4, h5, h6, .stMarkdown p {
                color: #f5f7ff;
            }
            .stButton>button {
                background: linear-gradient(120deg, #6c63ff, #00c9ff);
                color: white;
                border: none;
                font-weight: 600;
                border-radius: 999px;
                padding: 0.6rem 2rem;
            }
            .stTextArea textarea {
                font-family: "Fira Code", monospace;
                border-radius: 0.6rem;
                border: 1px solid #4d4f61;
                min-height: 320px;
                background-color: #1e1e1e;
                color: #f8f8f2;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 1rem;
            }
            .stTabs [data-baseweb="tab"] {
                background-color: rgba(255,255,255,0.08);
                padding: 0.5rem 1.2rem;
                border-radius: 999px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="PyJS Compiler", layout="wide")
    _inject_styles()

    st.markdown(
        """
        <div style="text-align:center; margin-bottom:1.5rem;">
            <h1 style="margin-bottom:0;font-size:3rem;">
                <span style="color:#3776AB;">Py</span><span style="color:#FFD43B;">JS</span>
                <span style="color:#F7DF1E;">Compiler</span>
            </h1>
            <p style="opacity:0.85;">
                Visualiza cada fase del compilador educativo para un subconjunto de JavaScript.<br/>
                Edita un ejemplo, compila y explora tokens, AST, tabla de símbolos y errores en un solo lugar.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    samples = load_samples()
    if not samples:
        st.error("No se encontraron ejemplos en la carpeta 'samples/'.")
        return

    sample_names = list(samples.keys())
    session = st.session_state
    session.setdefault("selected_sample", sample_names[0])
    session.setdefault("code_editor", samples[session.selected_sample].read_text(encoding="utf-8"))
    session.setdefault("last_result", None)

    selector_col, actions_col = st.columns([3, 1])
    with selector_col:
        selected = st.selectbox(
            "Selecciona un ejemplo",
            sample_names,
            index=sample_names.index(session.selected_sample),
            help="Los archivos provienen de la carpeta samples/",
        )
    if selected != session.selected_sample:
        session.selected_sample = selected
        session.code_editor = samples[selected].read_text(encoding="utf-8")

    with actions_col:
        save_toggle = st.checkbox("Guardar en disco", value=False, help="Escribe los cambios directamente en el archivo.")

    st.text_area(
        "Código fuente",
        key="code_editor",
        help="Puedes editar libremente este código antes de compilar.",
    )

    compile_clicked = st.button("Compilar", use_container_width=True)

    if compile_clicked:
        code = session.code_editor
        if save_toggle:
            samples[session.selected_sample].write_text(code, encoding="utf-8")
        with st.spinner("Analizando el programa..."):
            try:
                session.last_result = run_compiler(code)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Ocurrió un error inesperado: {exc}")
                return

    result = session.last_result
    if not result:
        st.info("Compila un ejemplo para ver los resultados.")
        return

    token_rows = result["token_rows"]
    syntax_errors: List[str] = result["syntax_errors"]
    semantic_errors: List[str] = result["semantic_errors"]
    symbols = result["symbols"]
    graph_dot = result["graph_dot"]

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("Tokens", len(token_rows))
    metric_col2.metric("Errores sintácticos", len(syntax_errors), delta=None)
    metric_col3.metric("Errores semánticos", len(semantic_errors), delta=None)

    tabs = st.tabs(["Tokens y símbolos", "AST", "Errores"])
    with tabs[0]:
        tok_col, sym_col = st.columns(2)
        with tok_col:
            st.markdown("#### Tokens")
            if token_rows:
                st.dataframe(pd.DataFrame(token_rows), use_container_width=True)
            else:
                st.write("No se generaron tokens.")
        with sym_col:
            st.markdown("#### Tabla de símbolos")
            if symbols:
                st.dataframe(pd.DataFrame(symbols), use_container_width=True)
            else:
                st.write("Tabla de símbolos vacía.")
    with tabs[1]:
        if graph_dot:
            st.graphviz_chart(graph_dot)
        else:
            st.write("No se pudo construir el AST.")
    with tabs[2]:
        col_syntax, col_semantic = st.columns(2)
        with col_syntax:
            st.markdown("#### Sintácticos")
            if syntax_errors:
                for err in syntax_errors:
                    st.error(err)
            else:
                st.success("Sin errores sintácticos.")
        with col_semantic:
            st.markdown("#### Semánticos")
            if semantic_errors:
                for err in semantic_errors:
                    st.error(err)
            else:
                st.success("Sin errores semánticos.")


if __name__ == "__main__":
    main()
