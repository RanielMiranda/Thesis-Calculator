# derivative_nll.py
from sympy import Add, Mul, Pow, sin, cos, tan, exp, log, sec, diff, latex, S, Symbol # Import S for S.One, S.Zero etc.
import time
import tracemalloc
import logging

logger = logging.getLogger(__name__)

class NLLNode:
    def __init__(self, value, children=None):
        self.value = value
        self.children = children or []

def parse_expression_to_nll(expr):
    """
    Recursively parse a sympy expression into a Nested Linked List (NLL) structure.
    """
    if not hasattr(expr, 'args') or not expr.args:
        # Handle SymPy constants like S.One, S.Zero, S.NegativeOne as values
        if isinstance(expr, (S.One.__class__, S.Zero.__class__, S.NegativeOne.__class__)):
            return NLLNode(expr)
        # Handle Symbol objects
        if isinstance(expr, Symbol):
            return NLLNode(expr)
        # For other literals (e.g., Python int/float converted by sympify)
        # Or even direct Python int/float that might come from internal processing
        if isinstance(expr, (int, float)):
            # It's safer to sympify Python numbers to their SymPy equivalents
            return NLLNode(S(expr)) # Convert Python int/float to SymPy Number
        return NLLNode(expr) # Fallback for unexpected leaf types

    return NLLNode(expr.func, [parse_expression_to_nll(arg) for arg in expr.args])


def compute_nll_derivative_recursive(node, var):
    """
    Recursively compute the derivative of the NLL expression tree.
    (Renamed from compute_nll_derivative to align with internal recursive naming)
    """
    # Leaf node (variable or constant)
    if not node.children:
        if node.value == var:
            return NLLNode(S.One) # Use SymPy's S.One
        elif isinstance(node.value, (int, float, S.Number)): # Check for SymPy constants or numeric literals
            return NLLNode(S.Zero) # Use SymPy's S.Zero
        else: # Treat other Symbols or unhandled types as constants for now if not 'var'
            # If it's a SymPy Symbol that's not 'var', its derivative is 0
            if isinstance(node.value, Symbol):
                return NLLNode(S.Zero)
            # Fallback for truly unhandled constants, though ideally, parse_expression_to_nll should handle them.
            logger.warning(f"Unhandled non-variable leaf node type in derivative_recursive: {type(node.value)}. Treating as constant (derivative 0).")
            return NLLNode(S.Zero)

    # Addition: (u + v)' = u' + v'
    if node.value == Add:
        return NLLNode(Add, [compute_nll_derivative_recursive(child, var) for child in node.children])

    # Multiplication: (u * v)' = u'*v + u*v'
    if node.value == Mul:
        terms = []
        n = len(node.children)
        for i in range(n):
            d_terms = []
            for j, child in enumerate(node.children):
                d_terms.append(compute_nll_derivative_recursive(child, var) if i == j else child)
            terms.append(NLLNode(Mul, d_terms))
        return NLLNode(Add, terms)

    # Power: (u^v)' = v*u^(v-1)*u' if v is constant, else use general rule
    if node.value == Pow:
        base, exp_node = node.children # Renamed exp to exp_node to avoid conflict with exp function
        
        # Check if exponent is a constant (no children, and its value is a numeric type or SymPy constant)
        # Use S.is_number to check if it's a constant SymPy number
        if not exp_node.children and exp_node.value.is_number: # Check if it's a constant number
            # This is d(u^n)/dx = n * u^(n-1) * u'
            # Ensure operations like (exp.value - 1) result in SymPy numbers
            return NLLNode(Mul, [
                exp_node, # n (already an NLLNode of a SymPy Number)
                NLLNode(Pow, [base, NLLNode(exp_node.value - S.One)]), # u^(n-1)
                compute_nll_derivative_recursive(base, var) # u'
            ])
        else:
            # General case: d/dx u^v = u^v * (v'*log(u) + v*u'/u)
            return NLLNode(Mul, [
                NLLNode(Pow, [base, exp_node]), # u^v
                NLLNode(Add, [
                    NLLNode(Mul, [compute_nll_derivative_recursive(exp_node, var), NLLNode(log, [base])]), # v'*log(u)
                    NLLNode(Mul, [exp_node, compute_nll_derivative_recursive(base, var), NLLNode(Pow, [base, NLLNode(S.NegativeOne)])]) # v*u'/u
                ])
            ])

    # Trigonometric and exponential/logarithmic functions
    if node.value == sin:
        u = node.children[0]
        return NLLNode(Mul, [NLLNode(cos, [u]), compute_nll_derivative_recursive(u, var)])
    if node.value == cos:
        u = node.children[0]
        return NLLNode(Mul, [NLLNode(S.NegativeOne), NLLNode(sin, [u]), compute_nll_derivative_recursive(u, var)])
    if node.value == tan:
        u = node.children[0]
        return NLLNode(Mul, [NLLNode(Pow, [NLLNode(sec, [u]), NLLNode(S.Two)]), compute_nll_derivative_recursive(u, var)]) # S.Two for clarity
    if node.value == exp:
        u = node.children[0]
        return NLLNode(Mul, [NLLNode(exp, [u]), compute_nll_derivative_recursive(u, var)])
    if node.value == log:
        u = node.children[0]
        return NLLNode(Mul, [NLLNode(Pow, [u, NLLNode(S.NegativeOne)]), compute_nll_derivative_recursive(u, var)])

    # Fallback: use SymPy's diff for unsupported nodes
    # This converts the NLL sub-tree back to SymPy, differentiates, then converts back to NLL
    logger.warning(f"No specific NLL rule matched for function '{node.value}'. Using SymPy's diff as fallback.")
    sympy_expr = node_to_sympy(node)
    differentiated_sympy_expr = diff(sympy_expr, var)
    return parse_expression_to_nll(differentiated_sympy_expr)

