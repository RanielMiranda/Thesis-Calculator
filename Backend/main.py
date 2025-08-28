import logging
import re
import operator as op # Although op is not strictly used in the new manual parser, it's a standard import for expression parsing context
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sympy import Symbol as SympySymbol, Integer, Float, Add, Mul, Pow, sin, cos, tan, exp, log, sqrt, sec, csc, cot, S, latex
from pydantic import BaseModel
from typing import Optional, List, Tuple, Dict

# Import the other modules
from derivative_ast import compute_derivative_ast
from derivative_dag import compute_derivative_dag
from derivative_nll import compute_derivative_nll
from generate_expression import generate_random_expression

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4000", "http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExpressionInput(BaseModel):
    expression: str
    variable: str = 'x'
    data_structure: str

class GenerationInput(BaseModel):
    num_terms: Optional[int] = 3
    max_depth: Optional[int] = 2
    variables: Optional[List[str]] = ['x', 'y']

# --- CUSTOM TOKENIZER AND PARSER ---

# Define token types
TOKEN_NUMBER = 'NUMBER'
TOKEN_SYMBOL = 'SYMBOL'
TOKEN_FUNCTION = 'FUNCTION'
TOKEN_OPERATOR = 'OPERATOR'
TOKEN_LPAREN = 'LPAREN'
TOKEN_RPAREN = 'RPAREN'
TOKEN_EOF = 'EOF' # End of file/expression

class Token:
    def __init__(self, type: str, value: str):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, '{self.value}')"

class Tokenizer:
    # Regex for tokens (order matters: longer matches first)
    TOKEN_SPECS = [
        (r'\d+\.?\d*|\.\d+', TOKEN_NUMBER),                         # Matches integers and floats
        (r'sin|cos|tan|exp|log|sqrt|sec|csc|cot', TOKEN_FUNCTION),  # Matches function names
        (r'[a-zA-Z_][a-zA-Z0-9_]*', TOKEN_SYMBOL),                  # Matches variables/symbols
        (r'\+', TOKEN_OPERATOR),
        (r'-', TOKEN_OPERATOR),
        (r'\*', TOKEN_OPERATOR),
        (r'/', TOKEN_OPERATOR),
        (r'\^', TOKEN_OPERATOR),                                    # Exponentiation operator
        (r'\(', TOKEN_LPAREN),
        (r'\)', TOKEN_RPAREN),
        (r'\s+', None), # Skip whitespace
    ]

    def __init__(self, expression_string: str):
        self.expression_string = expression_string
        self.position = 0
        self.tokens = self._tokenize()

    def _tokenize(self) -> List[Token]:
        tokens = []
        while self.position < len(self.expression_string):
            match_found = False
            for pattern, token_type in self.TOKEN_SPECS:
                regex = re.compile(pattern)
                match = regex.match(self.expression_string, self.position)
                if match:
                    if token_type is not None: # Not whitespace
                        tokens.append(Token(token_type, match.group(0)))
                    self.position = match.end(0)
                    match_found = True
                    break
            if not match_found:
                raise ValueError(f"Unexpected character at position {self.position}: {self.expression_string[self.position:]}")
        tokens.append(Token(TOKEN_EOF, '')) # Add EOF token
        return tokens

    def peek(self, offset=0) -> Token:
        if self.current_token_index + offset < len(self.tokens):
            return self.tokens[self.current_token_index + offset]
        return Token(TOKEN_EOF, '')

    def next(self) -> Token:
        if self.current_token_index < len(self.tokens):
            token = self.tokens[self.current_token_index]
            self.current_token_index += 1
            return token
        return Token(TOKEN_EOF, '') # Should not happen if parser checks for EOF

    def reset_cursor(self):
        self.current_token_index = 0

