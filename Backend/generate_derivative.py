# generate_derivative.py
import sympy
import random

def generate_random_expression(
    max_depth=3,
    include_trig=True,
    include_exp_log=True,
    include_power=True,
    num_terms_max=2,
    variables=('x',)
):
    """
    Generates a random mathematical expression using SymPy.

    Args:
        max_depth (int): Maximum depth of the expression tree.
        include_trig (bool): Whether to include trigonometric functions (sin, cos, tan, sec, csc, cot).
        include_exp_log (bool): Whether to include exponential (e^x) and logarithmic (ln(x)) functions.
        include_power (bool): Whether to include power functions (x^n).
        num_terms_max (int): Maximum number of terms in sums/products.
        variables (tuple): Tuple of variable symbols (e.g., ('x',)).

    Returns:
        sympy.Expr: A randomly generated SymPy expression.
    """
    if not variables:
        raise ValueError("At least one variable must be provided.")

    x = sympy.symbols(variables[0]) # Use the first variable for simplicity in generation
                                    # Can be extended to use multiple variables

    # Base elements: variables and constants
    base_elements = [x, sympy.Integer(random.randint(1, 5))]

    # Functions available
    functions = []
    if include_trig:
        functions.extend([sympy.sin, sympy.cos, sympy.tan, sympy.sec, sympy.csc, sympy.cot])
    if include_exp_log:
        functions.extend([sympy.exp, sympy.log])
    
    # Operators
    operators = [sympy.Add, sympy.Mul]
    if include_power:
        operators.append(sympy.Pow)

    def _gen_expr(current_depth):
        if current_depth >= max_depth:
            return random.choice(base_elements)

        choice = random.randint(0, 100)
        
        # Chance to pick a base element
        if choice < 30: # 30% chance for base element
            return random.choice(base_elements)
        
        # Chance to pick a function
        if functions and choice < 60: # 30% chance for function
            func = random.choice(functions)
            arg = _gen_expr(current_depth + 1)
            return func(arg)
        
        # Otherwise, pick an operator
        op = random.choice(operators)
        num_args = random.randint(2, num_terms_max)

        if op == sympy.Pow:
            base = _gen_expr(current_depth + 1)
            # Ensure exponent is a simple number for basic generation
            exponent_type = random.choice(['integer', 'variable'])
            if exponent_type == 'integer':
                 exponent = sympy.Integer(random.randint(2, 4))
            else: # If we have multiple variables, pick a different one than the base's main var
                exponent = sympy.symbols(random.choice(variables)) if len(variables) > 1 else sympy.Integer(random.randint(2,4))
            return sympy.Pow(base, exponent)
        else:
            args = [_gen_expr(current_depth + 1) for _ in range(num_args)]
            return op(*args)

    expression = _gen_expr(0)
    
    # Add a constant multiple sometimes
    if random.random() < 0.3: # 30% chance
        return random.randint(1, 5) * expression
    
    return expression

if __name__ == '__main__':
    # Example usage:
    print("Generated expressions:")
    for _ in range(5):
        expr = generate_random_expression(max_depth=2, include_trig=True, include_exp_log=True)
        print(f"  {expr}")
    
    print("\nGenerated expression (no trig, max_depth=1):")
    expr_no_trig = generate_random_expression(max_depth=1, include_trig=False)
    print(f"  {expr_no_trig}")

    print("\nGenerated expression (compound, higher depth):")
    expr_compound = generate_random_expression(max_depth=4, include_trig=True, include_power=True, num_terms_max=3)
    print(f"  {expr_compound}")