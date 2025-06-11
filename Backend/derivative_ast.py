# derivative_ast.py
from sympy import symbols, sympify, latex, Add, Mul, Pow, sin, cos, exp, log, Integer, Symbol, Derivative, Function
from sympy.core.function import UndefinedFunction
from sympy import S # Import for simplification, e.g., S.Zero, S.One
import time
import tracemalloc
import logging

logger = logging.getLogger(__name__)

# --- Helper for Step Formatting ---
def _add_step(steps_list, current_expr, rule_key, explanation, prefix="= ", is_intermediate=False):
    try:
        expr_latex = latex(current_expr)
    except Exception as e:
        logger.warning(f"Could not convert expression to LaTeX for step '{rule_key}': {current_expr}, Error: {e}")
        expr_latex = str(current_expr) # Fallback to string representation

    steps_list.append({
        "id": f"step_{len(steps_list)}_{rule_key}",
        "prefix": prefix,
        "parts": [
            {"latex": expr_latex, "rule_id": rule_key, "explanation_key": rule_key}
        ],
        "explanation_text": explanation 
    })

def _differentiate_recursive(expression, variable, steps_list):
    # Rule: Derivative of a constant is 0
    if not expression.has(variable):
        _add_step(steps_list, S.Zero, "constantRule", f"Derivative of constant '{latex(expression)}' is 0.")
        return S.Zero

    # Rule: Derivative of the variable itself is 1
    if expression == variable:
        _add_step(steps_list, S.One, "variableRule", f"Derivative of '{latex(variable)}' with respect to itself is 1.")
        return S.One

    # --- Sum Rule: d(u+v)/dx = du/dx + dv/dx ---
    if isinstance(expression, Add):
        _add_step(steps_list, expression, "sumRule_start", f"Applying Sum Rule: ")
        d_terms = []
        for arg in expression.args:
            d_term = _differentiate_recursive(arg, variable, steps_list)
            d_terms.append(d_term)
        result = Add(*d_terms).simplify() # Simplify the sum for better presentation
        _add_step(steps_list, result, "sumRule_result", f"Sum of derivatives: {latex(result)}")
        return result

    # --- Product Rule: d(u*v)/dx = u*(dv/dx) + v*(du/dx) ---
    if isinstance(expression, Mul):
        # Separate constant and variable parts
        const_terms = [arg for arg in expression.args if not arg.has(variable)]
        non_const_terms = [arg for arg in expression.args if arg.has(variable)]

        # Constant Multiple Rule: d(c*f(x))/dx = c * d(f(x))/dx
        if const_terms and non_const_terms:
            c = Mul(*const_terms)
            f = Mul(*non_const_terms)
            _add_step(steps_list, expression, "constantMultipleRule_start", f"Applying Constant Multiple Rule for {latex(c)} * {latex(f)}")
            df_dx = _differentiate_recursive(f, variable, steps_list)
            result = Mul(c, df_dx).simplify() # Simplify the product for better presentation
            _add_step(steps_list, result, "constantMultipleRule_result", f"Result: {latex(c)} * ({latex(df_dx)}): ")
            return result
        # Standard Product Rule for two variable terms
        elif len(non_const_terms) == 2 and not const_terms:
            u, v = non_const_terms[0], non_const_terms[1]
            _add_step(steps_list, expression, "productRule_start", f"Applying Product Rule to: {latex(u)} * {latex(v)}")
            
            _add_step(steps_list, Derivative(v, variable), "productRule_dv_dx_expr", f"Derivative of second term: $\\frac{{d}}{{d{latex(variable)}}}({latex(v)})$")
            dv_dx = _differentiate_recursive(v, variable, steps_list)
            
            _add_step(steps_list, Derivative(u, variable), "productRule_du_dx_expr", f"Derivative of first term: $\\frac{{d}}{{d{latex(variable)}}}({latex(u)})$")
            du_dx = _differentiate_recursive(u, variable, steps_list)
            
            term1 = Mul(u, dv_dx).simplify()
            term2 = Mul(v, du_dx).simplify()
            result = Add(term1, term2).simplify()
            explanation_text = f"Product Rule result: ({latex(u)})({latex(dv_dx)}) + ({latex(v)})({latex(du_dx)}) = {latex(result)}"
            _add_step(steps_list, result, "productRule_result", explanation_text)
            return result
        # Product rule for more than two variable terms (fallback to SymPy for simplicity)
        elif len(non_const_terms) > 2 and not const_terms:
            _add_step(steps_list, expression, "productRule_complex", f"Applying Product Rule to multiple terms like {latex(expression)}.")
            temp_result = Derivative(expression, variable, evaluate=True).simplify()
            _add_step(steps_list, temp_result, "productRule_sympy_fallback", f"Using SymPy's diff for complex product step. Result: {latex(temp_result)}")
            return temp_result
        else: # Only constant terms or no terms (shouldn't happen with SymPy Mul)
            _add_step(steps_list, S.Zero, "constantRule", f"Derivative of constant product '{latex(expression)}' is 0.")
            return S.Zero

    # --- Quotient Rule: d(u/v)/dx = (v*(du/dx) - u*(dv/dx)) / v^2 ---
    # SymPy represents u/v as u * v**(-1)
    # Check if expression is Mul and contains a Pow with negative exponent
    if isinstance(expression, Mul) and any(isinstance(arg, Pow) and arg.args[1].is_negative for arg in expression.args):
        # Attempt to parse as u/v
        numerator_args = [arg for arg in expression.args if not (isinstance(arg, Pow) and arg.args[1].is_negative)]
        denominator_args = [arg.args[0] for arg in expression.args if isinstance(arg, Pow) and arg.args[1].is_negative]

        if len(denominator_args) == 1: # Simple u/v case
            u = Mul(*numerator_args).simplify()
            v = denominator_args[0]
            
            # Reconstruct the original quotient form for the step display
            original_quotient_latex = f"\\frac{{{latex(u)}}}{{{latex(v)}}}"
            _add_step(steps_list, original_quotient_latex, "quotientRule_start", f"Applying Quotient Rule to: {original_quotient_latex}")

            _add_step(steps_list, Derivative(u, variable), "quotientRule_du_dx_expr", f"Derivative of numerator: $\\frac{{d}}{{d{latex(variable)}}}({latex(u)})$")
            du_dx = _differentiate_recursive(u, variable, steps_list)
            
            _add_step(steps_list, Derivative(v, variable), "quotientRule_dv_dx_expr", f"Derivative of denominator: $\\frac{{d}}{{d{latex(variable)}}}({latex(v)})$")
            dv_dx = _differentiate_recursive(v, variable, steps_list)
            
            # (v * du/dx)
            term1 = Mul(v, du_dx).simplify()
            # (u * dv/dx)
            term2 = Mul(u, dv_dx).simplify()
            
            # Numerator of the quotient rule: (v * du/dx - u * dv/dx)
            quotient_numerator = Add(term1, Mul(S.NegativeOne, term2)).simplify()
            # Denominator of the quotient rule: v^2
            quotient_denominator = Pow(v, 2).simplify()
            
            # Combine into the final quotient expression
            result = Mul(quotient_numerator, Pow(quotient_denominator, -1)).simplify()

            explanation_text = f"Quotient Rule result: $\\frac{{{latex(v)} \\cdot ({latex(du_dx)}) - {latex(u)} \\cdot ({latex(dv_dx)})}}{{{{latex(v)}}^2}} = {latex(result)}$"
            return result
        # For more complex rational expressions, let SymPy handle it
        else:
            _add_step(steps_list, expression, "quotientRule_complex_fallback", f"Complex quotient expression {latex(expression)} detected. Using SymPy's diff.")
            temp_result = Derivative(expression, variable, evaluate=True).simplify()
            _add_step(steps_list, temp_result, "quotientRule_sympy_fallback", f"Fallback SymPy result: {latex(temp_result)}")
            return temp_result
            
    # --- Power Rule: d(u^n)/dx = n*u^(n-1)*du/dx ---
    if isinstance(expression, Pow):
        base, exponent = expression.args[0], expression.args[1]
        _add_step(steps_list, expression, "powerRule_start", f"Applying Power Rule to: ")

        if not exponent.has(variable): # u^n where n is constant
            n = exponent
            _add_step(steps_list, Derivative(base, variable), "chainRule_for_power_base", f"Chain rule: need derivative of base: ")
            dbase_dx = _differentiate_recursive(base, variable, steps_list)
            
            term_n = n
            term_base_pow = Pow(base, n - 1).simplify()
            
            result = Mul(term_n, term_base_pow, dbase_dx).simplify()
            _add_step(steps_list, result, "powerRule_u_n_result", f"Power Rule result for: ")
            return result
        elif not base.has(variable) and exponent.has(variable): # a^u where a is constant
            a = base
            _add_step(steps_list, expression, "expRule_a_u_start", f"Applying Exponential Rule for: ")
            _add_step(steps_list, Derivative(exponent, variable), "chainRule_for_exp_a_u_exponent", f"Chain rule: need derivative of exponent: ")
            du_dx = _differentiate_recursive(exponent, variable, steps_list)
            result = Mul(expression, log(a), du_dx).simplify() 
            _add_step(steps_list, result, "expRule_a_u_result", f"Result for : ")
            return result
        else: # f(x)^g(x) - general power rule (logarithmic differentiation)
            _add_step(steps_list, expression, "powerRule_general_start", f"General Power Rule for functions raised to functions: ")
            # SymPy's diff handles this as d/dx(e^(g(x)log(f(x))))
            temp_result = Derivative(expression, variable, evaluate=True).simplify()
            _add_step(steps_list, temp_result, "powerRule_general_sympy_fallback", f"Using SymPy's diff for general power rule $f(x)^{{g(x)}}$. Result: ")
            return temp_result

    # --- Function Calls (Chain Rule implicitly) ---
    if isinstance(expression, sin):
        u = expression.args[0]
        _add_step(steps_list, expression, "sinRule_start", f"Applying Sine Rule: ")
        _add_step(steps_list, Derivative(u, variable), "chainRule_for_sin_arg", f"Chain rule: need derivative of argument: ")
        du_dx = _differentiate_recursive(u, variable, steps_list)
        result = Mul(cos(u), du_dx).simplify()
        _add_step(steps_list, result, "sinRule_result", f"Sine Rule result: ")
        return result

    if isinstance(expression, cos):
        u = expression.args[0]
        _add_step(steps_list, expression, "cosRule_start", f"Applying Cosine Rule: ")
        _add_step(steps_list, Derivative(u, variable), "chainRule_for_cos_arg", f"Chain rule: need derivative of argument: ")
        du_dx = _differentiate_recursive(u, variable, steps_list)
        result = Mul(S.NegativeOne, sin(u), du_dx).simplify() 
        _add_step(steps_list, result, "cosRule_result", f"Cosine Rule result: ")
        return result

    if isinstance(expression, exp):
        u = expression.args[0]
        _add_step(steps_list, expression, "expRule_start", f"Applying Exponential Rule to: ")
        _add_step(steps_list, Derivative(u, variable), "chainRule_for_exp_arg", f"Chain rule: need derivative of argument: ")
        du_dx = _differentiate_recursive(u, variable, steps_list)
        result = Mul(exp(u), du_dx).simplify() 
        _add_step(steps_list, result, "expRule_result", f"Exponential Rule $e^u$ result: ")
        return result
    
    if isinstance(expression, log): # Natural logarithm (base e)
        u = expression.args[0]
        _add_step(steps_list, expression, "logRule_start", f"Applying Natural Logarithmic Rule to: ")
        _add_step(steps_list, Derivative(u, variable), "chainRule_for_log_arg", f"Chain rule: need derivative of argument: ")
        du_dx = _differentiate_recursive(u, variable, steps_list)
        result = Mul(Pow(u, -1), du_dx).simplify() 
        _add_step(steps_list, result, "logRule_result", f"Natural Logarithmic Rule result: ")
        return result
    
    # Generic function (e.g., f(x), g(x) not defined in SymPy)
    if isinstance(expression, Function) and not isinstance(expression, (sin,cos,exp,log,Pow,Add,Mul,Integer,Symbol,Derivative,UndefinedFunction)):
        _add_step(steps_list, expression, "generalFunctionRule_start", f"General function derivative for ")
        temp_result = Derivative(expression, variable, evaluate=True).simplify() 
        _add_step(steps_list, temp_result, "generalFunctionRule_result", f"Result for ${latex(expression)}$: ${latex(temp_result)}$")
        return temp_result

    # Fallback for expressions not explicitly handled by rules
    _add_step(steps_list, expression, "unknownRule", f"No specific AST rule matched for: {latex(expression)}. Using SymPy's diff as fallback.")
    temp_result = Derivative(expression, variable, evaluate=True).simplify()
    _add_step(steps_list, temp_result, "unknownRule_sympy_fallback", f"Fallback SymPy result: ")
    return temp_result


