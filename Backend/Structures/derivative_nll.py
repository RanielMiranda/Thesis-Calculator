import logging
import re
import time
from typing import List, Dict, Union, Any, Iterator, Iterable, Tuple, Optional
import tracemalloc

# --- Logger Setup ---
logger = logging.getLogger(__name__)

# =====================================================================
# 1. CUSTOM BASE CLASSES (REPLACING SYMPY LEAF NODES AND CONSTANTS)
# =====================================================================

class MySymbol:
    """Custom Symbol class to replace SympySymbol."""
    def __init__(self, name: str):
        self.name = name
    def __repr__(self) -> str:
        return self.name
    def __eq__(self, other):
        return isinstance(other, MySymbol) and self.name == other.name
    def __hash__(self) -> int:
        return hash(self.name)
    def has(self, var) -> bool:
        """Mimics the SymPy .has() method for leaf nodes."""
        return self == var

class MyNumber(float):
    """Base class for custom numbers."""
    def __repr__(self) -> str:
        return str(self)
    def has(self, var) -> bool:
        return False
    
class MyInteger(MyNumber):
    """Custom Integer class."""
    def __init__(self, value):
        super().__init__()
    def __repr__(self) -> str:
        return str(int(self))
    def __add__(self, other):
        return MyNumber(float(self) + float(other))

class MyFloat(MyNumber):
    """Custom Float class."""
    def __init__(self, value):
        super().__init__()

# Custom Constants (replacing S.Zero, S.One, S.NegativeOne)
MY_ZERO = MyInteger(0)
MY_ONE = MyInteger(1)
MY_NEG_ONE = MyInteger(-1)
MY_TWO = MyInteger(2)
MY_HALF = MyFloat(0.5)
MY_NEG_HALF = MyFloat(-0.5)

# --- Custom List Implementation (Nested Linked List Node) ---
# NLL structure: [Operator_Name, Operand1, Operand2, ...]
class CustomList:
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
        # Recursively print to show the NLL structure
        return f"CustomList({repr(self._items)})"

    def append(self, item: Any):
        self._items.append(item)

    def __add__(self, other):
        if isinstance(other, CustomList):
            return CustomList(self._items + other._items)
        elif isinstance(other, list):
            return CustomList(self._items + other)
        return NotImplemented

    def has(self, var: MySymbol) -> bool:
        """Recursive check for variable presence."""
        for item in self._items[1:]: # Skip the operator name
            if isinstance(item, CustomList):
                if item.has(var):
                    return True
            elif item == var:
                return True
        return False

# =====================================================================
# 2. TOKENIZER AND PARSER (STRING TO NLL CONVERSION)
# The parser now returns a CustomList (NLL) or a leaf node directly.
# =====================================================================

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
                raise ValueError(f"Unexpected character at position {position}: {self.expression_string[position]}")
        tokens.append(Token(TOKEN_EOF, ''))
        return tokens
    
    def next(self) -> Token:
        if self.current_token_index < len(self.tokens):
            token = self.tokens[self.current_token_index]
            self.current_token_index += 1
            return token
        return Token(TOKEN_EOF, '')

