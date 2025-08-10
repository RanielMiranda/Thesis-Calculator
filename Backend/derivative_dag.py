# derivative_dag.py
from sympy import (
    symbols, sympify, latex, Add, Mul, Pow, sin, cos, exp, log,
    Integer, Symbol, Derivative, Function, tan, sec, csc, cot, S
)
from functools import lru_cache
import time
import tracemalloc
import logging

logger = logging.getLogger(__name__)

# ---------- Global-ish caches for DAG file ----------
@lru_cache(maxsize=8192)
def _cached_latex(expr):
    try:
        return latex(expr)
    except Exception:
        return str(expr)

@lru_cache(maxsize=None)
def _diff_value_cached(expr, var):
    """SymPy-driven derivative value; cached globally."""
    return Derivative(expr, var, evaluate=True).doit()

# DAG cache stores derivative value and its latex to avoid recomputing either
# Use a plain dict for the session-local cache (cleared per compute run)
_differentiation_cache = {}

# ---------- step helper ----------
def _add_step(steps_list, latex_or_expr, rule_key, explanation, prefix="= "):
    if isinstance(latex_or_expr, str):
        expr_latex = latex_or_expr
    else:
        expr_latex = _cached_latex(latex_or_expr)
    steps_list.append({
        "id": f"step_{len(steps_list)}_{rule_key}",
        "prefix": prefix,
        "parts": [{"latex": expr_latex, "rule_id": rule_key, "explanation_key": rule_key}],
        "explanation_text": explanation
    })
    return steps_list[-1]['id']

