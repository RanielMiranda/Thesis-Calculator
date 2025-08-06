import random
from sympy import symbols, S, sin, cos, tan, exp, log, Add, Mul, Pow

def generate_random_expression(variables, num_terms=3, max_depth=2):
    """
    Generates a random SymPy expression.
    Args:
        variables (list): A list of SymPy Symbol objects to use as variables.
        num_terms (int): The number of top-level terms in the expression.
        max_depth (int): The maximum nesting depth of the expression tree.
    Returns:
        sympy.core.expr.Expr: A randomly generated SymPy expression.
    """
    # Define available functions and operators
    operators = [Add, Mul, Pow]
    functions = [sin, cos, exp, log]
    
    # Simple leaf nodes (variables or constants)
    def create_leaf():
        if random.random() < 0.7:  # 70% chance of being a variable
            return random.choice(variables)
        else: # 30% chance of being a constant
            return S(random.randint(1, 10))

    # Recursive function to build the tree
    def create_node(current_depth):
        if current_depth >= max_depth or random.random() < 0.4: # Base case: create a leaf
            return create_leaf()
        
        # Recursive case: create a function or operator node
        choice = random.choice(operators + functions)
        
        if choice in functions:
            # Function nodes have a single child
            return choice(create_node(current_depth + 1))
        else:
            # Operator nodes have two children (for simplicity)
            return choice(create_node(current_depth + 1), create_node(current_depth + 1))
    
    # Combine terms with addition to form the final expression
    terms = [create_node(0) for _ in range(num_terms)]
    return Add(*terms)

if __name__ == '__main__':
    # Example usage
    x, y = symbols('x y')
    expr = generate_random_expression([x, y], num_terms=2, max_depth=3)
    print(f"Generated Expression: {expr}")