# The parser directly outputs the CustomList/NLL structure, no SymPy needed.
class Parser:
    def __init__(self, tokenizer: Tokenizer, custom_vars: Dict[str, MySymbol]):
        self.tokenizer = tokenizer
        self.custom_vars = custom_vars
        self.current_token = self.tokenizer.next()

    def _eat(self, token_type: str):
        if self.current_token.type == token_type:
            self.current_token = self.tokenizer.next()
        else:
            raise ValueError(f"Expected {token_type}, got {self.current_token.type} ('{self.current_token.value}')")

    def parse(self):
        result = self._expr()
        if self.current_token.type != TOKEN_EOF:
            raise ValueError("Unexpected token at end of expression")
        return result

    def _expr(self) -> Any:
        node = self._term()
        while self.current_token.type == TOKEN_OPERATOR and self.current_token.value in ('+', '-'):
            op = self.current_token.value
            self._eat(TOKEN_OPERATOR)
            right = self._term()
            
            # Binary operations: Add/Subtract
            if op == '+':
                node = CustomList(['Add', node, right])
            else: # Implicitly 'Subtract' -> Add(node, Mul(-1, right))
                right_negated = CustomList(['Mul', MY_NEG_ONE, right])
                node = CustomList(['Add', node, right_negated])
        return node

    def _term(self) -> Any:
        node = self._factor()
        while self.current_token.type == TOKEN_OPERATOR and self.current_token.value in ('*', '/'):
            op = self.current_token.value
            self._eat(TOKEN_OPERATOR)
            right = self._factor()
            
            # Binary operations: Mul/Divide
            if op == '*':
                node = CustomList(['Mul', node, right])
            else: # Implicitly 'Divide' -> Mul(node, Pow(right, -1))
                right_pow_neg_one = CustomList(['Pow', right, MY_NEG_ONE])
                node = CustomList(['Mul', node, right_pow_neg_one])
        return node

    def _factor(self) -> Any:
        node = self._atom()
        if self.current_token.type == TOKEN_OPERATOR and self.current_token.value == '^':
            self._eat(TOKEN_OPERATOR)
            right = self._factor()
            node = CustomList(['Pow', node, right])
        return node

    def _atom(self) -> Any:
        token = self.current_token
        if token.type == TOKEN_NUMBER:
            self._eat(TOKEN_NUMBER)
            value = token.value
            return MyFloat(float(value)) if '.' in value else MyInteger(int(value))
            
        elif token.type == TOKEN_SYMBOL:
            self._eat(TOKEN_SYMBOL)
            # Return custom symbol object
            return self.custom_vars.get(token.value, MySymbol(token.value))
            
        elif token.type == TOKEN_FUNCTION:
            func_name = token.value
            self._eat(TOKEN_FUNCTION)
            self._eat(TOKEN_LPAREN)
            arg = self._expr()
            self._eat(TOKEN_RPAREN)
            # Create a CustomList for the function call
            return CustomList([func_name, arg])
            
        elif token.type == TOKEN_LPAREN:
            self._eat(TOKEN_LPAREN)
            node = self._expr()
            self._eat(TOKEN_RPAREN)
            return node
            
        elif token.type == TOKEN_OPERATOR and token.value == '-':
            self._eat(TOKEN_OPERATOR)
            # Unary minus: -x -> Mul(-1, x)
            return CustomList(['Mul', MY_NEG_ONE, self._factor()])
            
        raise ValueError(f"Unexpected token: {token}")

# =====================================================================
# 3. CUSTOM LATEX GENERATOR (REPLACING SYMPY.LATEX)
# =====================================================================

def nll_to_latex(nll_expr: Any, parent_op: Optional[str] = None) -> str:
    """Recursively converts NLL structure into a LaTeX string with parentheses rules."""
    
    if isinstance(nll_expr, MySymbol):
        return nll_expr.name
    if isinstance(nll_expr, MyNumber):
        # Format floats neatly, fall back to simple string for integers
        if isinstance(nll_expr, MyFloat):
            return f"{nll_expr:.4g}"
        return str(int(nll_expr))
    
    if not isinstance(nll_expr, CustomList):
        # Should not happen if all leaf nodes are covered
        return str(nll_expr)

    op = nll_expr[0]
    args = nll_expr[1:]
    
    # Precedence lookup for implicit parentheses
    # Higher number means higher precedence (e.g., Pow > Mul > Add)
    precedence = {'Pow': 3, 'Mul': 2, 'Add': 1}
    current_precedence = precedence.get(op, 4) # Function calls have highest precedence

    def wrap_latex(sub_expr, child_op):
        """Adds parentheses if the child's operator has lower precedence."""
        child_precedence = precedence.get(child_op, 4)
        latex_str = nll_to_latex(sub_expr, op)
        
        # Check if the child is an operation with lower or equal precedence to the current operation
        if child_precedence <= current_precedence and child_op != op:
             return f"\\left({latex_str}\\right)"
        
        # Special case for negative numbers/symbols when part of a product
        if op == 'Mul' and isinstance(sub_expr, CustomList) and sub_expr[0] == 'Add':
            return f"\\left({latex_str}\\right)"
            
        return latex_str

    if op == 'Add':
        terms = []
        for i, arg in enumerate(args):
            # Check for subtraction (implicit negation)
            if isinstance(arg, CustomList) and arg[0] == 'Mul':
                # Check for Mul(-1, X)
                if arg[1] == MY_NEG_ONE:
                    terms.append(f"-{wrap_latex(arg[2], 'Mul')}")
                    continue
            
            # Simple addition
            term_latex = nll_to_latex(arg, op)
            if i > 0 and not term_latex.startswith('-'):
                terms.append(f"+{term_latex}")
            else:
                terms.append(term_latex)
        
        result = "".join(terms).replace('+-', '-')
        
    elif op == 'Mul':
        numerators = []
        denominators = []
        
        for arg in args:
            if isinstance(arg, CustomList) and arg[0] == 'Pow' and arg[2] == MY_NEG_ONE:
                # 1/x -> Pow(x, -1) -> denominator
                denominators.append(wrap_latex(arg[1], 'Pow'))
            else:
                numerators.append(wrap_latex(arg, op))
                
        if denominators:
            num_str = "".join(numerators) if numerators else "1"
            den_str = "".join(denominators)
            result = f"\\frac{{{num_str}}}{{{den_str}}}"
        else:
            result = "".join(numerators)
            
    elif op == 'Pow':
        base = wrap_latex(args[0], op)
        exponent = nll_to_latex(args[1], op)
        
        # Use braces for base if it's not a single symbol
        if isinstance(args[0], CustomList):
            base = f"\\left({nll_to_latex(args[0])}\\right)"
        
        result = f"{base}^{{{exponent}}}"

    # Standard Functions (sin, cos, log, etc.)
    elif op in ['sin', 'cos', 'tan', 'sec', 'csc', 'cot']:
        result = f"\\{op}\\left({nll_to_latex(args[0])}\\right)"
    elif op == 'log':
        result = f"\\ln\\left({nll_to_latex(args[0])}\\right)"
    elif op == 'exp':
        # e^u
        result = f"e^{{{nll_to_latex(args[0])}}}"
    elif op == 'sqrt':
        # sqrt(u)
        result = f"\\sqrt{{{nll_to_latex(args[0])}}}"
    else:
        # Fallback for unhandled operator strings
        result = f"\\text{{UnknownOp}}({', '.join(nll_to_latex(a) for a in args)})"

    # Wrap the entire expression in parentheses if current precedence is lower than parent's
    if parent_op and precedence.get(parent_op, 4) > current_precedence:
        return f"\\left({result}\\right)"
        
    return result

