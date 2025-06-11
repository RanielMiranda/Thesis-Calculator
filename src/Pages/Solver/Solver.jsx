// Solver.jsx
import React, { useState } from 'react';
import { MathJaxContext } from "better-react-mathjax"; // MathJax already here
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
  const [derivativeSteps, setDerivativeSteps] = useState([]); // This is passed to StepByStep
  const [executionTime, setExecutionTime] = useState(null);
  const [peakMemory, setPeakMemory] = useState(null);
  const [dataStructure, setDataStructure] = useState('');

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
  
  /**
   * Converts a mathematical string expression into a LaTeX format suitable for MathJax display.
   * This function attempts to handle common functions, operators, and some nesting.
   */
  const formatForMathJax = (text) => {
    if (!text) return ''; // Handle empty or undefined input

    let formattedText = text;

    // 1. Escape LaTeX special characters that might appear in raw input
    formattedText = formattedText
      .replace(/\\/g, '\\\\') // Escape backslashes
      .replace(/%/g, '\\%')   // Escape percent signs
      .replace(/_/g, '\\_');   // Escape underscores

    // 2. Convert common function names to LaTeX commands with braces for arguments
    // Use non-greedy quantifiers and lookarounds where appropriate for better matching
    formattedText = formattedText
      .replace(/sin\((.*?)\)/g, '\\sin{$1}')
      .replace(/cos\((.*?)\)/g, '\\cos{$1}')
      .replace(/tan\((.*?)\)/g, '\\tan{$1}')
      .replace(/log\((.*?)\)/g, '\\log{$1}')
      .replace(/ln\((.*?)\)/g, '\\ln{$1}')
      .replace(/exp\((.*?)\)/g, 'e^{$1}') // Convert exp(x) to e^{x}
      .replace(/abs\((.*?)\)/g, '\\left|$1\\right|') // Absolute value
      .replace(/sqrt\((.*?)\)/g, '\\sqrt{$1}') // Square root handling

    // 3. Handle specific operators
    // Power rule: x^y, x^(y+z). Use braces for exponent if it's more than a single char/digit.
    // This is order sensitive! Handle complex powers before simple ones.
    formattedText = formattedText
      .replace(/\^(\(|\w+)/g, '^{$1}') // x^(y+z) -> x^{y+z}, x^y -> x^{y}
      .replace(/\)\^{/g, ')^{'); // Fix for (f(x))^{g(x)} when it becomes (f(x))^{\{g(x)\}} due to earlier replacements

    // Division: Prefer \frac for clarity, trying to match balanced parentheses for numerator/denominator
    // This is the trickiest part for regex with arbitrary nesting.
    // A simplified approach that works for common cases:
    formattedText = formattedText
      .replace(/([^()]+)\/([^()]+)/g, '\\frac{$1}{$2}'); // simple a/b
    // To handle (A+B)/(C+D), (cos(x^2))/sin(x) etc. regex needs to be more complex (and sometimes impossible reliably without parsing).
    // The following is a very basic attempt to handle expressions in parentheses before/after a slash.
    // For `(cos(x^2))/sin(x)`:
    formattedText = formattedText.replace(/\((.*?)\)\s*\/\s*(.*)/g, '\\frac{$1}{$2}'); // (numerator)/denominator
    formattedText = formattedText.replace(/(.*)\s*\/\s*\((.*?)\)/g, '\\frac{$1}{$2}'); // numerator/(denominator)

    // Multiplication: a*b -> a \cdot b
    formattedText = formattedText.replace(/\*/g, '\\cdot ');

    // 4. Constants
    formattedText = formattedText.replace(/pi/g, '\\pi');

    return formattedText;
  };

  const solveExpression = async () => {
    if (!input.trim()) {
      alert("Please enter a function to solve.");
      return;
    }
    const parsedInput = input;
    
    const dataStructureElement = document.querySelector('select[name="option"]');
    if (!dataStructureElement) {
        alert("Could not find data structure selector. Please ensure it's rendered.");
        return;
    }
    const currentDataStructure = dataStructureElement.value;
    setDataStructure(currentDataStructure);

    console.log("Sending to backend:", { expression: parsedInput, data_structure: currentDataStructure });

    try {
      const solveResponse = await fetch("http://127.0.0.1:8000/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expression: parsedInput, data_structure: currentDataStructure }),
      });

      const solveData = await solveResponse.json(); // Try to parse JSON regardless of ok status first for error messages

      if (!solveResponse.ok) {
        console.error("Solver Error Response:", solveData);
        throw new Error(solveData.detail || "Failed to fetch derivative from backend.");
      }
      
      console.log("Received from backend:", solveData);
      setDerivative(solveData.derivative_latex); // Expecting LaTeX string
      setDerivativeSteps(solveData.steps || []); // Expecting an array of step objects
      setExecutionTime(solveData.execution_time_ms);
      setPeakMemory(solveData.peak_memory_bytes);

    } catch (error) {
      console.error("Error in solveExpression:", error);
      alert(`Error processing the expression: ${error.message}`);
      setDerivative(''); // Clear previous results on error
      setDerivativeSteps([]); // Clear previous steps on error
      setExecutionTime(null);
      setPeakMemory(null);
    }
  };

   const generateExpression = () => { /* ... */ }; // Your existing function

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
              setInput={setInput} // Make sure setInput is passed if InputField uses it directly
              solveExpression={solveExpression}
              insertSymbol={insertSymbol}
              formatForMathJax={formatForMathJax} // Pass if InputField uses it for live preview
            />
            <SolverConfig /> {/* Ensure this doesn't conflict with how data_structure is read */}
          </div>

          <div className="w-full md:w-2/3">
            <SolutionDisplay 
              derivative={derivative} // Already expects LaTeX
            />
            {/* Pass the dynamic steps to StepByStep */}
            <StepByStep steps={derivativeSteps} /> 
          </div>
        </div>

        <div className='flex flex-col md:flex-row gap-8 p-6 w-full lg:w-2/3 justify-center mx-auto'>
          <div className="w-full bg-light py-2 rounded-lg text-dark mx-auto flex items-center justify-center shadow-lg">
            <MeasurementDisplay dataStructure={dataStructure} executionTime={executionTime} peakMemory={peakMemory} />
          </div>
        </div>

        <Bottomcontent />
      </div>
    </MathJaxContext>
  );
};

export default Solver;