# ---------- DAG differentiator ----------
def _differentiate_recursive_dag(expression, variable, steps_list, cache):
    """Differentiates expression using caching to simulate DAG reuse.
       cache is a dict mapping (expr, var) -> derivative (SymPy)"""
    key = (expression, variable)
    if key in cache:
        # On reuse just add a short cached entry and return the value
        cached_val = cache[key]
        _add_step(steps_list, _cached_latex(cached_val), "cached_subexpr",
                  f"Using cached derivative for { _cached_latex(expression) }")
        return cached_val

    # Base cases
    if not expression.has(variable):
        _add_step(steps_list, S.Zero, "constantRule", f"The derivative of { _cached_latex(expression) } is 0.",
                  prefix="= ")
        cache[key] = S.Zero
        return S.Zero

    if expression == variable:
        _add_step(steps_list, S.One, "variableRule", f"The derivative of { _cached_latex(variable) } with respect to itself is 1.")
        cache[key] = S.One
        return S.One

    # Sum
    if isinstance(expression, Add):
        _add_step(steps_list, expression, "sumRule_start", "Applying Sum Rule:")
        d_terms = [ _differentiate_recursive_dag(arg, variable, steps_list, cache) for arg in expression.args ]
        result = Add(*d_terms)
        _add_step(steps_list, result, "sumRule_result", f"Sum of derivatives: {_cached_latex(result)}")
        cache[key] = result
        return result

    # Product (constant multiple or two-term product or many-term)
    if isinstance(expression, Mul):
        const_terms = [a for a in expression.args if not a.has(variable)]
        non_const_terms = [a for a in expression.args if a.has(variable)]

        if const_terms and non_const_terms:
            c = Mul(*const_terms)
            f = Mul(*non_const_terms)
            _add_step(steps_list, expression, "constantMultipleRule_start", f"Applying Constant Multiple Rule:")
            df = _differentiate_recursive_dag(f, variable, steps_list, cache)
            result = Mul(c, df)
            _add_step(steps_list, result, "constantMultipleRule_result", f"Result: {_cached_latex(result)}")
            cache[key] = result
            return result

        if len(non_const_terms) == 2 and not const_terms:
            u, v = non_const_terms
            _add_step(steps_list, expression, "productRule_start", f"Applying Product Rule to: {_cached_latex(expression)}")
            _add_step(steps_list, f"\\frac{{d}}{{d{_cached_latex(variable)}}}({_cached_latex(v)})", "productRule_dv_dx_expr",
                      "Derivative of second term")
            dv = _differentiate_recursive_dag(v, variable, steps_list, cache)
            _add_step(steps_list, f"\\frac{{d}}{{d{_cached_latex(variable)}}}({_cached_latex(u)})", "productRule_du_dx_expr",
                      "Derivative of first term")
            du = _differentiate_recursive_dag(u, variable, steps_list, cache)
            result = Add(Mul(u, dv), Mul(v, du))
            _add_step(steps_list, result, "productRule_result", f"Product Rule result: {_cached_latex(result)}")
            cache[key] = result
            return result

        if len(non_const_terms) > 2 and not const_terms:
            # Use optimized product formula: P * sum(d(ai)/ai)
            P = expression
            sum_terms = []
            for a in expression.args:
                if a.has(variable):
                    da = _differentiate_recursive_dag(a, variable, steps_list, cache)
                    sum_terms.append(da / a)
            result = Mul(P, Add(*sum_terms))
            _add_step(steps_list, result, "productRule_many_terms", f"Optimized product result: {_cached_latex(result)}")
            cache[key] = result
            return result

        # constant case
        _add_step(steps_list, S.Zero, "constantRule", f"Derivative of constant product '{_cached_latex(expression)}' is 0.")
        cache[key] = S.Zero
        return S.Zero

    # Quotient detection (u * v**(-1)) -> fallback to SymPy
    if isinstance(expression, Mul) and any(isinstance(a, Pow) and a.args[1].is_negative for a in expression.args):
        _add_step(steps_list, expression, "quotientRule_start", f"Applying Quotient Rule to: {_cached_latex(expression)}")
        result = _diff_value_cached(expression, variable)
        _add_step(steps_list, result, "quotientRule_result", f"Quotient fallback: {_cached_latex(result)}")
        _differentiation_cache[key] = result
        cache[key] = result
        return result

    # Power
    if isinstance(expression, Pow):
        base, exponent = expression.args[0], expression.args[1]
        _add_step(steps_list, expression, "powerRule_start", "Applying Power Rule:")
        if exponent == S.Half:
            # sqrt case
            dbase = _differentiate_recursive_dag(base, variable, steps_list, cache)
            result = Mul(S.Half, Pow(base, S.NegativeHalf), dbase)
            _add_step(steps_list, result, "sqrtRule_result", f"Square root result: {_cached_latex(result)}")
            cache[key] = result
            return result
        if not exponent.has(variable):
            dbase = _differentiate_recursive_dag(base, variable, steps_list, cache)
            result = Mul(exponent, Pow(base, exponent - 1), dbase)
            _add_step(steps_list, result, "powerRule_u_n_result", f"Power result: {_cached_latex(result)}")
            cache[key] = result
            return result
        if not base.has(variable) and exponent.has(variable):
            du = _differentiate_recursive_dag(exponent, variable, steps_list, cache)
            result = Mul(expression, log(base), du)
            _add_step(steps_list, result, "expRule_a_u_result", f"Exponential a^u result: {_cached_latex(result)}")
            cache[key] = result
            return result
        # general fallback
        result = _diff_value_cached(expression, variable)
        _add_step(steps_list, result, "powerRule_general_sympy_fallback", f"General power fallback: {_cached_latex(result)}")
        cache[key] = result
        return result

    # Elementary functions
    if isinstance(expression, sin):
        u = expression.args[0]
        _add_step(steps_list, expression, "sinRule_start", "Applying Sine Rule to:")
        du = _differentiate_recursive_dag(u, variable, steps_list, cache)
        result = Mul(cos(u), du)
        _add_step(steps_list, result, "sinRule_result", f"Sine Rule result: {_cached_latex(result)}")
        cache[key] = result
        return result

    if isinstance(expression, cos):
        u = expression.args[0]
        _add_step(steps_list, expression, "cosRule_start", "Applying Cosine Rule to:")
        du = _differentiate_recursive_dag(u, variable, steps_list, cache)
        result = Mul(S.NegativeOne, sin(u), du)
        _add_step(steps_list, result, "cosRule_result", f"Cosine result: {_cached_latex(result)}")
        cache[key] = result
        return result

    if isinstance(expression, tan):
        u = expression.args[0]
        _add_step(steps_list, expression, "tanRule_start", "Applying Tangent Rule to:")
        du = _differentiate_recursive_dag(u, variable, steps_list, cache)
        result = Mul(Pow(sec(u), 2), du)
        _add_step(steps_list, result, "tanRule_result", f"Tangent result: {_cached_latex(result)}")
        cache[key] = result
        return result

    if isinstance(expression, sec):
        u = expression.args[0]
        _add_step(steps_list, expression, "secRule_start", "Applying Secant Rule to:")
        du = _differentiate_recursive_dag(u, variable, steps_list, cache)
        result = Mul(sec(u), tan(u), du)
        _add_step(steps_list, result, "secRule_result", f"Secant result: {_cached_latex(result)}")
        cache[key] = result
        return result

    if isinstance(expression, csc):
        u = expression.args[0]
        _add_step(steps_list, expression, "cscRule_start", "Applying Cosecant Rule to:")
        du = _differentiate_recursive_dag(u, variable, steps_list, cache)
        result = Mul(S.NegativeOne, csc(u), cot(u), du)
        _add_step(steps_list, result, "cscRule_result", f"Cosecant result: {_cached_latex(result)}")
        cache[key] = result
        return result

    if isinstance(expression, cot):
        u = expression.args[0]
        _add_step(steps_list, expression, "cotRule_start", "Applying Cotangent Rule to:")
        du = _differentiate_recursive_dag(u, variable, steps_list, cache)
        result = Mul(S.NegativeOne, Pow(csc(u), 2), du)
        _add_step(steps_list, result, "cotRule_result", f"Cotangent result: {_cached_latex(result)}")
        cache[key] = result
        return result

    if isinstance(expression, exp):
        u = expression.args[0]
        _add_step(steps_list, expression, "expRule_start", "Applying Exponential Rule to:")
        du = _differentiate_recursive_dag(u, variable, steps_list, cache)
        result = Mul(exp(u), du)
        _add_step(steps_list, result, "expRule_result", f"Exponential result: {_cached_latex(result)}")
        cache[key] = result
        return result

    if isinstance(expression, log):
        u = expression.args[0]
        _add_step(steps_list, expression, "logRule_start", "Applying Log Rule to:")
        du = _differentiate_recursive_dag(u, variable, steps_list, cache)
        result = Mul(Pow(u, -1), du)
        _add_step(steps_list, result, "logRule_result", f"Log result: {_cached_latex(result)}")
        cache[key] = result
        return result

    # Fallback: ask SymPy
    _add_step(steps_list, expression, "unknownRule", f"No DAG rule matched for: {_cached_latex(expression)}. Using SymPy's diff as fallback.")
    result = _diff_value_cached(expression, variable)
    _add_step(steps_list, result, "unknownRule_sympy_fallback", f"Fallback result: {_cached_latex(result)}")
    cache[key] = result
    return result