def node_to_sympy(node):
    """
    Convert an NLLNode back to a sympy expression.
    """
    if not node.children:
        # Ensure that values like S.One, S.Zero are returned directly,
        # and Python ints/floats are converted to SymPy Numbers if they somehow bypassed sympify
        if isinstance(node.value, (int, float)):
            return S(node.value)
        return node.value
    return node.value(*[node_to_sympy(child) for child in node.children])


def compute_derivative_nll(sympy_expr, variable_symbol):
    """
    Main function to compute the derivative using the NLL structure.
    Mimics the structure of compute_derivative_ast and compute_derivative_dag.
    """
    steps = []

    # Add initial step (same as other derivative files)
    steps.append({
        "id": "step_0_initial_expression",
        "prefix": f"\\frac{{d}}{{d{latex(variable_symbol)}}}",
        "parts": [{"latex": latex(sympy_expr), "rule_id": "initial_expression", "explanation_key": "initial_expression"}],
        "explanation_text": f"Differentiating: "
    })

    tracemalloc.start()
    start_time = time.perf_counter()

    # Parse the SymPy expression to NLL
    nll_expression_tree = parse_expression_to_nll(sympy_expr)

    # Compute the derivative using the NLL structure
    nll_differentiated_tree = compute_nll_derivative_recursive(nll_expression_tree, variable_symbol)

    # Convert the differentiated NLL tree back to a SymPy expression
    differentiated_expr = node_to_sympy(nll_differentiated_tree)

    end_time = time.perf_counter()
    current_memory, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    execution_time_ms = (end_time - start_time) * 1000

    final_latex_derivative = latex(differentiated_expr)

    # Add the final derivative step
    steps.append({
        "id": f"step_{len(steps)}_final_derivative",
        "prefix": "= ",
        "parts": [{"latex": final_latex_derivative, "rule_id": "final_derivative", "explanation_key": "final_derivative"}],
        "explanation_text": f"The final derivative is: "
    })

    # Node count for NLL is the total number of nodes in the NLL tree
    # This requires a traversal of the NLL tree
    def count_nll_nodes(node):
        count = 1
        for child in node.children:
            count += count_nll_nodes(child)
        return count
    
    nll_node_count_val = count_nll_nodes(nll_expression_tree)


    return {
        "derivative_latex": final_latex_derivative,
        "raw_sympy_derivative": differentiated_expr,
        "steps": steps,
        "execution_time_ms": execution_time_ms,
        "peak_memory_bytes": peak_memory,
        "ast_node_count": nll_node_count_val, # Use this key for NLL node count as well
        "data_structure_used": "NLL"
    }