def compute_derivative_ast(sympy_expr, variable_symbol):
    steps = []  

    _add_step(steps, sympy_expr, "initial_expression", 
              f"Differentiating with respect to {latex(variable_symbol)}:", 
              prefix=f"\\frac{{d}}{{d{latex(variable_symbol)}}}")

    tracemalloc.start()
    start_time = time.perf_counter()

    differentiated_expr = _differentiate_recursive(sympy_expr, variable_symbol, steps) 
    
    end_time = time.perf_counter()
    current_memory, peak_memory = tracemalloc.get_traced_memory()

    execution_time_ms = (end_time - start_time) * 1000

    # Ensure the final derivative is added as the very last step if not already
    # Check if the last step's expression matches the final derivative
    if not steps or latex(steps[-1]['parts'][0]['latex']) != latex(differentiated_expr):
        _add_step(steps, differentiated_expr, "final_derivative", 
                    f"The final derivative is: ")
    else: # Update the last step's rule and explanation if it already contains the final result
        steps[-1]['rule_id'] = "final_derivative"
        steps[-1]['explanation_text'] = f"The final derivative is: "

    
    final_latex_derivative = latex(differentiated_expr)
    raw_sympy_derivative = differentiated_expr 

    ast_node_count_val = 0
    if hasattr(sympy_expr, 'preorder_traversal'):
        try:
            ast_node_count_val = len(list(sympy_expr.preorder_traversal()))
        except Exception as e:
            logger.error(f"Error calling preorder_traversal on {sympy_expr}: {e}")
            ast_node_count_val = -1 # Indicate error
    else:
        logger.warning(f"sympy_expr does NOT have 'preorder_traversal'. Type: {type(sympy_expr)}")
        ast_node_count_val = -2 # Indicate missing attribute

    return {
        "derivative_latex": final_latex_derivative,
        "raw_sympy_derivative": raw_sympy_derivative, 
        "steps": steps,
        "execution_time_ms": execution_time_ms,
        "peak_memory_bytes": peak_memory,
        "ast_node_count": ast_node_count_val 
    }