import logging
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

# Import the derivative computation and expression generation functions
# These are assumed to be separate files in the same directory.
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
    allow_origins=["http://localhost:4000", "http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for API ---
class ExpressionInput(BaseModel):
    expression: str
    variable: str = 'x'

class GenerationInput(BaseModel):
    num_terms: Optional[int] = 3
    max_depth: Optional[int] = 2
    variables: Optional[List[str]] = ['x']

# --- Streaming Generator for Benchmarking ---
async def benchmark_generator(expression: str, variable: str):
    """
    An asynchronous generator that runs the derivative computation benchmark
    for all data structures and streams progress and final results.
    """
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
                progress_percent = int((current_iteration / total_iterations) * 100)
                
                # Send a progress update to the client
                progress_message = {
                    'type': 'progress', 
                    'progress': progress_percent,
                    'current_task': f"Running {ds} benchmark {i+1}/{total_runs}"
                }
                yield f"data: {json.dumps(progress_message)}\n\n"
                
                # Retrieve the correct derivative computation function
                compute_func = {
                    'AST': compute_derivative_ast,
                    'DAG': compute_derivative_dag,
                    'NLL': compute_derivative_nll
                }.get(ds)
                
                if not compute_func:
                    raise ValueError(f"Invalid data structure: {ds}")
                
                # Execute the computation
                result_data = compute_func(expression, variable)
                
                # Collect data after warmup runs
                if i >= warmup_runs:
                    times.append(result_data['execution_time_ms'])
                    memories.append(result_data['peak_memory_bytes'])
                    
                    # Capture the derivative and steps from the first measured run
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
                # Handle case where measured_runs is 0 (e.g., if total_runs <= warmup_runs)
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
