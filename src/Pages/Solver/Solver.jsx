// Solver.jsx
import React from 'react';
import { MathJaxContext } from "better-react-mathjax";
import Navbar from '../../Components/Navbar';
import Bottomcontent from '../../Components/Bottomcontent';
import InputField from './InputField';
import SolverConfig from './SolverConfig';
import SolutionDisplay from './SolutionDisplay';
import StepByStep from './StepByStep';
import MeasurementDisplay from './MeasurementDisplay.jsx';

const Solver = () => {
    // State for user input, expression, and configuration
    const [input, setInput] = React.useState('sin(x^2) + cos(x)');
    const [derivative, setDerivative] = React.useState('');
    const [dataStructure, setDataStructure] = React.useState('AST');
    const [variable, setVariable] = React.useState('x');
    const [numTerms, setNumTerms] = React.useState(3);
    const [maxDepth, setMaxDepth] = React.useState(2);
    const [errorMessage, setErrorMessage] = React.useState('');
    const [isLoading, setIsLoading] = React.useState(false);
    
    // State for tracking benchmark progress
    const [progress, setProgress] = React.useState(0);

    // State to store results from all data structures
    const [results, setResults] = React.useState({
        AST: { derivative: '', steps: [], avgTime: null, avgMemory: null },
        DAG: { derivative: '', steps: [], avgTime: null, avgMemory: null },
        NLL: { derivative: '', steps: [], avgTime: null, avgMemory: null }
    });

    const handleInputChange = (e) => setInput(e.target.value);

    /**
     * Inserts a mathematical symbol into the input field at the cursor's position.
     * @param {string} symbol - The symbol or function to insert.
     */
    const insertSymbol = (symbol) => {
        const inputField = document.getElementById('equation-input');
        if (!inputField) return;
        const { selectionStart, selectionEnd } = inputField;
        const newValue = input.substring(0, selectionStart) + symbol + input.substring(selectionEnd);
        setInput(newValue);
        inputField.focus();
        // Move cursor to the end of the inserted symbol
        const newCursorPosition = selectionStart + symbol.length;
        inputField.setSelectionRange(newCursorPosition, newCursorPosition);
    };

    /**
     * Solves the expression by sending it to the backend.
     * It runs the computation for all data structures (AST, DAG, NLL)
     * and averages the performance metrics over several runs to get a stable measurement.
     */
    const solveExpression = async () => {
        if (!input.trim()) {
            setErrorMessage("Please enter a function to solve.");
            return;
        }
        setIsLoading(true);
        setErrorMessage('');
        setProgress(0); // Reset progress bar

        const dataStructures = ['AST', 'DAG', 'NLL'];
        const newResults = {};
        const totalRuns = 15;
        const warmupRuns = 5;
        const measuredRuns = totalRuns - warmupRuns;

        try {
            for (const ds of dataStructures) {
                let times = [], memories = [], derivative = '', steps = [];
                for (let i = 0; i < totalRuns; i++) {
                    const resp = await fetch("http://127.0.0.1:8000/solve", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            expression: input,
                            data_structure: ds,
                            variable
                        })
                    });
                    const data = await resp.json();
                    if (!resp.ok) throw new Error(data.detail || "An error occurred in the backend.");

                    // Update progress after each successful run
                    setProgress(prev => prev + 1);

                    // Discard warmup runs and collect data from measured runs
                    if (i >= warmupRuns) {
                        times.push(data.execution_time_ms);
                        memories.push(data.peak_memory_bytes);
                        // Capture the derivative and steps from the first measured run
                        if (i === warmupRuns) {
                            derivative = data.derivative_latex; 
                            steps = data.steps || [];
                        }
                    }
                }
                const avgTime = times.reduce((a, b) => a + b, 0) / measuredRuns;
                const avgMemory = memories.reduce((a, b) => a + b, 0) / measuredRuns;
                newResults[ds] = { derivative, steps, avgTime, avgMemory };
                setDerivative(derivative); // Update the main derivative display
            }
            setResults(newResults);
        } catch (error) {
            console.error("Error in solveExpression:", error);
            setErrorMessage(`Error: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    /**
     * Converts a Python-style expression (e.g., x**2) to a more standard format (e.g., x^2).
     * @param {string} expr - The Python expression string.
     * @returns {string} The converted expression string.
     */
    const convertPythonExpToCaret = (expr) => {
        let converted = expr.replace(/exp/g, 'e^');
        converted = converted.replace(
            /([a-zA-Z0-9_.]+|\([^)]+\))\*\*([a-zA-Z0-9_.]+|\w+\(.*?\)|\(.*?\)|\S+)/g,
            (match, base, exponent) => {
                // Add parentheses if the exponent is complex
                if ((exponent.startsWith('(') && exponent.endsWith(')')) || exponent.match(/^[a-zA-Z0-9_.]+$/))
                    return `${base}^${exponent}`;
                return `${base}^(${exponent})`;
            }
        );
        return converted;
    }

    /**
     * Fetches a randomly generated mathematical expression from the backend.
     */
    const generateExpression = async () => {
        setErrorMessage('');
        try {
            const response = await fetch("http://127.0.0.1:8000/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    num_terms: numTerms,
                    max_depth: maxDepth,
                    variables: [variable]
                }),
            });
            const data = await response.json();

            if (!response.ok) {
                console.error("Generate error:", data);
                setErrorMessage(data.detail || "Failed to generate expression.");
                return;
            }
            
            const converted = convertPythonExpToCaret(data.expression_string);
            setInput(converted);
            setDerivative(''); // Clear previous results
        } catch (error) {
            console.error("Error in generateExpression:", error);
            setErrorMessage(`Error generating expression: ${error.message}`);
        }
    };

    /**
     * Clears the input field and any previous results or errors.
     */
    const clearInput = () => {
        setInput('');
        setDerivative('');
        setErrorMessage('');
        setResults({
             AST: { derivative: '', steps: [], avgTime: null, avgMemory: null },
             DAG: { derivative: '', steps: [], avgTime: null, avgMemory: null },
             NLL: { derivative: '', steps: [], avgTime: null, avgMemory: null }
        });
    };

    return (
        <div className="bg-bgcolor min-h-screen w-full flex flex-col">
            <Navbar /> 
            <h1 className="font-bold text-2xl text-dark text-center mt-10 mb-4">Derivative Solver</h1>
            <main className="flex flex-col md:flex-row gap-8 p-6 w-full lg:w-2/3 justify-center mx-auto">
                <div className="w-full md:w-1/3">
                    <InputField
                        input={input}
                        handleInputChange={handleInputChange}
                        setInput={setInput}
                        solveExpression={solveExpression}
                        insertSymbol={insertSymbol}
                        clearInput={clearInput}
                        generateExpression={generateExpression}
                    />
                    <SolverConfig
                        displayedDataStructure={dataStructure}
                        setDisplayedDataStructure={setDataStructure}
                        numTerms={numTerms}
                        setNumTerms={setNumTerms}
                        maxDepth={maxDepth}
                        setMaxDepth={setMaxDepth}
                        variable={variable}
                        setVariable={setVariable}
                        isLoading={isLoading}
                        hasResults={!!derivative}
                    />
                </div>
                <div className="w-full md:w-2/3">
                    <SolutionDisplay derivative={derivative} error={errorMessage} />
                    <MeasurementDisplay results={results} isLoading={isLoading} progress={progress} />
                    <StepByStep steps={results[dataStructure]?.steps || []} />
                </div>
            </main>
            <Bottomcontent />
        </div>
    );
};