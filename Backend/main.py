# main.py
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sympy import symbols, sympify, latex, SympifyError, Symbol as SympySymbol 
from pydantic import BaseModel

# Import the AST derivative computation function
from derivative_ast import compute_derivative_ast 

# (Placeholders for DAG and NLL would be similar but with their own compute functions)
# from derivative_dag import compute_derivative_dag 
# from derivative_nll import compute_derivative_nll 

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4000", "http://localhost:5173"], # Adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExpressionInput(BaseModel):
    expression: str
    variable: str = 'x'  # Default variable, can be specified by client
    data_structure: str

def preprocess_expression(expr_str: str, var_str: str):
    try:
        custom_symbols = {var_str: SympySymbol(var_str)}
        common_syms = {s: SympySymbol(s) for s in ['y', 'z', 'a', 'b', 'c', 'n', 'k']}
        all_locals = {**common_syms, **custom_symbols}

        processed_expr_str = expr_str.replace('^', '**')
        
        from sympy import sqrt, sin, cos, tan, exp, log 
        function_locals = {"sqrt": sqrt, "sin": sin, "cos": cos, "tan": tan, "exp": exp, "log": log}
        all_locals.update(function_locals)
        
        sympy_expr = sympify(processed_expr_str, locals=all_locals)
        variable_symbol = all_locals[var_str]
        
        return sympy_expr, variable_symbol
    except SympifyError as e:
        logger.error(f"SympifyError for expression '{expr_str}': {e}")
        raise ValueError(f"Invalid mathematical expression: {e}")
    except KeyError as e:
        logger.error(f"KeyError during preprocessing, variable '{var_str}' might be missing: {e}")
        raise ValueError(f"Invalid variable specified or used in expression: {var_str}")
    except Exception as e:
        logger.error(f"Preprocessing error for expression '{expr_str}': {e}")
        raise ValueError(f"Error preprocessing expression: {str(e)}")

@app.post("/solve")
async def solve_derivative(input_data: ExpressionInput):
    logger.debug(f"Received solve request: Expression='{input_data.expression}', Var='{input_data.variable}', DS='{input_data.data_structure}'")
    try:
        sympy_expr, variable_symbol = preprocess_expression(input_data.expression, input_data.variable)
        logger.debug(f"Processed expression: {sympy_expr}, Variable: {variable_symbol}")

        result_data = None
        if input_data.data_structure == "AST":
            result_data = compute_derivative_ast(sympy_expr, variable_symbol)
        # elif input_data.data_structure == "DAG":
        #     # result_data = compute_derivative_dag(sympy_expr, variable_symbol)
        #     raise HTTPException(status_code=501, detail="DAG method not fully implemented for detailed data collection.")
        # elif input_data.data_structure == "NLL":
        #     # result_data = compute_derivative_nll(sympy_expr, variable_symbol)
        #     raise HTTPException(status_code=501, detail="NLL method not fully implemented for detailed data collection.")
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
            raise HTTPException(status_code=500, detail="Error computing derivative or data structure not fully implemented.")

    except ValueError as ve:
        logger.error(f"ValueError during solve: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as he:
        raise he 
    except Exception as e:
        logger.error(f"Unexpected error during solve: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)