class Parser:
    def __init__(self, tokenizer: Tokenizer, custom_vars: Dict[str, SympySymbol]):
        self.tokenizer = tokenizer
        self.tokenizer.reset_cursor() # Ensure tokenizer starts from beginning
        self.custom_vars = custom_vars
        self.current_token = self.tokenizer.next()

        self.supported_sympy_functions = {
            "sqrt": sqrt, "sin": sin, "cos": cos, "tan": tan,
            "exp": exp, "log": log, "sec": sec, "csc": csc, "cot": cot
        }

    def _eat(self, token_type: str, token_value: Optional[str] = None):
        if self.current_token.type == token_type and \
           (token_value is None or self.current_token.value == token_value):
            self.current_token = self.tokenizer.next()
        else:
            raise ValueError(f"Expected {token_type}{f' ({token_value})' if token_value else ''}, "
                             f"got {self.current_token.type} ('{self.current_token.value}')")

    def parse(self):
        # Entry point for parsing
        result = self._expr()
        if self.current_token.type != TOKEN_EOF:
            raise ValueError(f"Unexpected token at end of expression: {self.current_token}")
        return result

    # Grammar rules (recursive descent) - highest precedence handled first (atom -> factor -> term -> expr)

    def _expr(self): # Handles Add/Subtract
        node = self._term()
        while self.current_token.type == TOKEN_OPERATOR and \
              self.current_token.value in ('+', '-'):
            op_token = self.current_token
            self._eat(TOKEN_OPERATOR, op_token.value)
            right_node = self._term()
            if op_token.value == '+':
                node = Add(node, right_node)
            else: # '-'
                node = Add(node, Mul(S.NegativeOne, right_node))
        return node

    def _term(self): # Handles Multiply/Divide
        node = self._factor()
        while self.current_token.type == TOKEN_OPERATOR and \
              self.current_token.value in ('*', '/'):
            op_token = self.current_token
            self._eat(TOKEN_OPERATOR, op_token.value)
            right_node = self._factor()
            if op_token.value == '*':
                node = Mul(node, right_node)
            else: # '/'
                node = Mul(node, Pow(right_node, S.NegativeOne))
        return node

    def _factor(self): # Handles Power
        node = self._atom()
        while self.current_token.type == TOKEN_OPERATOR and \
              self.current_token.value == '^':
            op_token = self.current_token
            self._eat(TOKEN_OPERATOR, '^')
            # Exponentiation is right-associative, so we parse atom for exponent
            right_node = self._factor() # Important: call _factor here for right-associativity
            node = Pow(node, right_node)
        return node

    def _atom(self): # Handles numbers, symbols, functions, parentheses, unary minus
        token = self.current_token

        if token.type == TOKEN_NUMBER:
            self._eat(TOKEN_NUMBER)
            if '.' in token.value:
                return Float(token.value)
            return Integer(token.value)
        
        elif token.type == TOKEN_SYMBOL:
            self._eat(TOKEN_SYMBOL)
            if token.value in self.custom_vars:
                return self.custom_vars[token.value]
            return SympySymbol(token.value) # Treat as a generic symbol

        elif token.type == TOKEN_FUNCTION:
            func_name = token.value
            self._eat(TOKEN_FUNCTION, func_name)
            self._eat(TOKEN_LPAREN)
            arg = self._expr()
            self._eat(TOKEN_RPAREN)
            if func_name in self.supported_sympy_functions:
                return self.supported_sympy_functions[func_name](arg)
            raise ValueError(f"Unsupported function: {func_name}")

        elif token.type == TOKEN_LPAREN:
            self._eat(TOKEN_LPAREN)
            node = self._expr()
            self._eat(TOKEN_RPAREN)
            return node
        
        elif token.type == TOKEN_OPERATOR and token.value == '-':
            # Handle unary minus (e.g., -x, -5)
            self._eat(TOKEN_OPERATOR, '-')
            operand = self._factor() # Unary minus binds tightly
            return Mul(S.NegativeOne, operand)

        else:
            raise ValueError(f"Unexpected token: {token}")


def preprocess_expression(expr_str: str, var_str: str):
    """
    Parses a mathematical expression string into a SymPy expression tree using a custom tokenizer and parser.
    """
    try:
        tokenizer = Tokenizer(expr_str)
        
        custom_symbols = {var_str: SympySymbol(var_str)}
        
        parser = Parser(tokenizer, custom_symbols)
        sympy_expr = parser.parse()
        
        variable_symbol = custom_symbols[var_str]
        
        return sympy_expr, variable_symbol

    except ValueError as e:
        logger.error(f"Parsing Error for expression '{expr_str}': {e}")
        raise HTTPException(status_code=400, detail=f"Invalid mathematical expression: {e}")
    except Exception as e:
        logger.error(f"Unexpected preprocessing error for '{expr_str}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while processing the expression: {e}")

@app.post("/solve")
async def solve_derivative(input_data: ExpressionInput):
    logger.debug(f"Received solve request: Expression='{input_data.expression}', Var='{input_data.variable}', DS='{input_data.data_structure}'")
    try:
        sympy_expr, variable_symbol = preprocess_expression(input_data.expression, input_data.variable)
        logger.debug(f"Processed expression: {sympy_expr}, Variable: {variable_symbol}")

        result_data = None
        if input_data.data_structure == "AST":
            result_data = compute_derivative_ast(sympy_expr, variable_symbol)
        elif input_data.data_structure == "DAG":
            result_data = compute_derivative_dag(sympy_expr, variable_symbol)
        elif input_data.data_structure == "NLL":
            result_data = compute_derivative_nll(sympy_expr, variable_symbol)
        else:
            logger.error(f"Invalid data structure: {input_data.data_structure}")
            raise HTTPException(status_code=400, detail="Invalid data structure. Choose AST, DAG, or NLL.")

        if result_data:
            response = {
                "derivative_latex": result_data["derivative_latex"],
                "steps": result_data["steps"],
                "execution_time_ms": result_data["execution_time_ms"],
                "peak_memory_bytes": result_data["peak_memory_bytes"],
                "ast_node_count": result_data["ast_node_count"],
                "data_structure_used": input_data.data_structure
            }
            logger.debug(f"Computation successful. Time: {response['execution_time_ms']:.2f}ms, Memory: {response['peak_memory_bytes']} bytes.")
            return response
        else:
            raise HTTPException(status_code=500, detail="Error computing derivative.")

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error during solve: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

@app.post("/generate")
async def generate_expression_endpoint(input_data: GenerationInput):
    logger.debug(f"Received generate request with parameters: {input_data}")
    try:
        sympy_vars = [SympySymbol(v) for v in input_data.variables]
        generated_expr = generate_random_expression(
            sympy_vars,
            num_terms=input_data.num_terms,
            max_depth=input_data.max_depth
        )
        response = {
            "expression_string": str(generated_expr),
            "expression_latex": latex(generated_expr)
        }
        return response
    except Exception as e:
        logger.error(f"Error generating expression: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while generating the expression: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    from sympy import latex # latex is imported here for local testing/debugging purposes, not related to the API flow
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
