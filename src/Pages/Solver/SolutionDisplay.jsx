import React from 'react';
import { MathJax } from "better-react-mathjax";

const SolutionDisplay = ({ derivative, error }) => { 
  return (
    <div className="card p-6 bg-light shadow-lg rounded-lg">
      <h3 className="text-primary mb-4 font-bold text-lg">Solved Derivative:</h3>
        <div className="math-display bg-secondary py-2 rounded-lg text-dark items-center flex justify-center">
        
        {error ? (
            <div class="text-dark text-xl font-bold ">
              <h1> Invalid Expression </h1> 
            </div> 
        ) : (
          <div className="math-display bg-secondary py-2 rounded-lg text-dark">
            {derivative ? (
              <MathJax dynamic>
                <span className="text-xl font-bold">
                  {`\\(${derivative}\\)`}
                </span>
              </MathJax>
            ) : (
              <p className="text-dark text-xl font-bold">Enter an expression to see the derivative.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SolutionDisplay;
