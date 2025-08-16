# derivative_ast.py
from sympy import (
    symbols, sympify, latex, Add, Mul, Pow, sin, cos, exp, log,
    Integer, Symbol, Derivative, Function, tan, sec, csc, cot, S
)
from functools import lru_cache
import time
import tracemalloc
import logging

logger = logging.getLogger(__name__)

# ---------- Lightweight caches ----------
@lru_cache(maxsize=8192)
def _cached_latex(expr):
    """Return LaTeX for expr with caching to avoid repeated expensive conversions."""
    try:
        return latex(expr)
    except Exception:
        return str(expr)

@lru_cache(maxsize=None)
def _diff_value_cached(expr, var):
    """Compute (and cache) the derivative value using SymPy's engine.
    This is used as a fallback or when we want the derivative value but don't
    need to record the detailed step trace again."""
    return Derivative(expr, var, evaluate=True).doit()

# ---------- step helper ----------
def _add_step(steps_list, latex_or_expr, rule_key, explanation, prefix="= "):
    """Add a step, accepting either an already-rendered LaTeX string or a SymPy expr."""
    if isinstance(latex_or_expr, str):
        expr_latex = latex_or_expr
    else:
        expr_latex = _cached_latex(latex_or_expr)
    steps_list.append({
        "id": f"step_{len(steps_list)}_{rule_key}",
        "prefix": prefix,
        "parts": [
            {"latex": expr_latex, "rule_id": rule_key, "explanation_key": rule_key}
        ],
        "explanation_text": explanation
    })

