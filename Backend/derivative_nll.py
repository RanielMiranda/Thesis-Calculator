from sympy import Add, Mul, Pow, sin, cos, tan, exp, log, sec, diff, latex, S, Symbol, simplify
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
        if isinstance(expr, (int, float)):
            return NLLNode(S(expr)) # Convert Python int/float to SymPy Number
        return NLLNode(expr) # Fallback for unexpected leaf types

    return NLLNode(expr.func, [parse_expression_to_nll(arg) for arg in expr.args])

def compute_nll_derivative_recursive(node, var, steps, parent_rule=None):
    """
    Recursively compute the derivative of the NLL expression tree,
    adding step-by-step explanations to the steps list.
    """
    def add_step(rule_key, explanation, latex_expr, explanation_key=None):
        steps.append({
            "id": f"step_{len(steps)}_{rule_key}",
            "prefix": "= ",
            "parts": [{
                "latex": latex(latex_expr) if not isinstance(latex_expr, str) else latex_expr,
                "rule_id": rule_key,
                "explanation_key": explanation_key or rule_key
            }],
            "explanation_text": explanation
        })

    # Leaf node (variable or constant)
    if not node.children:
        if node.value == var:
            add_step("variableRule", f"The derivative of {latex(var)} with respect to itself is 1.", S.One)
            return NLLNode(S.One)
        elif isinstance(node.value, (int, float, S.Number)):
            add_step("constantRule", f"The derivative of constant '{latex(node.value)}' is 0.", S.Zero)
            return NLLNode(S.Zero)
        elif isinstance(node.value, Symbol):
            add_step("constantRule", f"The derivative of constant '{latex(node.value)}' is 0.", S.Zero)
            return NLLNode(S.Zero)
        else:
            add_step("constantRule", f"Treating '{latex(node.value)}' as constant, derivative is 0.", S.Zero)
            return NLLNode(S.Zero)

    # Addition: (u + v)' = u' + v'
    if node.value == Add:
        add_step("sumRule_start", "Applying Sum Rule:", node_to_sympy(node))
        d_children = [compute_nll_derivative_recursive(child, var, steps, "sumRule_start") for child in node.children]
        result = NLLNode(Add, d_children)
        add_step("sumRule_result", "Sum of derivatives:", node_to_sympy(result))
        return result

    # Multiplication: (u * v)' = u'*v + u*v'
    if node.value == Mul:
        add_step("productRule_start", "Applying Product Rule:", node_to_sympy(node))
        terms = []
        n = len(node.children)
        for i in range(n):
            d_terms = []
            for j, child in enumerate(node.children):
                d_terms.append(compute_nll_derivative_recursive(child, var, steps, "productRule_start") if i == j else child)
            terms.append(NLLNode(Mul, d_terms))
        result = NLLNode(Add, terms)
        add_step("productRule_result", "Sum of product rule terms:", node_to_sympy(result))
        return result

    # Power: (u^v)' = v*u^(v-1)*u' if v is constant, else use general rule
    if node.value == Pow:
        base, exp_node = node.children
        if not exp_node.children and getattr(exp_node.value, "is_number", False):
            add_step("powerRule_start", "Applying Power Rule:", node_to_sympy(node))
            dbase = compute_nll_derivative_recursive(base, var, steps, "powerRule_start")
            result = NLLNode(Mul, [
                exp_node,
                NLLNode(Pow, [base, NLLNode(exp_node.value - S.One)]),
                dbase
            ])
            add_step("powerRule_u_n_result", "Result of Power Rule:", node_to_sympy(result))
            return result
        else:
            add_step("powerRule_general_start", "General Power Rule (logarithmic differentiation):", node_to_sympy(node))
            sympy_expr = node_to_sympy(node)
            sympy_diff = diff(sympy_expr, var)
            add_step("powerRule_general_sympy_fallback", "SymPy's direct computation for general power rule.", sympy_diff)
            return parse_expression_to_nll(sympy_diff)

    # Trigonometric and exponential/logarithmic functions
    if node.value == sin:
        u = node.children[0]
        add_step("sinRule_start", "Applying Sine Rule:", node_to_sympy(node))
        du = compute_nll_derivative_recursive(u, var, steps, "sinRule_start")
        result = NLLNode(Mul, [NLLNode(cos, [u]), du])
        add_step("sinRule_result", "Result of Sine Rule:", node_to_sympy(result))
        return result
    if node.value == cos:
        u = node.children[0]
        add_step("cosRule_start", "Applying Cosine Rule:", node_to_sympy(node))
        du = compute_nll_derivative_recursive(u, var, steps, "cosRule_start")
        result = NLLNode(Mul, [NLLNode(S.NegativeOne), NLLNode(sin, [u]), du])
        add_step("cosRule_result", "Result of Cosine Rule:", node_to_sympy(result))
        return result
    if node.value == tan:
        u = node.children[0]
        add_step("tanRule_start", "Applying Tangent Rule:", node_to_sympy(node))
        du = compute_nll_derivative_recursive(u, var, steps, "tanRule_start")
        result = NLLNode(Mul, [NLLNode(Pow, [NLLNode(sec, [u]), NLLNode(S(2))]), du])
        add_step("tanRule_result", "Result of Tangent Rule:", node_to_sympy(result))
        return result
    if node.value == exp:
        u = node.children[0]
        add_step("expRule_start", "Applying Exponential Rule:", node_to_sympy(node))
        du = compute_nll_derivative_recursive(u, var, steps, "expRule_start")
        result = NLLNode(Mul, [NLLNode(exp, [u]), du])
        add_step("expRule_result", "Result of Exponential Rule:", node_to_sympy(result))
        return result
    if node.value == log:
        u = node.children[0]
        add_step("logRule_start", "Applying Logarithmic Rule:", node_to_sympy(node))
        du = compute_nll_derivative_recursive(u, var, steps, "logRule_start")
        result = NLLNode(Mul, [NLLNode(Pow, [u, NLLNode(S.NegativeOne)]), du])
        add_step("logRule_result", "Result of Logarithmic Rule:", node_to_sympy(result))
        return result

    # Fallback: use SymPy's diff for unsupported nodes
    logger.warning(f"No specific NLL rule matched for function '{node.value}'. Using SymPy's diff as fallback.")
    sympy_expr = node_to_sympy(node)
    sympy_diff = diff(sympy_expr, var)
    add_step("unknownRule", f"No specific NLL rule matched for: {latex(sympy_expr)}. Using SymPy's diff as fallback.", sympy_diff)
    return parse_expression_to_nll(sympy_diff)

def node_to_sympy(node):
    """
    Convert an NLLNode back to a sympy expression.
    """
    if not node.children:
        if isinstance(node.value, (int, float)):
            return S(node.value)
        return node.value
    return node.value(*[node_to_sympy(child) for child in node.children])

def compute_derivative_nll(sympy_expr, variable_symbol):
    """
    Main function to compute the derivative using the NLL structure.
    Now includes step-by-step explanations.
    """
    steps = []

    # Add initial step
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

    # Compute the derivative using the NLL structure (with steps)
    nll_differentiated_tree = compute_nll_derivative_recursive(nll_expression_tree, variable_symbol, steps)

    # Convert the differentiated NLL tree back to a SymPy expression
    differentiated_expr = node_to_sympy(nll_differentiated_tree)

    # --- Simplify the result so NLL matches AST/DAG ---
    differentiated_expr = simplify(differentiated_expr)

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
        "ast_node_count": nll_node_count_val,
        "data_structure_used": "NLL"
    }