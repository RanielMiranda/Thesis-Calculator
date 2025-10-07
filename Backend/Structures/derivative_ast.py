import logging
import re
import time
import tracemalloc
from typing import List, Dict, Optional

# --- SymPy Imports ---
from sympy import (
    Symbol as SympySymbol, Integer, Float, Add, Mul, Pow,
    sin, cos, tan, exp, log, sqrt, sec, csc, cot, S, latex, diff
)
from sympy.core.numbers import Number

# --- Logger Setup ---
logger = logging.getLogger(__name__)

# --- Custom AST Data Structure ---
class ASTNode:
    def __init__(self, value, children=None):
        self.value = value
        self.children = children or []

# --- Manual Tokenizer and Parser (included for measurement) ---
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

def parse_sympy_to_ast(expr):
    if not hasattr(expr, 'args') or not expr.args:
        return ASTNode(expr)
    return ASTNode(expr.func, [parse_sympy_to_ast(arg) for arg in expr.args])

def node_to_sympy(node):
    if not node.children:
        return node.value
    return node.value(*[node_to_sympy(child) for child in node.children])

def compute_derivative_ast(expression_str: str, variable_str: str):
    steps = []

    def _add_step_ast(expr_node, rule_key, explanation, prefix="= "):
        _add_step(steps, node_to_sympy(expr_node), rule_key, explanation, prefix)

    tracemalloc.start()
    start_time = time.perf_counter()

    try:
        tokenizer = Tokenizer(expression_str)
        variable_symbol = SympySymbol(variable_str)
        parser = Parser(tokenizer, {variable_str: variable_symbol})
        sympy_expr = parser.parse()
        ast_tree = parse_sympy_to_ast(sympy_expr)

        _add_step_ast(ast_tree, "initial_expression", "Differentiating with AST:", prefix=f"\\frac{{d}}{{d{latex(variable_symbol)}}}")
        
        def _compute_ast_derivative_recursive(node, var):
            if not node.children:
                sympy_node = node_to_sympy(node)
                if sympy_node == var:
                    _add_step(steps, S.One, "variableRule", f"The derivative of {variable_str} is 1.")
                    return ASTNode(S.One)
                if isinstance(sympy_node, (Number, int, float)) or not sympy_node.has(var):
                    _add_step(steps, S.Zero, "constantRule", f"The derivative of a constant is 0.")
                    return ASTNode(S.Zero)
                
                derivative_segment = diff(sympy_node, var)
                _add_step(steps, derivative_segment, "leaf_fallback", f"Fallback for leaf node {latex(sympy_node)}.")
                return parse_sympy_to_ast(derivative_segment)
            
            op = node.value
            args = node.children
            
            if op == Add:
                _add_step_ast(node, "sumRule_start", "Applying the Sum Rule:")
                result_node = ASTNode(Add, [_compute_ast_derivative_recursive(arg, var) for arg in args])
                _add_step_ast(result_node, "sumRule_result", "The sum of the derivatives is:")
                return result_node
            
            if op == Mul:
                _add_step_ast(node, "productRule_start", "Applying the Product Rule.")
                terms = []
                for i in range(len(args)):
                    d_terms = []
                    for j, child in enumerate(args):
                        d_terms.append(_compute_ast_derivative_recursive(child, var) if i == j else child)
                    terms.append(ASTNode(Mul, d_terms))
                result_node = ASTNode(Add, terms)
                _add_step_ast(result_node, "productRule_result", "The result of the Product Rule is:")
                return result_node

            if op == Pow:
                _add_step_ast(node, "powerRule_start", "Applying the Power Rule:")
                base, exp_node = args
                if not node_to_sympy(exp_node).has(var):
                    du = _compute_ast_derivative_recursive(base, var)
                    new_exp = parse_sympy_to_ast(node_to_sympy(exp_node) - 1)
                    result_node = ASTNode(Mul, [exp_node, ASTNode(Pow, [base, new_exp]), du])
                    _add_step_ast(result_node, "powerRule_result", "Result of the Power Rule:")
                    return result_node
            
            # chain rule
            def apply_chain_rule(rule_name, display_rule, result_func):
                u_node = args[0]
                _add_step_ast(node, f"{rule_name}Rule_start", f"Applying the {display_rule} Rule:")
                du_node = _compute_ast_derivative_recursive(u_node, var)
                result_node = result_func(u_node, du_node)
                _add_step_ast(result_node, f"{rule_name}Rule_result", f"The result for the function is:")
                return result_node

            if op == sin:
                return apply_chain_rule("sin", r"Sine", lambda u, du: ASTNode(Mul, [ASTNode(cos, [u]), du]))
            if op == cos:
                return apply_chain_rule("cos", r"Cosine", lambda u, du: ASTNode(Mul, [ASTNode(S.NegativeOne), ASTNode(sin, [u]), du]))
            if op == tan:
                return apply_chain_rule("tan", r"Tangent", lambda u, du: ASTNode(Mul, [ASTNode(Pow, [ASTNode(sec, [u]), ASTNode(S(2))]), du]))
            if op == sec:
                return apply_chain_rule("sec", r"Secant", lambda u, du: ASTNode(Mul, [ASTNode(sec, [u]), ASTNode(tan, [u]), du]))
            if op == csc:
                return apply_chain_rule("csc", r"Cosecant", lambda u, du: ASTNode(Mul, [ASTNode(S.NegativeOne), ASTNode(csc, [u]), ASTNode(cot, [u]), du]))
            if op == cot:
                return apply_chain_rule("cot", r"Cotangent", lambda u, du: ASTNode(Mul, [ASTNode(S.NegativeOne), ASTNode(Pow, [ASTNode(csc, [u]), ASTNode(S(2))]), du]))
            if op == exp:
                return apply_chain_rule("exp", r"Chain", lambda u, du: ASTNode(Mul, [ASTNode(exp, [u]), du]))
            if op == log:
                return apply_chain_rule("log", r"Chain", lambda u, du: ASTNode(Mul, [ASTNode(Pow, [u, ASTNode(S.NegativeOne)]), du]))

            sympy_segment = node_to_sympy(node)
            _add_step(steps, sympy_segment, "unknownRule_sympy_fallback", "No specific AST rule matched. Using a fallback.")
            derivative_segment = diff(sympy_segment, var)
            return parse_sympy_to_ast(derivative_segment)

        differentiated_ast = _compute_ast_derivative_recursive(ast_tree, variable_symbol)
        final_derivative = node_to_sympy(differentiated_ast)

    finally:
        end_time = time.perf_counter()
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    
    _add_step(steps, final_derivative, "final_derivative", "The final derivative is:")
    
    def count_nodes(node): return 1 + sum(count_nodes(child) for child in node.children)
    ast_node_count = count_nodes(ast_tree)

    return {
        "derivative_latex": latex(final_derivative),
        "steps": steps,
        "execution_time_ms": (end_time - start_time) * 1000,
        "peak_memory_bytes": peak_memory,
        "ast_node_count": ast_node_count,
    }
