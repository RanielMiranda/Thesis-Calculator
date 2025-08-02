# derivative_dag.py
from sympy import symbols, sympify, latex, Add, Mul, Pow, sin, cos, exp, log, Integer, Symbol, Derivative, Function, sqrt
from sympy import tan, sec, csc, cot # Import new trigonometric functions
from sympy.core.function import UndefinedFunction
from sympy import S # Import for simplification, e.g., S.Zero, S.One
import time
import tracemalloc
import logging

logger = logging.getLogger(__name__)

# Cache for storing results of differentiated subexpressions
# This helps in simulating DAG behavior by avoiding redundant computations
# Key: (expression, variable), Value: differentiated_expression
_differentiation_cache = {}
# _step_trace = {} # Not used in this version for simpler DAG step visualization

# --- Helper for Step Formatting ---
def _add_step(steps_list, rule_key, explanation, prefix="", parts=None):
    """
    Adds a step to the list of derivative steps.
    :param steps_list: The list to append the step to.
    :param rule_key: A unique key identifying the rule applied.
    :param explanation: A human-readable explanation for the step.
    :param prefix: An optional LaTeX string prefix for the step (e.g., d/dx).
    :param parts: An optional list of dictionaries, where each dict has 'latex' and 'explanation_key'.
                  The 'latex' value MUST be a string (LaTeX formatted).
                  If None, a default part will be created if an expression is explicitly passed via 'expression_for_part'.
    """
    parts_to_add = []
    if parts:
        for part in parts:
            try:
                # Ensure the 'latex' value in each part is a string
                part_latex_str = latex(part['latex']) if not isinstance(part['latex'], str) else part['latex']
                parts_to_add.append({"latex": part_latex_str, "rule_id": rule_key, "explanation_key": part.get('explanation_key', rule_key)})
            except Exception as e:
                logger.warning(f"Could not convert part to LaTeX for step '{rule_key}': {part.get('latex')}, Error: {e}")
                parts_to_add.append({"latex": str(part.get('latex', '')), "rule_id": rule_key, "explanation_key": part.get('explanation_key', rule_key)})
    
    step_id = f"step_{len(steps_list)}_{rule_key}"
    steps_list.append({
        "id": step_id,
        "prefix": prefix,
        "parts": parts_to_add,
        "explanation_text": explanation
    })
    return step_id

