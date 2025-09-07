import logging
import re
import time
import tracemalloc
from typing import List, Dict, Optional, Tuple

# --- SymPy Imports ---
from sympy import (
    Symbol as SympySymbol, Integer, Float, Add, Mul, Pow,
    sin, cos, tan, exp, log, sqrt, sec, csc, cot, S, latex, diff
)
from sympy.core.numbers import Number

# --- Logger Setup ---
logger = logging.getLogger(__name__)

# --- DAG Node ---
class DAGNode:
    def __init__(self, value, children: Optional[Tuple['DAGNode', ...]] = None):
        self.value = value
        self.children = children or tuple()
        self._hash = None

    def __hash__(self):
        if self._hash is None:
            self._hash = hash((self.value, self.children))
        return self._hash

    def __eq__(self, other):
        if not isinstance(other, DAGNode):
            return NotImplemented
        return self.value == other.value and self.children == other.children

    def __repr__(self):
        return f"DAGNode({self.value}, children={self.children})"

# --- Tokenizer and Parser ---
TOKEN_NUMBER = 'NUMBER'
TOKEN_SYMBOL = 'SYMBOL'
TOKEN_FUNCTION = 'FUNCTION'
TOKEN_OPERATOR = 'OPERATOR'
TOKEN_LPAREN = 'LPAPAREN'
TOKEN_RPAREN = 'RPAREN'
TOKEN_EOF = 'EOF'

class Token:
    def __init__(self, type: str, value: str):
        self.type = type
        self.value = value
    def __repr__(self):
        return f"Token({self.type}, '{self.value}')"

class Tokenizer:
    TOKEN_SPECS = [
        (r'\d+\.?\d*|\.\d+', TOKEN_NUMBER),
        (r'sin|cos|tan|exp|log|sqrt|sec|csc|cot', TOKEN_FUNCTION),
        (r'[a-zA-Z_][a-zA-Z0-9_]*', TOKEN_SYMBOL),
        (r'[\+\-\*\/^]', TOKEN_OPERATOR),
        (r'\(', TOKEN_LPAREN),
        (r'\)', TOKEN_RPAREN),
        (r'\s+', None),
    ]

    def __init__(self, expression_string: str):
        self.expression_string = expression_string
        self.tokens = self._tokenize()
        self.current_token_index = 0

    def _tokenize(self) -> List[Token]:
        tokens = []
        position = 0
        while position < len(self.expression_string):
            match = None
            for pattern, token_type in self.TOKEN_SPECS:
                regex = re.compile(pattern)
                match = regex.match(self.expression_string, position)
                if match:
                    if token_type:
                        tokens.append(Token(token_type, match.group(0)))
                    position = match.end(0)
                    break
            if not match:
                raise ValueError(f"Unexpected character at position {position}")
        tokens.append(Token(TOKEN_EOF, ''))
        return tokens
    
    def next(self) -> Token:
        if self.current_token_index < len(self.tokens):
            token = self.tokens[self.current_token_index]
            self.current_token_index += 1
            return token
        return Token(TOKEN_EOF, '')

class Parser:
    def __init__(self, tokenizer: Tokenizer, custom_vars: Dict[str, SympySymbol]):
        self.tokenizer = tokenizer
        self.custom_vars = custom_vars
        self.current_token = self.tokenizer.next()
        self.supported_sympy_functions = {
            "sqrt": sqrt, "sin": sin, "cos": cos, "tan": tan, "exp": exp,
            "log": log, "sec": sec, "csc": csc, "cot": cot
        }

    def _eat(self, token_type: str):
        if self.current_token.type == token_type:
            self.current_token = self.tokenizer.next()
        else:
            raise ValueError(f"Expected {token_type}, got {self.current_token.type}")

    def parse(self):
        result = self._expr()
        if self.current_token.type != TOKEN_EOF:
            raise ValueError("Unexpected token at end of expression")
        return result

    def _expr(self):
        node = self._term()
        while self.current_token.type == TOKEN_OPERATOR and self.current_token.value in ('+', '-'):
            op = self.current_token.value
            self._eat(TOKEN_OPERATOR)
            right = self._term()
            node = Add(node, right) if op == '+' else Add(node, Mul(S.NegativeOne, right))
        return node

    def _term(self):
        node = self._factor()
        while self.current_token.type == TOKEN_OPERATOR and self.current_token.value in ('*', '/'):
            op = self.current_token.value
            self._eat(TOKEN_OPERATOR)
            right = self._factor()
            node = Mul(node, right) if op == '*' else Mul(node, Pow(right, S.NegativeOne))
        return node

    def _factor(self):
        node = self._atom()
        if self.current_token.type == TOKEN_OPERATOR and self.current_token.value == '^':
            self._eat(TOKEN_OPERATOR)
            right = self._factor()
            node = Pow(node, right)
        return node

    def _atom(self):
        token = self.current_token
        if token.type == TOKEN_NUMBER:
            self._eat(TOKEN_NUMBER)
            return Float(token.value) if '.' in token.value else Integer(token.value)
        elif token.type == TOKEN_SYMBOL:
            self._eat(TOKEN_SYMBOL)
            return self.custom_vars.get(token.value, SympySymbol(token.value))
        elif token.type == TOKEN_FUNCTION:
            func_name = token.value
            self._eat(TOKEN_FUNCTION)
            self._eat(TOKEN_LPAREN)
            arg = self._expr()
            self._eat(TOKEN_RPAREN)
            return self.supported_sympy_functions[func_name](arg)
        elif token.type == TOKEN_LPAREN:
            self._eat(TOKEN_LPAREN)
            node = self._expr()
            self._eat(TOKEN_RPAREN)
            return node
        elif token.type == TOKEN_OPERATOR and token.value == '-':
            self._eat(TOKEN_OPERATOR)
            return Mul(S.NegativeOne, self._factor())
        raise ValueError(f"Unexpected token: {token}")

