import logging
import re
import time
import tracemalloc
from typing import List, Dict, Optional
from functools import lru_cache

# --- SymPy Imports ---
# Import specific SymPy components to build the expression tree manually
from sympy import (
    Symbol as SympySymbol, Integer, Float, Add, Mul, Pow,
    sin, cos, tan, exp, log, sqrt, sec, csc, cot, S, latex, Derivative
)

# --- Logger Setup ---
logger = logging.getLogger(__name__)

# --- Caching for Performance ---
@lru_cache(maxsize=8192)
def _cached_latex(expr):
    """Caches the LaTeX representation of a SymPy expression."""
    try:
        return latex(expr)
    except Exception:
        return str(expr)

@lru_cache(maxsize=None)
def _diff_value_cached(expr, var):
    """Caches the result of a derivative computation fallback."""
    return Derivative(expr, var, evaluate=True).doit()

# --- Manual Tokenizer and Parser ---
# These classes are responsible for converting the input string into an expression tree.
# This entire process is now included in the performance measurement for this module.

TOKEN_NUMBER = 'NUMBER'
TOKEN_SYMBOL = 'SYMBOL'
TOKEN_FUNCTION = 'FUNCTION'
TOKEN_OPERATOR = 'OPERATOR'
TOKEN_LPAREN = 'LPAREN'
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
        (r'\s+', None),  # Skip whitespace
    ]

    def __init__(self, expression_string: str):
        self.expression_string = expression_string
        self.tokens = self._tokenize()
        self.current_token_index = 0

    def _tokenize(self) -> List[Token]:
        tokens = []
        position = 0
        while position < len(self.expression_string):
            match_found = False
            for pattern, token_type in self.TOKEN_SPECS:
                regex = re.compile(pattern)
                match = regex.match(self.expression_string, position)
                if match:
                    if token_type is not None:
                        tokens.append(Token(token_type, match.group(0)))
                    position = match.end(0)
                    match_found = True
                    break
            if not match_found:
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
            # Right-associativity for power
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
def _add_step(steps_list, latex_or_expr, rule_key, explanation, prefix="= "):
    """Utility to format and add a step to the explanation list."""
    expr_latex = latex_or_expr if isinstance(latex_or_expr, str) else _cached_latex(latex_or_expr)
    steps_list.append({
        "id": f"step_{len(steps_list)}_{rule_key}",
        "prefix": prefix,
        "parts": [{"latex": expr_latex, "rule_id": rule_key, "explanation_key": rule_key}],
        "explanation_text": explanation
    })