# ---------- AST differentiator (refactored) ----------
def compute_derivative_ast(sympy_expr, variable_symbol):
    """
    Compute derivative using AST-style traversal.
    Uses local memoization to avoid recomputing identical sub-derivatives.
    Returns the same shape of result dict as original implementation.
    """
    steps = []
    # local cache keyed by (expr, var) -> derivative (SymPy)
    local_cache = {}

    _add_step(steps, sympy_expr, "initial_expression",
              f"Differentiating: ",
              prefix=f"\\frac{{d}}{{d{_cached_latex(variable_symbol)}}}")

    tracemalloc.start()
    start_time = time.perf_counter()
    try:
        def _rec(expr):
            """Recursive differentiator that records steps on first computation;
               returns a SymPy expression (derivative)."""
            key = (expr, variable_symbol)
            if key in local_cache:
                # Use cached derivative value, but record a short cached notice to keep trace concise
                cached_value = local_cache[key]
                _add_step(steps, _cached_latex(cached_value), "cached_subexpr",
                          f"Using cached derivative for { _cached_latex(expr) }")
                return cached_value

            # Base cases
            if not expr.has(variable_symbol):
                _add_step(steps, S.Zero, "constantRule",
                          f"Derivative of a constant is: ")
                local_cache[key] = S.Zero
                return S.Zero

            if expr == variable_symbol:
                _add_step(steps, S.One, "variableRule",
                          f"Derivative of {_cached_latex(variable_symbol)} with respect to itself is: ")
                local_cache[key] = S.One
                return S.One

            # Sum
            if isinstance(expr, Add):
                _add_step(steps, expr, "sumRule_start", "Applying Sum Rule to:")
                d_terms = [ _rec(arg) for arg in expr.args ]
                result = Add(*d_terms)
                local_cache[key] = result
                _add_step(steps, result, "sumRule_result", f"Sum of derivatives:")
                return result

            # Product (incl. constant multiple)
            if isinstance(expr, Mul):
                const_terms = [a for a in expr.args if not a.has(variable_symbol)]
                non_const_terms = [a for a in expr.args if a.has(variable_symbol)]

                # constant multiple: c * f(x)
                if const_terms and non_const_terms:
                    c = Mul(*const_terms)
                    f = Mul(*non_const_terms)
                    _add_step(steps, expr, "constantMultipleRule_start",
                              f"Applying Constant Multiple Rule to: ")
                    df = _rec(f)
                    result = Mul(c, df)
                    local_cache[key] = result
                    _add_step(steps, result, "constantMultipleRule_result",
                              f"Result of Constant Multiple Rule: ")
                    return result

                # standard product rule for two factors
                if len(non_const_terms) == 2 and not const_terms:
                    u, v = non_const_terms
                    _add_step(steps, expr, "productRule_start", f"Applying Product Rule to: ")
                    # show d/dx(...) display without constructing Derivative objects
                    _add_step(steps, f"\\frac{{d}}{{d{_cached_latex(variable_symbol)}}}({_cached_latex(v)})",
                              "productRule_dv_dx_expr", f"Derivative of second term")
                    dv = _rec(v)
                    _add_step(steps, f"\\frac{{d}}{{d{_cached_latex(variable_symbol)}}}({_cached_latex(u)})",
                              "productRule_du_dx_expr", f"Derivative of first term")
                    du = _rec(u)
                    term1 = Mul(u, dv)
                    term2 = Mul(v, du)
                    result = Add(term1, term2)
                    local_cache[key] = result
                    _add_step(steps, result, "productRule_result",
                              f"Product Rule result: ")
                    return result

                # many-term product: use efficient product-sum trick
                if len(non_const_terms) > 2 and not const_terms:
                    # Compute P * sum(d(ai)/ai)
                    P = expr
                    # compute derivative values for terms that depend on var
                    sum_parts = []
                    for a in expr.args:
                        if a.has(variable_symbol):
                            da = _rec(a)
                            # safe symbolic division (we rely on symbolic algebra)
                            sum_parts.append(da / a)
                    result = Mul(P, Add(*sum_parts))
                    local_cache[key] = result
                    _add_step(steps, result, "productRule_many_terms",
                              f"Product rule (many factors) optimized: ")
                    return result

                # else: constant product -> 0
                _add_step(steps, S.Zero, "constantRule",
                          f"Derivative of constant product is: ")
                local_cache[key] = S.Zero
                return S.Zero

            # Quotient handling: SymPy usually represents u/v as u * v**(-1)
            if isinstance(expr, Mul) and any(isinstance(a, Pow) and a.args[1].is_negative for a in expr.args):
                # fallback to SymPy solution (cached)
                _add_step(steps, expr, "quotientRule_start", f"Applying Quotient Rule to: ")
                result = _diff_value_cached(expr, variable_symbol)
                local_cache[key] = result
                _add_step(steps, result, "quotientRule_result", f"Using SymPy for quotient: ")
                return result

            # Power
            if isinstance(expr, Pow):
                base, exponent = expr.args[0], expr.args[1]
                _add_step(steps, expr, "powerRule_start", "Applying Power Rule to:")
                if not exponent.has(variable_symbol):
                    # u^n
                    dbase = _rec(base)
                    result = Mul(exponent, Pow(base, exponent - 1), dbase)
                    local_cache[key] = result
                    _add_step(steps, result, "powerRule_u_n_result", f"Power rule result: ")
                    return result
                if not base.has(variable_symbol) and exponent.has(variable_symbol):
                    # a^u
                    du = _rec(exponent)
                    result = Mul(expr, log(base), du)
                    local_cache[key] = result
                    _add_step(steps, result, "expRule_a_u_result", f"Exponential rule result: ")
                    return result
                # general case: fallback
                result = _diff_value_cached(expr, variable_symbol)
                local_cache[key] = result
                _add_step(steps, result, "powerRule_general_sympy_fallback",
                          f"General power fallback: ")
                return result

            # elementary functions (sin, cos, tan, sec, csc, cot, exp, log)
            # We prefer to pattern-match by type/class rather than using isinstance(expr, sin) etc.
            # But SymPy's sin, cos are callable classes, so the earlier style still works.
            if isinstance(expr, sin):
                u = expr.args[0]
                _add_step(steps, expr, "sinRule_start", "Applying Sine Rule to:")
                du = _rec(u)
                result = Mul(cos(u), du)
                local_cache[key] = result
                _add_step(steps, result, "sinRule_result", f"Sine Rule result:")
                return result

            if isinstance(expr, cos):
                u = expr.args[0]
                _add_step(steps, expr, "cosRule_start", "Applying Cosine Rule to:")
                du = _rec(u)
                result = Mul(S.NegativeOne, sin(u), du)
                local_cache[key] = result
                _add_step(steps, result, "cosRule_result", f"Cosine Rule result:")
                return result

            if isinstance(expr, tan):
                u = expr.args[0]
                _add_step(steps, expr, "tanRule_start", "Applying Tangent Rule to:")
                du = _rec(u)
                result = Mul(Pow(sec(u), 2), du)
                local_cache[key] = result
                _add_step(steps, result, "tanRule_result", f"Tangent Rule result:")
                return result

            if isinstance(expr, sec):
                u = expr.args[0]
                _add_step(steps, expr, "secRule_start", "Applying Secant Rule to:")
                du = _rec(u)
                result = Mul(sec(u), tan(u), du)
                local_cache[key] = result
                _add_step(steps, result, "secRule_result", f"Secant Rule result:")
                return result

            if isinstance(expr, csc):
                u = expr.args[0]
                _add_step(steps, expr, "cscRule_start", "Applying Cosecant Rule to:")
                du = _rec(u)
                result = Mul(S.NegativeOne, csc(u), cot(u), du)
                local_cache[key] = result
                _add_step(steps, result, "cscRule_result", f"Cosecant Rule result:")
                return result

            if isinstance(expr, cot):
                u = expr.args[0]
                _add_step(steps, expr, "cotRule_start", "Applying Cotangent Rule to:")
                du = _rec(u)
                result = Mul(S.NegativeOne, Pow(csc(u), 2), du)
                local_cache[key] = result
                _add_step(steps, result, "cotRule_result", f"Cotangent Rule result:")
                return result

            if isinstance(expr, exp):
                u = expr.args[0]
                _add_step(steps, expr, "expRule_start", "Applying Exponential Rule to:")
                du = _rec(u)
                result = Mul(exp(u), du)
                local_cache[key] = result
                _add_step(steps, result, "expRule_result", f"Exponential result: ")
                return result

            if isinstance(expr, log):
                u = expr.args[0]
                _add_step(steps, expr, "logRule_start", "Applying Log Rule to:")
                du = _rec(u)
                result = Mul(Pow(u, -1), du)
                local_cache[key] = result
                _add_step(steps, result, "logRule_result", f"Log result: ")
                return result

            # general function fallback
            _add_step(steps, expr, "unknownRule", f"No specific AST rule matched for: . Using SymPy's diff as fallback.")
            result = _diff_value_cached(expr, variable_symbol)
            local_cache[key] = result
            _add_step(steps, result, "unknownRule_sympy_fallback", f"Fallback result: ")
            return result

        differentiated_expr = _rec(sympy_expr)
        # Final simplify once (helps readability while avoiding repeated work)
        final_expr = differentiated_expr.simplify()
    finally:
        end_time = time.perf_counter()
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    # ensure final derivative is present at the end of steps
    if not steps or steps[-1]['parts'][0]['latex'] != _cached_latex(final_expr):
        _add_step(steps, final_expr, "final_derivative", "The final derivative is:")

    # ast node count: try preorder traversal if available, else -1
    ast_node_count_val = -2
    try:
        if hasattr(sympy_expr, 'preorder_traversal'):
            ast_node_count_val = len(list(sympy_expr.preorder_traversal()))
    except Exception as e:
        logger.debug(f"preorder_traversal failed: {e}")

    return {
        "derivative_latex": _cached_latex(final_expr),
        "raw_sympy_derivative": final_expr,
        "steps": steps,
        "execution_time_ms": (end_time - start_time) * 1000,
        "peak_memory_bytes": peak_memory,
        "ast_node_count": ast_node_count_val
    }