# --- Helper Functions ---
def _add_step(steps_list, expr, rule_key, explanation, prefix="= "):
    steps_list.append({
        "id": f"step_{len(steps_list)}_{rule_key}",
        "prefix": prefix,
        "parts": [{"latex": latex(expr), "rule_id": rule_key, "explanation_key": rule_key}],
        "explanation_text": explanation
    })

def parse_sympy_to_dag(expr, node_map: Dict[SympySymbol, 'DAGNode']):
    if expr in node_map:
        return node_map[expr]

    if not hasattr(expr, 'args') or not expr.args:
        node = DAGNode(expr)
        node_map[expr] = node
        return node

    children = tuple(parse_sympy_to_dag(arg, node_map) for arg in expr.args)
    node = DAGNode(expr.func, children)
    node_map[expr] = node
    return node

def dag_to_sympy(node):
    if not node.children:
        return node.value
    return node.value(*[dag_to_sympy(child) for child in node.children])

def compute_derivative_dag(expression_str: str, variable_str: str):
    steps = []

    def _add_step_dag(expr_node, rule_key, explanation, prefix="= "):
        _add_step(steps, dag_to_sympy(expr_node), rule_key, explanation, prefix)

    tracemalloc.start()
    start_time = time.perf_counter()

    try:
        tokenizer = Tokenizer(expression_str)
        variable_symbol = SympySymbol(variable_str)
        parser = Parser(tokenizer, {variable_str: variable_symbol})
        sympy_expr = parser.parse()

        dag_node_map = {}
        dag_tree = parse_sympy_to_dag(sympy_expr, dag_node_map)

        _add_step_dag(dag_tree, "initial_expression", "Differentiating:", prefix=f"\\frac{{d}}{{d{latex(variable_symbol)}}}")

        memo = {}
        def _compute_dag_derivative_recursive(node, var):
            if node in memo:
                return memo[node]
            
            # --- Base cases ---
            if not node.children:
                sympy_node = dag_to_sympy(node)
                if sympy_node == var:
                    _add_step(steps, S.One, "variableRule", f"The derivative of {variable_str} is 1.")
                    result = DAGNode(S.One)
                elif isinstance(sympy_node, (Number, int, float)) or not sympy_node.has(var):
                    _add_step(steps, S.Zero, "constantRule", f"The derivative of constant {latex(sympy_node)} is 0.")
                    result = DAGNode(S.Zero)
                else:
                    derivative_segment = diff(sympy_node, var)
                    _add_step(steps, derivative_segment, "leaf_fallback", f"Fallback for leaf node {latex(sympy_node)}.")
                    result = parse_sympy_to_dag(derivative_segment, dag_node_map) # Cache and re-use
                memo[node] = result
                return result
            
            op = node.value
            args = node.children

            # --- Operator rules ---
            if op == Add:
                _add_step_dag(node, "sumRule_start", "Applying the Sum Rule: (f+g)' = f' + g'")
                result_children = tuple(_compute_dag_derivative_recursive(arg, var) for arg in args)
                result_node = DAGNode(Add, result_children)
                _add_step_dag(result_node, "sumRule_result", "The sum of the derivatives is:")
                memo[node] = result_node
                return result_node
            
            if op == Mul:
                _add_step_dag(node, "productRule_start", "Applying the Product Rule.")
                terms = []
                for i in range(len(args)):
                    d_terms = []
                    for j, child in enumerate(args):
                        d_terms.append(_compute_dag_derivative_recursive(child, var) if i == j else child)
                    terms.append(DAGNode(Mul, tuple(d_terms)))
                result_node = DAGNode(Add, tuple(terms))
                _add_step_dag(result_node, "productRule_result", "The result of the Product Rule is:")
                memo[node] = result_node
                return result_node

            if op == Pow:
                _add_step_dag(node, "powerRule_start", "Applying the Power Rule or related rules.")
                base, exp_node = args
                if not dag_to_sympy(exp_node).has(var):
                    du = _compute_dag_derivative_recursive(base, var)
                    new_exp = parse_sympy_to_dag(dag_to_sympy(exp_node) - 1, dag_node_map)
                    result_node = DAGNode(Mul, (exp_node, DAGNode(Pow, (base, new_exp)), du))
                    _add_step_dag(result_node, "powerRule_result", "Result of the Power Rule (u^n)' = n*u^(n-1)*u':")
                    memo[node] = result_node
                    return result_node

            def apply_chain_rule(rule_name, display_rule, result_func):
                u_node = args[0]
                _add_step_dag(node, f"{rule_name}Rule_start", f"Applying the Chain Rule for {rule_name}(u): {display_rule}")
                du_node = _compute_dag_derivative_recursive(u_node, var)
                result_node = result_func(u_node, du_node)
                _add_step_dag(result_node, f"{rule_name}Rule_result", f"The result for the {rule_name} function is:")
                return result_node

            if op == sin:
                result = apply_chain_rule("sin", r"", lambda u, du: DAGNode(Mul, (DAGNode(cos, (u,)), du)))
                memo[node] = result
                return result
            if op == cos:
                result = apply_chain_rule("cos", r"", lambda u, du: DAGNode(Mul, (DAGNode(S.NegativeOne), DAGNode(sin, (u,)), du)))
                memo[node] = result
                return result
            if op == tan:
                result = apply_chain_rule("tan", r"", lambda u, du: DAGNode(Mul, (DAGNode(Pow, (DAGNode(sec, (u,)), DAGNode(S(2),))), du)))
                memo[node] = result
                return result
            if op == sec:
                result = apply_chain_rule("sec", r"", lambda u, du: DAGNode(Mul, (DAGNode(sec, (u,)), DAGNode(tan, (u,)), du)))
                memo[node] = result
                return result
            if op == csc:
                result = apply_chain_rule("csc", r"", lambda u, du: DAGNode(Mul, (DAGNode(S.NegativeOne), DAGNode(csc, (u,)), DAGNode(cot, (u,)), du)))
                memo[node] = result
                return result
            if op == cot:
                result = apply_chain_rule("cot", r"", lambda u, du: DAGNode(Mul, (DAGNode(S.NegativeOne), DAGNode(Pow, (DAGNode(csc, (u,)), DAGNode(S(2),))), du)))
                memo[node] = result
                return result
            if op == exp:
                result = apply_chain_rule("exp", r"", lambda u, du: DAGNode(Mul, (DAGNode(exp, (u,)), du)))
                memo[node] = result
                return result
            if op == log:
                result = apply_chain_rule("log", r"", lambda u, du: DAGNode(Mul, (DAGNode(Pow, (u, DAGNode(S.NegativeOne),)), du)))
                memo[node] = result
                return result

            # --- Fallback ---
            sympy_segment = dag_to_sympy(node)
            _add_step(steps, sympy_segment, "unknownRule_sympy_fallback", "No specific DAG rule matched. Using a fallback.")
            derivative_segment = diff(sympy_segment, var)
            result = parse_sympy_to_dag(derivative_segment, dag_node_map)
            memo[node] = result
            return result
        
        differentiated_dag = _compute_dag_derivative_recursive(dag_tree, variable_symbol)
        final_derivative = dag_to_sympy(differentiated_dag)

    finally:
        end_time = time.perf_counter()
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    
    _add_step(steps, final_derivative, "final_derivative", "The final derivative is:")
    
    dag_node_count = len(dag_node_map)

    return {
        "derivative_latex": latex(final_derivative),
        "steps": steps,
        "execution_time_ms": (end_time - start_time) * 1000,
        "peak_memory_bytes": peak_memory,
        "dag_node_count": dag_node_count,
    }

    
