import importlib

def run_benchmark(structure_name, expression, variable='x'):

    # Dynamically import the structure file
    module = importlib.import_module(structure_name)
    
    # Pick the correct compute function automatically
    for fn_name in dir(module):
        if fn_name.startswith("compute_derivative_"):
            compute_fn = getattr(module, fn_name)
            break
    else:
        raise ValueError(f"No compute_derivative_* function found in {structure_name}")

    # Run the derivative computation
    result = compute_fn(expression, variable)

    # Return numeric-safe output for MATLAB
    return {
        "structure": structure_name,
        "expression": expression,
        "time_ms": float(result.get("execution_time_ms", 0.0)),
        "memory_bytes": float(result.get("peak_memory_bytes", 0.0)),
        "latex": result.get("derivative_latex", "")
    }
