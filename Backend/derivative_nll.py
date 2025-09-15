import logging
import re
import time
import tracemalloc
from typing import List, Dict, Union, Any, Iterator, Iterable

# --- SymPy Imports ---
# We use SymPy for its powerful symbolic objects (Add, Mul, sin, etc.) and its
# robust `diff` function for fallbacks. A pure manual implementation would
# require rewriting a significant portion of a symbolic math library.
from sympy import (
    Symbol as SympySymbol, Integer, Float, Add, Mul, Pow,
    sin, cos, tan, exp, log, sqrt, sec, csc, cot, S, latex, diff
)
from sympy.core.numbers import Number
from sympy.core.function import FunctionClass

# --- Logger Setup ---
logger = logging.getLogger(__name__)

# --- Custom List Implementation (mimicking native list behavior) ---
class CustomList:
    """
    A simple custom list class to avoid using the built-in Python list for
    the NLL data structure, as requested for study purposes.
    """
    def __init__(self, items: Iterable[Any] = None):
        self._items = []
        if items is not None:
            self._items.extend(items)

    def __getitem__(self, index: int) -> Any:
        return self._items[index]

    def __setitem__(self, index: int, value: Any):
        self._items[index] = value

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._items)
        
    def __repr__(self) -> str:
        return f"CustomList({repr(self._items)})"

    def append(self, item: Any):
        self._items.append(item)

    def __add__(self, other):
        """Allows for concatenation like native lists."""
        if isinstance(other, CustomList):
            return CustomList(self._items + other._items)
        elif isinstance(other, list):
            return CustomList(self._items + other)
        return NotImplemented

# --- Tokenizer and Parser (to convert string to an initial SymPy object) ---
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

# --- NLL Conversion and Computation Logic ---

# A map to convert string function names back to SymPy objects for display/fallback.
_sympy_func_map = {
    'Add': Add, 'Mul': Mul, 'Pow': Pow, 'sin': sin, 'cos': cos, 'tan': tan,
    'exp': exp, 'log': log, 'sqrt': sqrt, 'sec': sec, 'csc': csc, 'cot': cot
}

def parse_sympy_to_nll(expr):
    """Recursively converts a SymPy expression to a nested CustomList (NLL)."""
    if not hasattr(expr, 'args') or not expr.args:
        return expr  # Base case: a symbol or number
    
    # The function/operator name as a string is the first element of the list
    func_name = expr.func.__name__
    # Recursively convert all children and add them to the CustomList
    return CustomList([func_name] + [parse_sympy_to_nll(arg) for arg in expr.args])

def nll_to_sympy(nll_expr):
    """Recursively converts a nested CustomList (NLL) back to a SymPy expression."""
    if not isinstance(nll_expr, CustomList):
        return nll_expr # Base case: a symbol or number
    
    op_str = nll_expr[0]
    op_func = _sympy_func_map.get(op_str)
    
    if op_func is None:
        raise ValueError(f"Unknown function '{op_str}' in NLL representation.")
        
    # Recursively convert children and apply the SymPy function to them
    args = [nll_to_sympy(nll_expr[i]) for i in range(1, len(nll_expr))]
    return op_func(*args)

def _add_step(steps_list, expr, rule_key, explanation, prefix="= "):
    steps_list.append({
        "id": f"step_{len(steps_list)}_{rule_key}",
        "prefix": prefix,
        "parts": [{"latex": latex(expr), "rule_id": rule_key, "explanation_key": rule_key}],
        "explanation_text": explanation
    })

