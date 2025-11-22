import logging
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from sympy import symbols, latex, sympify
from sympy.core.sympify import SympifyError

# Derivative computation and expression generation functions
# (Assuming these files exist in your project structure)
from Structures.derivative_ast import compute_derivative_ast
from Structures.derivative_dag import compute_derivative_dag
from Structures.derivative_nll import compute_derivative_nll
from generate_expression import generate_random_expression

# --- Basic Setup ---
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4000", "http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Validation Helper ---
def is_valid_expression(expression: str):
    """
    Validates the math expression using SymPy's parser.
    Returns (True, None) if valid.
    Returns (False, Error Message) if invalid.
    """
    if not expression or not expression.strip():
        return False, "Expression cannot be empty."

    try:
        sympify(expression, evaluate=False)
        return True, None
    except (SympifyError, SyntaxError, TypeError, ValueError):
        return False, "Invalid mathematical syntax. Please check for adjacent operators or unbalanced parentheses."

# --- Pydantic Models ---
class ExpressionInput(BaseModel):
    expression: str
    variable: str = 'x'

class GenerationInput(BaseModel):
    num_terms: Optional[int] = 3
    max_depth: Optional[int] = 2
    variables: Optional[List[str]] = ['x']

# --- Streaming Generator ---
async def benchmark_generator(expression: str, variable: str):
    
    # 1. IMMEDIATE VALIDATION
    is_valid, error_msg = is_valid_expression(expression)
    if not is_valid:
        error_response = {
            'type': 'error',
            'detail': error_msg
        }
        yield f"data: {json.dumps(error_response)}\n\n"
        return # STOP execution here.

    data_structures = ['AST', 'DAG', 'NLL']
    total_runs = 30
    warmup_runs = 10
    measured_runs = total_runs - warmup_runs
    
    total_iterations = len(data_structures) * total_runs
    current_iteration = 0
    
    final_results = {
        ds: {'derivative': None, 'steps': [], 'avgTime': None, 'avgMemory': None} 
        for ds in data_structures
    }

    try:
        for ds in data_structures:
            times = []
            memories = []
            derivative_latex = ''
            steps = []
            
            for i in range(total_runs):
                current_iteration += 1
                
                # Retrieve the correct derivative computation function
                compute_func = {
                    'AST': compute_derivative_ast,
                    'DAG': compute_derivative_dag,
                    'NLL': compute_derivative_nll
                }.get(ds)
                
                if not compute_func:
                    raise ValueError(f"Invalid data structure: {ds}")
                
                # --- Error Handling during computation ---
                try:
                    result_data = compute_func(expression, variable)

                # 1. Catch "Not Implemented" errors (Rules outside scope)
                except NotImplementedError as nie:
                    logger.warning(f"Scope limitation in {ds}: {str(nie)}")
                    error_payload = {
                        'type': 'error',
                        'detail': f"Limit reached in {ds} structure: {str(nie)} (This rule is outside the current scope)"
                    }
                    yield f"data: {json.dumps(error_payload)}\n\n"
                    return 

                # 2. Catch General Calculation errors
                except Exception as calc_error:
                    logger.error(f"Calculation failed in {ds}: {str(calc_error)}")
                    error_payload = {
                        'type': 'error', 
                        'detail': f"Calculation error in {ds} structure: {str(calc_error)}"
                    }
                    yield f"data: {json.dumps(error_payload)}\n\n"
                    return

                # Collect data after warmup runs
                if i >= warmup_runs:
                    times.append(result_data['execution_time_ms'])
                    memories.append(result_data['peak_memory_bytes'])
                    
                    if i == warmup_runs:
                        derivative_latex = result_data.get('derivative_latex', '')
                        steps = result_data.get('steps', [])
                        
            # Calculate averages for the current data structure
            if measured_runs > 0:
                avg_time = sum(times) / measured_runs
                avg_memory = sum(memories) / measured_runs
                final_results[ds] = {
                    'derivative': derivative_latex,
                    'steps': steps,
                    'avgTime': avg_time,
                    'avgMemory': avg_memory
                }
            else:
                final_results[ds] = {
                    'derivative': derivative_latex,
                    'steps': steps,
                    'avgTime': 0,
                    'avgMemory': 0
                }

        # Send the final complete results
        final_message = {
            'type': 'complete',
            'results': final_results
        }
        yield f"data: {json.dumps(final_message)}\n\n"

    except Exception as e:
        logger.error(f"Unexpected error during benchmark: {str(e)}", exc_info=True)
        # This catches anything else (server logic errors)
        error_message = {'type': 'error', 'detail': f"An unexpected server error occurred: {str(e)}"}
        yield f"data: {json.dumps(error_message)}\n\n"


# --- API Endpoints ---
@app.get("/solve_stream")
async def solve_derivative_stream(expression: str, variable: str = 'x'):
    logger.debug(f"Received streaming solve request for Expression='{expression}', Var='{variable}'")
    return StreamingResponse(
        benchmark_generator(expression, variable),
        media_type="text/event-stream"
    )

@app.post("/generate")
async def generate_expression_endpoint(input_data: GenerationInput):
    # ... (Your existing generate code remains the same) ...
    logger.debug(f"Received generate request with parameters: {input_data}")
    try:
        sym_variables = symbols(input_data.variables)
        expression = generate_random_expression(
            variables=sym_variables,
            num_terms=input_data.num_terms,
            max_depth=input_data.max_depth,
        )
        expression_str = str(expression)
        expression_latex = latex(expression)
        response = {
            "expression_string": expression_str,
            "expression_latex": expression_latex
        }
        return response
    except Exception as e:
        logger.error(f"Error generating expression: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")