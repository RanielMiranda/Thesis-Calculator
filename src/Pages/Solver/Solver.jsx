import React, { useState } from 'react';
import { MathJaxContext } from "better-react-mathjax";
import Navbar from '../../Components/Navbar';
import Bottomcontent from '../../Components/Bottomcontent';
import InputField from './InputField';
import SolverConfig from './SolverConfig';
import SolutionDisplay from './SolutionDisplay';
import StepByStep from './StepByStep';
import MeasurementDisplay from './MeasurementDisplay.jsx';

const Solver = () => {
    const [input, setInput] = useState('');
    const [derivative, setDerivative] = useState('');
    const [dataStructure, setDataStructure] = useState('AST');
    const [variable, setVariable] = useState('x');
    const [numTerms, setNumTerms] = useState(3);
    const [maxDepth, setMaxDepth] = useState(2);
    const [errorMessage, setErrorMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);    

    const [results, setResults] = useState({
        AST: { derivative: '', steps: [], avgTime: null, avgMemory: null },
        DAG: { derivative: '', steps: [], avgTime: null, avgMemory: null },
        NLL: { derivative: '', steps: [], avgTime: null, avgMemory: null }
    });

    const handleInputChange = (e) => setInput(e.target.value);

    const insertSymbol = (symbol) => {
        const inputField = document.getElementById('equation-input');
        const start = inputField.selectionStart;
        const end = inputField.selectionEnd;
        const newValue = input.substring(0, start) + symbol + input.substring(end);
        setInput(newValue);
        inputField.focus();
        inputField.setSelectionRange(start + symbol.length, start + symbol.length);
    };

    const formatForMathJax = (text) => {
        if (!text) return '';
        let formattedText = text.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '\\_');
        formattedText = formattedText.replace(/\*\*/g, '^{');
        formattedText = formattedText.replace(/sin\((.*?)\)/g, '\\sin{$1}');
        formattedText = formattedText.replace(/cos\((.*?)\)/g, '\\cos{$1}');
        formattedText = formattedText.replace(/tan\((.*?)\)/g, '\\tan{$1}');
        formattedText = formattedText.replace(/log\((.*?)\)/g, '\\log{$1}');
        formattedText = formattedText.replace(/ln\((.*?)\)/g, '\\ln{$1}');
        formattedText = formattedText.replace(/exp\((.*?)\)/g, 'e^{$1}');
        formattedText = formattedText.replace(/\^([a-zA-Z0-9_])(?!\w)/g, '^{$1}');
        formattedText = formattedText.replace(/\^\((.*?)\)/g, '^{$1}');
        formattedText = formattedText.replace(/(\w+|\([^)]+\))\s*\/\s*(\w+|\([^)]+\))/g, '\\frac{$1}{$2}');
        formattedText = formattedText.replace(/\*/g, '\\cdot ');
        formattedText = formattedText.replace(/pi/g, '\\pi');
        return formattedText;
    };

    const solveExpression = async () => {
        if (!input.trim()) {
            setErrorMessage("Please enter a function to solve.");
            return;
        }
        setIsLoading(true);
        setErrorMessage('');

        const dataStructures = ['AST', 'DAG', 'NLL'];
        const newResults = {};

        try {
            for (const ds of dataStructures) {
                let times = [], memories = [], derivative = '', steps = [];
                for (let i = 0; i < 15; i++) {
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
                    if (!resp.ok) throw new Error(data.detail || "Backend error");

                    // Warm-up = first 5; collect only the last 10 for averaging
                    if (i >= 5) {
                        times.push(data.execution_time_ms);
                        memories.push(data.peak_memory_bytes);
                        if (i === 5) {
                            derivative = data.derivative_latex; 
                            steps = data.steps || [];
                        }
                    }
                }
                const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
                const avgMemory = memories.reduce((a, b) => a + b, 0) / memories.length;
                newResults[ds] = { derivative, steps, avgTime, avgMemory };
                setDerivative(derivative);              
            }
            setResults(newResults);
        } catch (error) {
            console.error("Error in solveExpression:", error);
            setErrorMessage(`Error: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    const convertPythonExpToCaret = (expr) => {
        let converted = expr.replace(/exp/g, 'e^');
        converted = converted.replace(
            /([a-zA-Z0-9_.]+|\([^)]+\))\*\*([a-zA-Z0-9_.]+|\w+\(.*?\)|\(.*?\)|\S+)/g,
            (match, base, exponent) => {
                if ((exponent.startsWith('(') && exponent.endsWith(')')) || exponent.match(/^[a-zA-Z0-9_.]+$/))
                    return `${base}^${exponent}`;
                return `${base}^(${exponent})`;
            }
        );
        return converted;
    }

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

            console.log("Generated expression:", data);
            
            const converted = convertPythonExpToCaret(data.expression_string);
            setInput(converted);
            setDerivative('');
            setDerivativeSteps([]);
            setExecutionTime(null);
            setPeakMemory(null);
        } catch (error) {
            console.error("Error in generateExpression:", error);
            setErrorMessage(`Error generating expression: ${error.message}`);
        }
    };

    const clearInput = () => {
        setInput('');
        setDerivative('');
        setDerivativeSteps([]);
        setExecutionTime(null);
        setPeakMemory(null);
        setErrorMessage('');
    };

    return (
        <MathJaxContext>
            <div className="bg-bgcolor min-h-screen w-full flex flex-col">
                <Navbar />
                <h1 className="font-bold text-2xl text-dark text-center mt-10 mb-4">Derivative Solver</h1>
                <div className="flex flex-col md:flex-row gap-8 p-6 w-full lg:w-2/3 justify-center mx-auto">
                    <div className="w-full md:w-1/3">
                        <InputField
                            input={input}
                            handleInputChange={handleInputChange}
                            setInput={setInput}
                            solveExpression={solveExpression}
                            insertSymbol={insertSymbol}
                            formatForMathJax={formatForMathJax}
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
                        <MeasurementDisplay results={results} isLoading={isLoading} />
                        <StepByStep steps={results[dataStructure].steps} />
                    </div>
                </div>
                <Bottomcontent />
            </div>
        </MathJaxContext>
    );
};

export default Solver;
