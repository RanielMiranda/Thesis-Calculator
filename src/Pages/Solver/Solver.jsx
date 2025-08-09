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
    const [derivativeSteps, setDerivativeSteps] = useState([]);
    const [executionTime, setExecutionTime] = useState(null);
    const [peakMemory, setPeakMemory] = useState(null);
    const [dataStructure, setDataStructure] = useState('AST');
    const [variable, setVariable] = useState('x');
    const [numTerms, setNumTerms] = useState(3);
    const [maxDepth, setMaxDepth] = useState(2);
    const [errorMessage, setErrorMessage] = useState('');

    const handleInputChange = (e) => {
        setInput(e.target.value);
    };

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

        let formattedText = text;

        // 1. Escape LaTeX special characters (backslashes first)
        formattedText = formattedText.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '\\_');

        // 2. Handle double-asterisk for exponents (Python-style)
        formattedText = formattedText.replace(/\*\*/g, '^{');

        // 3. Handle functions and their arguments - these should generally come before general exponent/fraction handling
        // Ensures arguments are wrapped in {}
        formattedText = formattedText.replace(/sin\((.*?)\)/g, '\\sin{$1}');
        formattedText = formattedText.replace(/cos\((.*?)\)/g, '\\cos{$1}');
        formattedText = formattedText.replace(/tan\((.*?)\)/g, '\\tan{$1}');
        formattedText = formattedText.replace(/log\((.*?)\)/g, '\\log{$1}');
        formattedText = formattedText.replace(/ln\((.*?)\)/g, '\\ln{$1}');
        formattedText = formattedText.replace(/exp\((.*?)\)/g, 'e^{$1}');
        formattedText = formattedText.replace(/abs\((.*?)\)/g, '\\left|$1\\right|');
        formattedText = formattedText.replace(/sqrt\((.*?)\)/g, '\\sqrt{$1}');
        
        // 4. Handle general single-caret exponents (x^2, x^(a+b))
        // This regex looks for '^' followed by a single alphanumeric character or a parenthesized expression.
        formattedText = formattedText.replace(/\^([a-zA-Z0-9_])(?!\w)/g, '^{$1}'); // For single char like x^2
        formattedText = formattedText.replace(/\^\((.*?)\)/g, '^{$1}'); // For x^(expr)

        // 5. Handle fractions (u/v)
        // This attempts to capture either simple terms (words/numbers) or parenthesized expressions
        // and format them as \frac{}{}
        formattedText = formattedText.replace(/(\w+|\([^)]+\))\s*\/\s*(\w+|\([^)]+\))/g, '\\frac{$1}{$2}');
        // For cases like "num/(den)" or "(num)/den" that the above might miss if only one side is parenthesized
        formattedText = formattedText.replace(/(.*?)\s*\/\s*\((.*?)\)/g, '\\frac{$1}{$2}'); // Handles (num)/den
        formattedText = formattedText.replace(/\((.*?)\)\s*\/\s*(.*)/g, '\\frac{$1}{$2}'); // Handles num/(den)

        // 6. Replace other operators
        formattedText = formattedText.replace(/\*/g, '\\cdot ');

        // 7. Handle constants
        formattedText = formattedText.replace(/pi/g, '\\pi');

        return formattedText;
    };

    const solveExpression = async () => {
        setErrorMessage('');
        if (!input.trim()) {
            setErrorMessage("Please enter a function to solve.");
            return;
        }

        try {
            const solveResponse = await fetch("http://127.00.1:8000/solve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    expression: input,
                    data_structure: dataStructure,
                    variable: variable
                }),
            });

            const solveData = await solveResponse.json();

            if (!solveResponse.ok) {
                console.error("Solver Error Response:", solveData);
                setErrorMessage(solveData.detail || "Failed to fetch derivative from backend.");
                return;
            }
            
            console.log("Received from backend:", solveData);
            setDerivative(solveData.derivative_latex);
            setDerivativeSteps(solveData.steps || []);
            setExecutionTime(solveData.execution_time_ms);
            setPeakMemory(solveData.peak_memory_bytes);

        } catch (error) {
            console.error("Error in solveExpression:", error);
            setErrorMessage(`Error processing the expression: ${error.message}`);
            setDerivative('');
            setDerivativeSteps([]);
            setExecutionTime(null);
            setPeakMemory(null);
        }
    };
    
    const convertPythonExpToCaret = (expression) => {
        let converted = expression.replace(/exp/g, 'e^'); // Convert 'exp' to 'e^'


        converted = converted.replace(
            /([a-zA-Z0-9_.]+|\([^)]+\))\*\*([a-zA-Z0-9_.]+|\w+\(.*?\)|\(.*?\)|\S+)/g,
            (match, base, exponent) => {
                if ((exponent.startsWith('(') && exponent.endsWith(')')) || exponent.match(/^[a-zA-Z0-9_.]+$/)) {
                    return `${base}^${exponent}`;
                } 
                else {
                    return `${base}^(${exponent})`;
                }
            }
        );
        return converted;
    };

    const generateExpression = async () => {
        setErrorMessage('');
        try {
            // Note: Replace with your actual backend URL if different
            const generateResponse = await fetch("http://127.0.0.1:8000/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    num_terms: numTerms,
                    max_depth: maxDepth,
                    variables: [variable]
                }),
            });

            const generateData = await generateResponse.json();

            if (!generateResponse.ok) {
                console.error("Generate Error Response:", generateData);
                setErrorMessage(generateData.detail || "Failed to generate expression.");
                return;
            }

            console.log("Generated expression:", generateData);
            const convertedExpression = convertPythonExpToCaret(generateData.expression_string);
            setInput(convertedExpression); 
            setDerivative('');
            setDerivativeSteps([]);
            setExecutionTime(null);
            setPeakMemory(null);

        } catch (error) {
            console.error("Error in generateExpression:", error);
            setErrorMessage(`Error generating expression: ${error.message}. Make sure your backend server is running and accessible.`);
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
                            dataStructure={dataStructure} 
                            setDataStructure={setDataStructure} 
                            numTerms={numTerms}
                            setNumTerms={setNumTerms}
                            maxDepth={maxDepth}
                            setMaxDepth={setMaxDepth}
                            variable={variable}
                            setVariable={setVariable}
                        />
                    </div>

                    <div className="w-full md:w-2/3">
                        <SolutionDisplay derivative={derivative} error={errorMessage} />
                        <div>
                            <MeasurementDisplay dataStructure={dataStructure} executionTime={executionTime} peakMemory={peakMemory} />
                        </div>
                        <StepByStep steps={derivativeSteps} />
                    </div>
                </div>

                <Bottomcontent />
            </div>
        </MathJaxContext>
    );
};

export default Solver;