def _differentiate_recursive_dag(expression, variable, steps_list):
    # Check cache first for DAG behavior
    cache_key = (expression, variable)
    if cache_key in _differentiation_cache:
        # If already computed, return the cached result. No new steps are added for cached computations.
        return _differentiation_cache[cache_key]

    result = None

    # Rule: Derivative of a constant is 0
    if not expression.has(variable):
        _add_step(steps_list, "constantRule", 
                  f"The derivative of constant ${latex(expression)}$ is 0.",
                  parts=[{"latex": S.Zero, "explanation_key": "constantRule"}])
        result = S.Zero

    # Rule: Derivative of the variable itself is 1
    elif expression == variable:
        _add_step(steps_list, "variableRule", 
                  f"The derivative of ${latex(variable)}$ with respect to itself is 1.",
                  parts=[{"latex": S.One, "explanation_key": "variableRule"}])
        result = S.One

    # --- Sum Rule: d(u+v)/dx = du/dx + dv/dx ---
    elif isinstance(expression, Add):
        _add_step(steps_list, "sumRule_start", 
                  f"Applying Sum Rule to: ",
                  parts=[{"latex": expression, "explanation_key": "sumRule_start"}])
        d_terms = []
        for arg in expression.args:
            d_term = _differentiate_recursive_dag(arg, variable, steps_list)
            d_terms.append(d_term)
        result = Add(*d_terms).simplify()
        _add_step(steps_list, "sumRule_result", 
                  f"Sum of derivatives: ${latex(result)}$",
                  parts=[{"latex": result, "explanation_key": "sumRule_result"}])
        
    # --- Product Rule: d(u*v)/dx = u*(dv/dx) + v*(du/dx) ---
    elif isinstance(expression, Mul):
        const_terms = [arg for arg in expression.args if not arg.has(variable)]
        non_const_terms = [arg for arg in expression.args if arg.has(variable)]

        # Constant Multiple Rule: d(c*f(x))/dx = c * d(f(x))/dx
        if const_terms and non_const_terms:
            c = Mul(*const_terms)
            f = Mul(*non_const_terms)
            _add_step(steps_list, "constantMultipleRule_start", 
                      f"Applying Constant Multiple Rule to: ",
                      parts=[{"latex": Mul(c,f), "explanation_key": "constantMultipleRule_start"}])
            df_dx = _differentiate_recursive_dag(f, variable, steps_list)
            result = Mul(c, df_dx).simplify()
            _add_step(steps_list, "constantMultipleRule_result", 
                      f"Result: ${latex(c)} \\cdot ({latex(df_dx)}) = {latex(result)}$",
                      parts=[{"latex": result, "explanation_key": "constantMultipleRule_result"}])
            
        # Standard Product Rule for two variable terms
        elif len(non_const_terms) == 2 and not const_terms:
            u, v = non_const_terms[0], non_const_terms[1]
            _add_step(steps_list, "productRule_start", 
                      f"Applying Product Rule to: ",
                      parts=[{"latex": expression, "explanation_key": "productRule_start"}])
            
            _add_step(steps_list, "productRule_dv_dx_expr", 
                      f"Derivative of second term: $\\frac{{d}}{{d{latex(variable)}}}({latex(v)})$",
                      parts=[{"latex": Derivative(v, variable), "explanation_key": "productRule_dv_dx_expr"}])
            dv_dx = _differentiate_recursive_dag(v, variable, steps_list)
            
            _add_step(steps_list, "productRule_du_dx_expr", 
                      f"Derivative of first term: $\\frac{{d}}{{d{latex(variable)}}}({latex(u)})$",
                      parts=[{"latex": Derivative(u, variable), "explanation_key": "productRule_du_dx_expr"}])
            du_dx = _differentiate_recursive_dag(u, variable, steps_list)
            
            term1 = Mul(u, dv_dx).simplify()
            term2 = Mul(v, du_dx).simplify()
            result = Add(term1, term2).simplify()
            explanation_text = f"Product Rule result: $({latex(u)})({latex(dv_dx)}) + ({latex(v)})({latex(du_dx)}) = {latex(result)}$"
            _add_step(steps_list, "productRule_result", explanation_text,
                      parts=[{"latex": result, "explanation_key": "productRule_result"}])
            
        # Product rule for more than two variable terms (fallback to SymPy for simplicity)
        elif len(non_const_terms) > 2 and not const_terms:
            _add_step(steps_list, "productRule_complex", 
                      f"Applying Product Rule to multiple terms like",
                      parts=[{"latex": expression, "explanation_key": "productRule_complex"}])
            result = Derivative(expression, variable, evaluate=True).simplify()
            _add_step(steps_list, "productRule_sympy_fallback", 
                      f"Using SymPy's diff for complex product step. Result: ${latex(result)}$",
                      parts=[{"latex": result, "explanation_key": "productRule_sympy_fallback"}])
            
        else: # Only constant terms or no terms (shouldn't happen with SymPy Mul)
            _add_step(steps_list, "constantRule", 
                      f"Derivative of constant product '${latex(expression)}'$ is 0.",
                      parts=[{"latex": S.Zero, "explanation_key": "constantRule"}])
            result = S.Zero

    # --- Quotient Rule: d(u/v)/dx = (v*(du/dx) - u*(dv/dx)) / v^2 ---
    elif isinstance(expression, Mul) and any(isinstance(arg, Pow) and arg.args[1].is_negative for arg in expression.args):
        numerator_args = [arg for arg in expression.args if not (isinstance(arg, Pow) and arg.args[1].is_negative)]
        denominator_args = [arg.args[0] for arg in expression.args if isinstance(arg, Pow) and arg.args[1].is_negative]

        if len(denominator_args) == 1:
            u = Mul(*numerator_args).simplify()
            v = denominator_args[0]
            
            original_quotient_latex = f"\\frac{{{latex(u)}}}{{{latex(v)}}}"
            _add_step(steps_list, "quotientRule_start", 
                      f"Applying Quotient Rule to: ",
                      parts=[{"latex": original_quotient_latex, "explanation_key": "quotientRule_start"}])

            _add_step(steps_list, "quotientRule_du_dx_expr", 
                      f"Derivative of numerator: ",
                      parts=[{"latex": Derivative(u, variable), "explanation_key": "quotientRule_du_dx_expr"}])
            du_dx = _differentiate_recursive_dag(u, variable, steps_list)
            
            _add_step(steps_list, "quotientRule_dv_dx_expr", 
                      f"Derivative of denominator: ",
                      parts=[{"latex": Derivative(v, variable), "explanation_key": "quotientRule_dv_dx_expr"}])
            dv_dx = _differentiate_recursive_dag(v, variable, steps_list)
            
            term1 = Mul(v, du_dx).simplify()
            term2 = Mul(u, dv_dx).simplify()
            
            quotient_numerator = Add(term1, Mul(S.NegativeOne, term2)).simplify()
            quotient_denominator = Pow(v, 2).simplify()
            
            result = Mul(quotient_numerator, Pow(quotient_denominator, -1)).simplify()

            explanation_text = f"Quotient Rule result: $\\frac{{{latex(v)} \\cdot ({latex(du_dx)}) - {latex(u)} \\cdot ({latex(dv_dx)})}}{{{latex(Pow(v,2))}}} = {latex(result)}$"
            _add_step(steps_list, "quotientRule_result", explanation_text,
                      parts=[{"latex": result, "explanation_key": "quotientRule_result"}])
            
        else:
            _add_step(steps_list, "quotientRule_complex_fallback", 
                      f"Complex quotient expression ${latex(expression)}$ detected. Using SymPy's diff.",
                      parts=[{"latex": expression, "explanation_key": "quotientRule_complex_fallback"}])
            result = Derivative(expression, variable, evaluate=True).simplify()
            _add_step(steps_list, "quotientRule_sympy_fallback", 
                      f"Fallback SymPy result: ${latex(result)}$",
                      parts=[{"latex": result, "explanation_key": "quotientRule_sympy_fallback"}])
            
    # --- Power Rule: d(u^n)/dx = n*u^(n-1)*du/dx ---
    elif isinstance(expression, Pow):
        base, exponent = expression.args[0], expression.args[1]
        
        if exponent == S.Half: # This handles sqrt(u)
            _add_step(steps_list, "sqrtRule_start", 
                      f"Applying Square Root Rule to: ",
                      parts=[{"latex": expression, "explanation_key": "sqrtRule_start"}])
            
            _add_step(steps_list, "chainRule_for_sqrt_arg", 
                      f"Chain rule: need derivative of argument: ",
                      parts=[{"latex": Derivative(base, variable), "explanation_key": "chainRule_for_sqrt_arg"}])
            dbase_dx = _differentiate_recursive_dag(base, variable, steps_list)
            
            result = Mul(S.Half, Pow(base, S.NegativeHalf), dbase_dx).simplify()
            _add_step(steps_list, "sqrtRule_result", 
                      f"Square Root Rule result: $\\frac{{1}}{{2\\sqrt{{{latex(base)}}}}} \\cdot ({latex(dbase_dx)}) = {latex(result)}$",
                      parts=[{"latex": result, "explanation_key": "sqrtRule_result"}])
            
        elif not exponent.has(variable): # u^n where n is constant
            n = exponent
            _add_step(steps_list, "powerRule_start", 
                      f"Applying Power Rule to: ",
                      parts=[{"latex": expression, "explanation_key": "powerRule_start"}])

            _add_step(steps_list, "chainRule_for_power_base", 
                      f"Chain rule: need derivative of base term: ",
                      parts=[{"latex": Derivative(base, variable), "explanation_key": "chainRule_for_power_base"}])
            dbase_dx = _differentiate_recursive_dag(base, variable, steps_list)
            
            term_n = n
            term_base_pow = Pow(base, n - 1).simplify()
            
            result = Mul(term_n, term_base_pow, dbase_dx).simplify()
            _add_step(steps_list, "powerRule_u_n_result", 
                      f"Power Rule result for: ",
                      parts=[{"latex": result, "explanation_key": "powerRule_u_n_result"}])
            
        elif not base.has(variable) and exponent.has(variable): # a^u where a is constant
            a = base
            _add_step(steps_list, "expRule_a_u_start", 
                      f"Applying Exponential Rule for $({latex(a)})^{{{latex(exponent)}}}$",
                      parts=[{"latex": expression, "explanation_key": "expRule_a_u_start"}])
            _add_step(steps_list, "chainRule_for_exp_a_u_exponent", 
                      f"Chain rule: need derivative of exponent: ",
                      parts=[{"latex": Derivative(exponent, variable), "explanation_key": "chainRule_for_exp_a_u_exponent"}])
            du_dx = _differentiate_recursive_dag(exponent, variable, steps_list)
            result = Mul(expression, log(a), du_dx).simplify() 
            _add_step(steps_list, "expRule_a_u_result", 
                      f"Result for: ",
                      parts=[{"latex": result, "explanation_key": "expRule_a_u_result"}])
            
        else: # f(x)^g(x) - general power rule (logarithmic differentiation)
            _add_step(steps_list, "powerRule_general_start", 
                      f"General Power Rule for functions raised to functions: ",
                      parts=[{"latex": expression, "explanation_key": "powerRule_general_start"}])
            result = Derivative(expression, variable, evaluate=True).simplify()
            _add_step(steps_list, "powerRule_general_sympy_fallback", 
                      f"Using SymPy's diff for general power rule $f(x)^{{g(x)}}$. Result: ${latex(result)}$",
                      parts=[{"latex": result, "explanation_key": "powerRule_general_sympy_fallback"}])

    # --- Function Calls (Chain Rule implicitly) ---
    elif isinstance(expression, sin):
        u = expression.args[0]
        _add_step(steps_list, "sinRule_start", 
                  f"Applying Sine Rule to: ",
                  parts=[{"latex": expression, "explanation_key": "sinRule_start"}])
        _add_step(steps_list, "chainRule_for_sin_arg", 
                  f"Chain rule: need derivative of argument: ",
                  parts=[{"latex": Derivative(u, variable), "explanation_key": "chainRule_for_sin_arg"}])
        du_dx = _differentiate_recursive_dag(u, variable, steps_list)
        result = Mul(cos(u), du_dx).simplify()
        _add_step(steps_list, "sinRule_result", 
                  f"Sine Rule result: ",
                  parts=[{"latex": result, "explanation_key": "sinRule_result"}])

    elif isinstance(expression, cos):
        u = expression.args[0]
        _add_step(steps_list, "cosRule_start", 
                  f"Applying Cosine Rule to: ",
                  parts=[{"latex": expression, "explanation_key": "cosRule_start"}])
        _add_step(steps_list, "chainRule_for_cos_arg", 
                  f"Chain rule: need derivative of argument:",
                  parts=[{"latex": Derivative(u, variable), "explanation_key": "chainRule_for_cos_arg"}])
        du_dx = _differentiate_recursive_dag(u, variable, steps_list)
        result = Mul(S.NegativeOne, sin(u), du_dx).simplify() 
        _add_step(steps_list, "cosRule_result", 
                  f"Cosine Rule result: $-\\sin({latex(u)}) \\cdot ({latex(du_dx)}) = {latex(result)}$",
                  parts=[{"latex": result, "explanation_key": "cosRule_result"}])

    elif isinstance(expression, tan):
        u = expression.args[0]
        _add_step(steps_list, "tanRule_start", 
                  f"Applying Tangent Rule to: ",
                  parts=[{"latex": expression, "explanation_key": "tanRule_start"}])
        _add_step(steps_list, "chainRule_for_tan_arg", 
                  f"Chain rule: need derivative of argument: ",
                  parts=[{"latex": Derivative(u, variable), "explanation_key": "chainRule_for_tan_arg"}])
        du_dx = _differentiate_recursive_dag(u, variable, steps_list)
        result = Mul(Pow(sec(u), 2), du_dx).simplify() 
        _add_step(steps_list, "tanRule_result", 
                  f"Tangent Rule result: ",
                  parts=[{"latex": result, "explanation_key": "tanRule_result"}])

    elif isinstance(expression, sec):
        u = expression.args[0]
        _add_step(steps_list, "secRule_start", 
                  f"Applying Secant Rule to: ",
                  parts=[{"latex": expression, "explanation_key": "secRule_start"}])
        _add_step(steps_list, "chainRule_for_sec_arg", 
                  f"Chain rule: need derivative of argument: ",
                  parts=[{"latex": Derivative(u, variable), "explanation_key": "chainRule_for_sec_arg"}])
        du_dx = _differentiate_recursive_dag(u, variable, steps_list)
        result = Mul(sec(u), tan(u), du_dx).simplify() 
        _add_step(steps_list, "secRule_result", 
                  f"Secant Rule result: ",
                  parts=[{"latex": result, "explanation_key": "secRule_result"}])

    elif isinstance(expression, csc):
        u = expression.args[0]
        _add_step(steps_list, "cscRule_start", 
                  f"Applying Cosecant Rule to: ",
                  parts=[{"latex": expression, "explanation_key": "cscRule_start"}])
        _add_step(steps_list, "chainRule_for_csc_arg", 
                  f"Chain rule: need derivative of argument: ",
                  parts=[{"latex": Derivative(u, variable), "explanation_key": "chainRule_for_csc_arg"}])
        du_dx = _differentiate_recursive_dag(u, variable, steps_list)
        result = Mul(S.NegativeOne, csc(u), cot(u), du_dx).simplify() 
        _add_step(steps_list, "cscRule_result", 
                  f"Cosecant Rule result: ",
                  parts=[{"latex": result, "explanation_key": "cscRule_result"}])

    elif isinstance(expression, cot):
        u = expression.args[0]
        _add_step(steps_list, "cotRule_start", 
                  f"Applying Cotangent Rule to: ",
                  parts=[{"latex": expression, "explanation_key": "cotRule_start"}])
        _add_step(steps_list, Derivative(u, variable), "chainRule_for_cot_arg", f"Chain rule: need derivative of argument: ")
        du_dx = _differentiate_recursive_dag(u, variable, steps_list)
        result = Mul(S.NegativeOne, Pow(csc(u), 2), du_dx).simplify() 
        _add_step(steps_list, "cotRule_result", 
                  f"Cotangent Rule result: ",
                  parts=[{"latex": result, "explanation_key": "cotRule_result"}])

    elif isinstance(expression, exp):
        u = expression.args[0]
        _add_step(steps_list, "expRule_start", 
                  f"Applying Exponential Rule to: ",
                  parts=[{"latex": expression, "explanation_key": "expRule_start"}])
        _add_step(steps_list, "chainRule_for_exp_arg", 
                  f"Chain rule: need derivative of argument: ",
                  parts=[{"latex": Derivative(u, variable), "explanation_key": "chainRule_for_exp_arg"}])
        du_dx = _differentiate_recursive_dag(u, variable, steps_list)
        result = Mul(exp(u), du_dx).simplify() 
        _add_step(steps_list, "expRule_result", 
                  f"Exponential Rule $e^u$ result: $e^{{{latex(u)}}} \\cdot ({latex(du_dx)}) = {latex(result)}$",
                  parts=[{"latex": result, "explanation_key": "expRule_result"}])
    
    elif isinstance(expression, log): # Natural logarithm (base e)
        u = expression.args[0]
        _add_step(steps_list, "logRule_start", 
                  f"Applying Natural Logarithmic Rule to: ",
                  parts=[{"latex": expression, "explanation_key": "logRule_start"}])
        _add_step(steps_list, "chainRule_for_log_arg", 
                  f"Chain rule: need derivative of argument: ",
                  parts=[{"latex": Derivative(u, variable), "explanation_key": "chainRule_for_log_arg"}])
        du_dx = _differentiate_recursive_dag(u, variable, steps_list)
        result = Mul(Pow(u, -1), du_dx).simplify() 
        _add_step(steps_list, "logRule_result", 
                  f"Natural Logarithmic Rule result: ",
                  parts=[{"latex": result, "explanation_key": "logRule_result"}])
    
    # Generic function (e.g., f(x), g(x) not defined in SymPy)
    elif isinstance(expression, Function) and not isinstance(expression, (sin,cos,exp,log,Pow,Add,Mul,Integer,Symbol,Derivative,UndefinedFunction,sqrt,tan,sec,csc,cot)):
        _add_step(steps_list, "generalFunctionRule_start", 
                  f"General function derivative for ${latex(expression)}$",
                  parts=[{"latex": expression, "explanation_key": "generalFunctionRule_start"}])
        result = Derivative(expression, variable, evaluate=True).simplify() 
        _add_step(steps_list, "generalFunctionRule_result", 
                  f"Result for ${latex(expression)}$: ${latex(result)}$",
                  parts=[{"latex": result, "explanation_key": "generalFunctionRule_result"}])

    # Fallback for expressions not explicitly handled by rules
    else:
        _add_step(steps_list, "unknownRule", 
                  f"No specific DAG rule matched for: ${latex(expression)}$. Using SymPy's diff as fallback.",
                  parts=[{"latex": expression, "explanation_key": "unknownRule"}])
        result = Derivative(expression, variable, evaluate=True).simplify()
        _add_step(steps_list, "unknownRule_sympy_fallback", 
                  f"Fallback SymPy result: ${latex(result)}$",
                  parts=[{"latex": result, "explanation_key": "unknownRule_sympy_fallback"}])
    
    # Store result in cache
    _differentiation_cache[cache_key] = result
    
    return result