def compute_derivative_dag(sympy_expr, variable_symbol):
    """Top-level entry for DAG differentiation."""
    steps = []
    # clear session-local cache and reuse global storage for expensive cache if needed
    session_cache = {}
    _differentiation_cache.clear()

    _add_step(steps, sympy_expr, "initial_expression", f"Differentiating:",
              prefix=f"\\frac{{d}}{{d{_cached_latex(variable_symbol)}}}")

    tracemalloc.start()
    start_time = time.perf_counter()
    try:
        differentiated_expr = _differentiate_recursive_dag(sympy_expr, variable_symbol, steps, session_cache)
        # final simplify once
        final_expr = differentiated_expr.simplify()
    finally:
        end_time = time.perf_counter()
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    # ensure final derivative step exists
    if not steps or steps[-1]['parts'][0]['latex'] != _cached_latex(final_expr):
        _add_step(steps, final_expr, "final_derivative", "The final derivative is:")

    # node count = cached entries count (approx DAG nodes visited)
    dag_node_count_val = len(session_cache)

    return {
        "derivative_latex": _cached_latex(final_expr),
        "raw_sympy_derivative": final_expr,
        "steps": steps,
        "execution_time_ms": (end_time - start_time) * 1000,
        "peak_memory_bytes": peak_memory,
        "ast_node_count": dag_node_count_val,
        "data_structure_used": "DAG"
    }
