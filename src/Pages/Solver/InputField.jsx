import React from 'react';
import { MathJax } from "better-react-mathjax";

const InputField = ({ input, handleInputChange, setInput, solveExpression, insertSymbol, formatForMathJax, generateExpression, clearInput }) => {
  return (
    <div className="card p-6 bg-light shadow-md rounded-lg">
      <h3 className="text-primary mb-4 font-bold text-lg">Equation Input</h3>
      <div className="relative">
        <input
          type="text"
          id="equation-input"
          className="input-field w-full px-4 py-2 rounded-md focus:outline-none focus:border-primary pr-24 bg-secondary text-dark"
          placeholder="e.g., sin(x^2) + e^(3y)"
          value={input}
          onChange={handleInputChange}
        />
        <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex gap-2">
          <button
            onClick={clearInput}
            className="btn text-red-500 hover:text-red-700"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5-4h4m-4 0a2 2 0 00-2 2h8a2 2 0 00-2-2m-4 0V3m-3 4h10"
              />
            </svg>
          </button>
          <button
            onClick={solveExpression}
            className="btn bg-primary hover:bg-primarylight px-3 py-1 rounded-md text-dark"
          >
            Solve
          </button>
        </div>
      </div>

      {/* Math Symbol Buttons */}
      <div className="flex flex-wrap gap-2 mt-4">
        {[
          { symbol: 'π', className: 'bg-primary hover:bg-primarylight text-dark'},
          { symbol: '√(', className: 'bg-primary hover:bg-primarylight text-dark'},
          { symbol: 'e', className: 'bg-primary hover:bg-primarylight text-dark'},
          { symbol: '/', className: 'bg-primary hover:bg-primarylight text-dark', special: true },
          { symbol: '^2', className: 'bg-primary hover:bg-primarylight text-dark', special: true }
        ].map((btn, index) => (
          <button
            key={index}
            onClick={() => insertSymbol(btn.symbol)}
            className={`btn ${btn.className} px-3 py-1 rounded-md h-10 ${btn.special ? 'flex items-center' : ''}`}
          >
            <MathJax inline>
              {btn.special
                ? btn.symbol === '/'
                  ? <MathJax inline style={{fontSize: '0.7em'}}>{'$$ \\frac{[\\,]}{[\\,]} $$'}</MathJax>
                  : '$$ x^{2} $$'
                : btn.symbol}
            </MathJax>
          </button>
        ))}
      </div>

      <div className="flex flex-col pt-4">
        <button className="btn bg-primary hover:bg-primarylight py-2 rounded-md text-dark"
            onClick={generateExpression}>
            Generate
          </button>
      </div>

      <div className="flex flex-col pt-4">
        <h className="text-primary font-bold text-lg">This is Displayed as:</h>
        <div className="flex bg-secondary w-full mx-auto rounded-md p-2 items-center justify-center">
          <MathJax className = "text-dark">
            {`$$\\frac{d}{dx} = ${formatForMathJax(input)}$$`}
          </MathJax>
        </div>
      </div>
    </div>
  );
};

export default InputField;