def compute_derivative_nll(expression_str: str, variable_str: str):
    steps = []
    
    def _add_step_nll(expr_nll, rule_key, explanation, prefix="= "):
        # Convert NLL to SymPy for consistent LaTeX display
        sympy_repr = nll_to_sympy(expr_nll)
        _add_step(steps, sympy_repr, rule_key, explanation, prefix)

    tracemalloc.start()
    start_time = time.perf_counter()

    try:
        # Step 1: Standard parsing to get a SymPy object
        tokenizer = Tokenizer(expression_str)
        variable_symbol = SympySymbol(variable_str)
        parser = Parser(tokenizer, {variable_str: variable_symbol})
        sympy_expr = parser.parse()
        
        # Step 2: Convert the SymPy object into our NLL representation
        nll_tree = parse_sympy_to_nll(sympy_expr)

        _add_step(steps, sympy_expr, "initial_expression", "Differentiating with NLL:",
                  prefix=f"\\frac{{d}}{{d{latex(variable_symbol)}}}")
        
        def _compute_nll_derivative_recursive(nll, var):
            # Base case: The NLL is not a CustomList, but a leaf node (Symbol, Number).
            if not isinstance(nll, CustomList):
                if nll == var:
                    _add_step(steps, S.One, "variableRule", f"The derivative of {variable_str} is 1.")
                    return S.One  # NLL for 1 is just the number 1
                if isinstance(nll, (Number, int, float)) or not nll.has(var):
                    _add_step(steps, S.Zero, "constantRule", f"The derivative of constant {latex(nll)} is 0.")
                    return S.Zero # NLL for 0 is just the number 0
                
                # Fallback for other leaf types (should be rare)
                derivative_segment = diff(nll, var)
                _add_step(steps, derivative_segment, "leaf_fallback", f"Fallback for leaf node {latex(nll)}.")
                return parse_sympy_to_nll(derivative_segment)
            
            op = nll[0]
            
            if op == 'Add':
                _add_step_nll(nll, "sumRule_start", "Applying the Sum Rule:")
                # Differentiate each child and wrap in a new 'Add' CustomList
                args = CustomList([_compute_nll_derivative_recursive(nll[i], var) for i in range(1, len(nll))])
                result_nll = CustomList(['Add']) + args
                _add_step_nll(result_nll, "sumRule_result", "The sum of the derivatives is:")
                return result_nll
            
            if op == 'Mul':
                _add_step_nll(nll, "productRule_start", "Applying the Product Rule.")
                terms = CustomList()
                for i in range(1, len(nll)):
                    d_terms = CustomList()
                    for j in range(1, len(nll)):
                        child = nll[j]
                        d_terms.append(_compute_nll_derivative_recursive(child, var) if i == j else child)
                    terms.append(CustomList(['Mul']) + d_terms)
                
                result_nll = CustomList(['Add']) + terms
                _add_step_nll(result_nll, "productRule_result", "The result of the Product Rule is:")
                return result_nll

            if op == 'Pow':
                _add_step_nll(nll, "powerRule_start", "Applying the Power Rule:")
                base, exp_nll = nll[1], nll[2]
                # Temporarily convert exponent to SymPy to check for the variable
                if not nll_to_sympy(exp_nll).has(var):
                    du = _compute_nll_derivative_recursive(base, var)
                    new_exp = CustomList(['Add', exp_nll, S.NegativeOne])
                    # Result: exp * base^(exp-1) * du
                    result_nll = CustomList(['Mul', exp_nll, CustomList(['Pow', base, new_exp]), du])
                    _add_step_nll(result_nll, "powerRule_result", "Result of the Power Rule:")
                    return result_nll
            
            def apply_chain_rule(rule_name, display_rule, result_func_nll):
                u_nll = nll[1]
                _add_step_nll(nll, f"{rule_name}Rule_start", f"Applying the {display_rule} Rule:")
                du_nll = _compute_nll_derivative_recursive(u_nll, var)
                result_nll = result_func_nll(u_nll, du_nll)
                _add_step_nll(result_nll, f"{rule_name}Rule_result", "The result for the function is:")
                return result_nll

            if op == 'sin':
                return apply_chain_rule("sin", "Sine", lambda u, du: CustomList(['Mul', CustomList(['cos', u]), du]))
            if op == 'cos':
                return apply_chain_rule("cos", "Cosine", lambda u, du: CustomList(['Mul', S.NegativeOne, CustomList(['sin', u]), du]))
            if op == 'tan':
                return apply_chain_rule("tan", "Tangent", lambda u, du: CustomList(['Mul', CustomList(['Pow', CustomList(['sec', u]), 2]), du]))
            if op == 'sec':
                return apply_chain_rule("sec", "Secant", lambda u, du: CustomList(['Mul', CustomList(['sec', u]), CustomList(['tan', u]), du]))
            if op == 'csc':
                return apply_chain_rule("csc", "Cosecant", lambda u, du: CustomList(['Mul', S.NegativeOne, CustomList(['csc', u]), CustomList(['cot', u]), du]))
            if op == 'cot':
                return apply_chain_rule("cot", "Cotangent", lambda u, du: CustomList(['Mul', S.NegativeOne, CustomList(['Pow', CustomList(['csc', u]), S(2)]), du]))
            if op == 'exp':
                return apply_chain_rule("exp", "Chain", lambda u, du: CustomList(['Mul', CustomList(['exp', u]), du]))
            if op == 'log':
                return apply_chain_rule("log", "Chain", lambda u, du: CustomList(['Mul', CustomList(['Pow', u, S.NegativeOne]), du]))

            # Fallback for unhandled functions/rules
            sympy_segment = nll_to_sympy(nll)
            _add_step(steps, sympy_segment, "unknownRule_sympy_fallback", "No specific NLL rule matched. Using a fallback.")
            derivative_segment = diff(sympy_segment, var)
            return parse_sympy_to_nll(derivative_segment)

        differentiated_nll = _compute_nll_derivative_recursive(nll_tree, variable_symbol)
        final_derivative = nll_to_sympy(differentiated_nll)

    finally:
        end_time = time.perf_counter()
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    
    _add_step(steps, final_derivative, "final_derivative", "The final derivative is:")
    
    # Counting nodes in NLL is counting CustomLists and non-list items
    def count_nodes_nll(nll):
        if not isinstance(nll, CustomList):
            return 1
        return 1 + sum(count_nodes_nll(child) for child in nll)
        
    nll_node_count = count_nodes_nll(nll_tree)

    return {
        "derivative_latex": latex(final_derivative),
        "steps": steps,
        "execution_time_ms": (end_time - start_time) * 1000,
        "peak_memory_bytes": peak_memory,
        "nll_node_count": nll_node_count,
    }