def compute_derivative_dag(sympy_expr, variable_symbol):
    steps = []  
    # Clear cache for each new computation
    _differentiation_cache.clear()

    _add_step(steps, "initial_expression", 
              f"Differentiating with respect to {latex(variable_symbol)}", 
              prefix=f"\\frac{{d}}{{d{latex(variable_symbol)}}}",
              parts=[{"latex": sympy_expr, "explanation_key": "initial_expression"}])

    tracemalloc.start()
    start_time = time.perf_counter()

    differentiated_expr = _differentiate_recursive_dag(sympy_expr, variable_symbol, steps) 
    
    end_time = time.perf_counter()
    current_memory, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop() # Stop tracemalloc when done

    execution_time_ms = (end_time - start_time) * 1000

    final_latex_derivative = latex(differentiated_expr)
    
    # Check if the last step's rendered LaTeX matches the final derivative
    # This comparison needs to be robust, comparing rendered LaTeX strings
    if not steps or (steps[-1]['parts'] and steps[-1]['parts'][0]['latex'] != final_latex_derivative):
        _add_step(steps, "final_derivative", 
                  f"The final derivative is: ",
                  parts=[{"latex": differentiated_expr, "explanation_key": "final_derivative"}])
    else: # Update the last step if it already contains the final result
        # This branch ensures the last step's explanation and rule_id are correct for the final result
        steps[-1]['explanation_text'] = f"The final derivative is: "
        # The 'parts' should already contain the correct LaTeX if the expression matched
        steps[-1]['parts'][0]['explanation_key'] = "final_derivative"
        steps[-1]['rule_id'] = "final_derivative" # Ensure the top-level rule_id is also updated

    raw_sympy_derivative = differentiated_expr 

    dag_node_count_val = len(_differentiation_cache) 
    
    return {
        "derivative_latex": final_latex_derivative,
        "raw_sympy_derivative": raw_sympy_derivative, 
        "steps": steps,
        "execution_time_ms": execution_time_ms,
        "peak_memory_bytes": peak_memory,
        "ast_node_count": dag_node_count_val, 
        "data_structure_used": "DAG"
    }