# =====================================================================
# 4. CORE DIFFERENTIATION LOGIC (NLL-BASED)
# =====================================================================

def _add_step(steps_list, expr_nll, rule_key, explanation, prefix="= "):
    """Helper to format differentiation steps for output using the custom LaTeX generator."""
    
    # Check if expr_nll is already a leaf node (like MY_ZERO)
    if not isinstance(expr_nll, (CustomList, MySymbol, MyNumber)):
        latex_str = str(expr_nll)
    else:
        latex_str = nll_to_latex(expr_nll)

    steps_list.append({
        "id": f"step_{len(steps_list)}_{rule_key}",
        "prefix": prefix,
        "parts": [{"latex": latex_str, "rule_id": rule_key, "explanation_key": rule_key}],
        "explanation_text": explanation
    })

def compute_derivative_nll(expression_str: str, variable_str: str):
    """
    Computes the symbolic derivative using the NLL representation.
    """
    tracemalloc.start()    
    start_time = time.perf_counter()
    steps = []
    
    # The variable we are differentiating with respect to, as a CUSTOM object
    variable_symbol = MySymbol(variable_str)
    
    differentiated_nll = None
    try:
        # Step 1: Parse the string directly into our NLL representation
        tokenizer = Tokenizer(expression_str)
        parser = Parser(tokenizer, {variable_str: variable_symbol})
        nll_tree = parser.parse()

        _add_step(steps, nll_tree, "initial_expression", "Differentiating with NLL:",
                    prefix=f"\\frac{{d}}{{d{variable_str}}}")
        
        def _compute_nll_derivative_recursive(nll, var):
            """Recursively applies differentiation rules to the NLL structure."""
            # --- Base Case: Leaf Nodes ---
            if not isinstance(nll, CustomList):
                if nll == var:
                    _add_step(steps, MY_ONE, "variableRule", f"The derivative of {variable_str} is 1.")
                    return MY_ONE
                if isinstance(nll, MyNumber) or not nll.has(var):
                    _add_step(steps, MY_ZERO, "constantRule", f"The derivative of a constant is 0.")
                    return MY_ZERO
                
                raise ValueError(f"Unhandled leaf node type or complex symbol: {nll}")
                
            op = nll[0]
            
            # --- Rule: Add (Sum Rule) ---
            if op == 'Add':
                _add_step(steps, nll, "sumRule_start", "Applying the Sum Rule:")
                # Differentiate each child
                args = CustomList([_compute_nll_derivative_recursive(nll[i], var) for i in range(1, len(nll))])
                result_nll = CustomList(['Add']) + args
                _add_step(steps, result_nll, "sumRule_result", "The sum of the derivatives is:")
                return result_nll
            
            # --- Rule: Mul (Product Rule) ---
            if op == 'Mul':
                _add_step(steps, nll, "productRule_start", "Applying the Product Rule.")
                terms = CustomList()
                
                # Product Rule (u * v * w)' = u'vw + uv'w + uvw'
                for i in range(1, len(nll)):
                    # Term to differentiate is nll[i]
                    d_term = _compute_nll_derivative_recursive(nll[i], var)
                    
                    # Create the product (d_term * remaining_terms)
                    d_product_args = CustomList([d_term])
                    for j in range(1, len(nll)):
                        if i != j:
                            d_product_args.append(nll[j])
                    
                    terms.append(CustomList(['Mul']) + d_product_args)
                
                result_nll = CustomList(['Add']) + terms
                _add_step(steps, result_nll, "productRule_result", "The result of the Product Rule is:")
                return result_nll

            # --- Rule: Pow (Simple Power Rule / Chain Rule for constant exponent) ---
            if op == 'Pow':
                base, exp_nll = nll[1], nll[2]
                
                # Simple Power Rule (exponent is a constant and doesn't contain the variable)
                if not exp_nll.has(var) and isinstance(exp_nll, MyNumber):
                    _add_step(steps, nll, "powerRule_start", "Applying the Power Rule (Constant Exponent):")
                    
                    # New exponent: exp - 1
                    # Note: We must check if exp_nll is an integer before using integer arithmetic
                    if isinstance(exp_nll, MyInteger):
                         new_exp = MyInteger(int(exp_nll) - 1)
                    else:
                         new_exp = MyFloat(float(exp_nll) - 1.0)
                         
                    # d/dx(u^n) = n * u^(n-1) * du/dx (Chain Rule for base u)
                    du = _compute_nll_derivative_recursive(base, var)
                    
                    new_pow = CustomList(['Pow', base, new_exp])
                    result_nll = CustomList(['Mul', exp_nll, new_pow, du])
                    
                    _add_step(steps, result_nll, "powerRule_result", "Result of the Power Rule:")
                    return result_nll
                
                # Complex Power Rule (Exponent is a function of the variable) is not supported 
                # without SymPy or complex rule implementations.
                raise ValueError("Complex Power Rule (u^v where v is not constant) is not supported by NLL engine.")
                
            def apply_chain_rule(rule_name, display_rule, result_func_nll):
                """Helper function for single-argument function derivatives (Chain Rule)."""
                u_nll = nll[1]
                _add_step(steps, nll, f"{rule_name}Rule_start", f"Applying the {display_rule} Rule (Chain Rule):")
                
                # Differentiate the inner function (u)
                du_nll = _compute_nll_derivative_recursive(u_nll, var)
                
                # Apply the derivative of the outer function times the derivative of the inner function
                result_nll = result_func_nll(u_nll, du_nll)
                _add_step(steps, result_nll, f"{rule_name}Rule_result", "The result for the function is:")
                return result_nll

            # --- Rule: sin ---
            if op == 'sin':
                return apply_chain_rule("sin", "Sine", 
                    lambda u, du: CustomList(['Mul', CustomList(['cos', u]), du]))
            # --- Rule: cos ---
            if op == 'cos':
                return apply_chain_rule("cos", "Cosine", 
                    lambda u, du: CustomList(['Mul', MY_NEG_ONE, CustomList(['sin', u]), du]))
            # --- Rule: tan (d/dx(tan(u)) = sec(u)^2 * du) ---
            if op == 'tan':
                sec_sq = CustomList(['Pow', CustomList(['sec', u]), MY_TWO])
                return apply_chain_rule("tan", "Tangent", 
                    lambda u, du: CustomList(['Mul', sec_sq, du]))
            # --- Rule: log (d/dx(log(u)) = u^(-1) * du) ---
            if op == 'log':
                u_neg_1 = CustomList(['Pow', u, MY_NEG_ONE])
                return apply_chain_rule("log", "Natural Log", 
                    lambda u, du: CustomList(['Mul', u_neg_1, du]))
            # --- Rule: exp (d/dx(exp(u)) = exp(u) * du) ---
            if op == 'exp':
                return apply_chain_rule("exp", "Exponential", 
                    lambda u, du: CustomList(['Mul', CustomList(['exp', u]), du]))
            # --- Rule: sqrt (d/dx(sqrt(u)) = 0.5 * u^(-0.5) * du) ---
            if op == 'sqrt':
                u_neg_half = CustomList(['Pow', u, MY_NEG_HALF])
                return apply_chain_rule("sqrt", "Square Root", 
                    lambda u, du: CustomList(['Mul', MY_HALF, u_neg_half, du]))

            # --- UNHANDLED / FALLBACK EXCEPTION ---
            raise ValueError(f"Operator '{op}' is not supported by the NLL differentiation ruleset.")

        differentiated_nll = _compute_nll_derivative_recursive(nll_tree, variable_symbol)
        
    except Exception as e:
        logger.error(f"Error during NLL differentiation: {e}")
        # Return the error message as the final result if something goes wrong
        final_derivative_latex = f"\\text{{Error: }} {str(e)}"
        differentiated_nll = MySymbol("ERROR") # Placeholder        
        
    else:
        # Final expression generated
        final_derivative_latex = nll_to_latex(differentiated_nll)

    end_time = time.perf_counter()
    execution_time_ms = (end_time - start_time) * 1000
    end_time = time.perf_counter()    
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()    
    _add_step(steps, differentiated_nll, "final_derivative", "The final derivative is:")

    # Return the dictionary of results
    return {
        "derivative_latex": final_derivative_latex,
        "steps": steps,
        "execution_time_ms": execution_time_ms,
        "peak_memory_bytes": peak_memory 
    }