# --- Main AST Differentiator ---
def compute_derivative_ast(expression_str: str, variable_str: str):
    """
    Computes a derivative using AST traversal. The entire process, including
    parsing the expression string, is measured for performance.
    """
    steps = []
    local_cache = {}  # Memoization for derivative sub-problems

    # --- Performance Measurement Start ---
    tracemalloc.start()
    start_time = time.perf_counter()
    
    try:
        # 1. Parse the string into a SymPy expression tree
        tokenizer = Tokenizer(expression_str)
        variable_symbol = SympySymbol(variable_str)
        parser = Parser(tokenizer, {variable_str: variable_symbol})
        sympy_expr = parser.parse()

        # Initial step for the UI
        _add_step(steps, sympy_expr, "initial_expression", "Differentiating: ",
                  prefix=f"\\frac{{d}}{{d{_cached_latex(variable_symbol)}}}")

        # 2. Recursively compute the derivative
        def _rec(expr):
            key = (expr, variable_symbol)
            if key in local_cache:
                cached_value = local_cache[key]
                _add_step(steps, cached_value, "cached_subexpr", f"Using cached derivative for {_cached_latex(expr)}")
                return cached_value

            # Base Cases
            if not expr.has(variable_symbol):
                result = S.Zero
                _add_step(steps, result, "constantRule", "The derivative of a constant is 0.")
            elif expr == variable_symbol:
                result = S.One
                _add_step(steps, result, "variableRule", f"The derivative of {variable_str} with respect to itself is 1.")
            # Recursive Rules
            elif isinstance(expr, Add):
                _add_step(steps, expr, "sumRule_start", "Applying the Sum Rule: (f+g)' = f' + g'")
                d_terms = [_rec(arg) for arg in expr.args]
                result = Add(*d_terms)
                _add_step(steps, result, "sumRule_result", "The sum of the derivatives is:")
            
            elif isinstance(expr, Mul):
                const_terms = [a for a in expr.args if not a.has(variable_symbol)]
                non_const_terms = [a for a in expr.args if a.has(variable_symbol)]
                if const_terms and non_const_terms:
                    c = Mul(*const_terms)
                    f = Mul(*non_const_terms)
                    _add_step(steps, expr, "constantMultipleRule_start", "Applying the Constant Multiple Rule: (c*f)' = c*f'")
                    df = _rec(f)
                    result = Mul(c, df)
                    _add_step(steps, result, "constantMultipleRule_result", "The result of the Constant Multiple Rule is:")
                elif len(non_const_terms) == 2 and not const_terms:
                    u, v = non_const_terms
                    _add_step(steps, expr, "productRule_start", "Applying the Product Rule: (uv)' = u'v + uv'")
                    du, dv = _rec(u), _rec(v)
                    result = Add(Mul(du, v), Mul(u, dv))
                    _add_step(steps, result, "productRule_result", "The result of the Product Rule is:")
                else:
                    _add_step(steps, expr, "general_product_fallback", "Using a general product rule or fallback.")
                    result = _diff_value_cached(expr, variable_symbol)

            elif isinstance(expr, Pow):
                base, exponent = expr.args
                _add_step(steps, expr, "powerRule_start", "Applying the Power Rule or related rules.")
                if not exponent.has(variable_symbol):
                    dbase = _rec(base)
                    result = Mul(exponent, Pow(base, exponent - 1), dbase)
                    _add_step(steps, result, "powerRule_result", "Result of the Power Rule (u^n)' = n*u^(n-1)*u':")
                elif not base.has(variable_symbol):
                    dexp = _rec(exponent)
                    result = Mul(expr, log(base), dexp)
                    _add_step(steps, result, "expRule_result", "Result of the Exponential Rule (a^u)' = a^u * ln(a) * u':")
                else:
                    _add_step(steps, expr, "general_power_fallback", "Using a general power rule (logarithmic differentiation) fallback.")
                    result = _diff_value_cached(expr, variable_symbol)

            elif isinstance(expr, sin):
                u = expr.args[0]
                _add_step(steps, expr, "sinRule_start", "Applying the Chain Rule for sin(u): d/dx(sin(u)) = cos(u) * u'")
                du = _rec(u)
                result = Mul(cos(u), du)
                _add_step(steps, result, "sinRule_result", "The result for the sine function is:")
            elif isinstance(expr, cos):
                u = expr.args[0]
                _add_step(steps, expr, "cosRule_start", "Applying the Chain Rule for cos(u): d/dx(cos(u)) = -sin(u) * u'")
                du = _rec(u)
                result = Mul(S.NegativeOne, sin(u), du)
                _add_step(steps, result, "cosRule_result", "The result for the cosine function is:")
            elif isinstance(expr, tan):
                u = expr.args[0]
                _add_step(steps, expr, "tanRule_start", "Applying the Chain Rule for tan(u): d/dx(tan(u)) = sec^2(u) * u'")
                du = _rec(u)
                result = Mul(Pow(sec(u), 2), du)
                _add_step(steps, result, "tanRule_result", "The result for the tangent function is:")
            elif isinstance(expr, exp):
                u = expr.args[0]
                _add_step(steps, expr, "expRule_start", "Applying the Chain Rule for exp(u): d/dx(e^u) = e^u * u'")
                du = _rec(u)
                result = Mul(exp(u), du)
                _add_step(steps, result, "expRule_result", "The result for the exponential function is:")
            elif isinstance(expr, log):
                u = expr.args[0]
                _add_step(steps, expr, "logRule_start", "Applying the Chain Rule for log(u): d/dx(ln(u)) = (1/u) * u'")
                du = _rec(u)
                result = Mul(Pow(u, -1), du)
                _add_step(steps, result, "logRule_result", "The result for the logarithm function is:")
            elif isinstance(expr, sec):
                u = expr.args[0]
                _add_step(steps, expr, "secRule_start", "Applying the Chain Rule for sec(u): d/dx(sec(u)) = sec(u)tan(u) * u'")
                du = _rec(u)
                result = Mul(sec(u), tan(u), du)
                _add_step(steps, result, "secRule_result", "The result for the secant function is:")
            elif isinstance(expr, csc):
                u = expr.args[0]
                _add_step(steps, expr, "cscRule_start", "Applying the Chain Rule for csc(u): d/dx(csc(u)) = -csc(u)cot(u) * u'")
                du = _rec(u)
                result = Mul(S.NegativeOne, csc(u), cot(u), du)
                _add_step(steps, result, "cscRule_result", "The result for the cosecant function is:")
            elif isinstance(expr, cot):
                u = expr.args[0]
                _add_step(steps, expr, "cotRule_start", "Applying the Chain Rule for cot(u): d/dx(cot(u)) = -csc^2(u) * u'")
                du = _rec(u)
                result = Mul(S.NegativeOne, Pow(csc(u), 2), du)
                _add_step(steps, result, "cotRule_result", "The result for the cotangent function is:")
            
            else:
                _add_step(steps, expr, "unknownRule_sympy_fallback", "No specific rule matched. Using a fallback.")
                result = _diff_value_cached(expr, variable_symbol)

            local_cache[key] = result
            return result

        final_derivative = _rec(sympy_expr)

    finally:
        # --- Performance Measurement End ---
        end_time = time.perf_counter()
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    _add_step(steps, final_derivative, "final_derivative", "The final derivative is:")
    
    ast_node_count = len(list(sympy_expr.preorder_traversal())) if hasattr(sympy_expr, 'preorder_traversal') else -1
    
    return {
        "derivative_latex": _cached_latex(final_derivative),
        "steps": steps,
        "execution_time_ms": (end_time - start_time) * 1000,
        "peak_memory_bytes": peak_memory,
        "ast_node_count": ast_node_count,
    }

