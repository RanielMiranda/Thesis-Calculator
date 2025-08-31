import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

# Import the derivative computation and expression generation functions
from derivative_ast import compute_derivative_ast
from derivative_dag import compute_derivative_dag
from derivative_nll import compute_derivative_nll
from generate_expression import generate_random_expression

# --- Basic Setup ---
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4000", "http://localhost:5173"], # Adjust if your frontend runs elsewhere
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for API ---
class ExpressionInput(BaseModel):
    expression: str
    variable: str = 'x'
    data_structure: str

class GenerationInput(BaseModel):
    num_terms: Optional[int] = 3
    max_depth: Optional[int] = 2
    variables: Optional[List[str]] = ['x']

# --- API Endpoints ---

@app.post("/solve")
async def solve_derivative(input_data: ExpressionInput):
    """
    Receives an expression, variable, and data structure type,
    and returns the step-by-step derivative.
    """
    logger.debug(f"Received solve request: Expression='{input_data.expression}', Var='{input_data.variable}', DS='{input_data.data_structure}'")
    try:
        result_data = None
        if input_data.data_structure == "AST":
            result_data = compute_derivative_ast(input_data.expression, input_data.variable)
        elif input_data.data_structure == "DAG":
            result_data = compute_derivative_dag(input_data.expression, input_data.variable)
        elif input_data.data_structure == "NLL":
            result_data = compute_derivative_nll(input_data.expression, input_data.variable)
        else:
            logger.error(f"Invalid data structure: {input_data.data_structure}")
            raise HTTPException(status_code=400, detail="Invalid data structure. Choose from: AST, DAG, or NLL.")

        if result_data:
            logger.debug(f"Computation successful. Time: {result_data['execution_time_ms']:.2f}ms, Memory: {result_data['peak_memory_bytes']} bytes.")
            return result_data
        else:
            raise HTTPException(status_code=500, detail="Error computing derivative.")

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error during solve: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

@app.post("/generate")
async def generate_expression_endpoint(input_data: GenerationInput):
    """
    Generates a random mathematical expression based on specified parameters.
    """
    logger.debug(f"Received generate request with parameters: {input_data}")
    try:
        expression_str, expression_latex = generate_random_expression(
            num_terms=input_data.num_terms,
            max_depth=input_data.max_depth,
            variables=input_data.variables
        )
        response = {
            "expression_string": expression_str,
            "expression_latex": expression_latex
        }
        return response
    except Exception as e:
        logger.error(f"Error generating expression: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred while generating the expression: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
