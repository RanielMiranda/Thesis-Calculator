// SolutionDisplay.jsx
import React from 'react';
import { MathJax } from "better-react-mathjax";

const SolutionDisplay = ({ derivative }) => { // Removed formatForMathJax from props
  return (
    <div className="card p-6 bg-light shadow-lg rounded-lg">
      <h3 className="text-primary mb-4 font-bold text-lg">Solved Derivative:</h3>
      <div className="math-display bg-secondary py-2 rounded-lg text-dark">
        {/* Directly use 'derivative' as it's already LaTeX from the backend */}
        {/* Also, ensure proper MathJax delimiters (double them for display math if needed, or rely on component's default) */}
        <MathJax className="text-dark">{`$$ ${derivative} $$`}</MathJax>
      </div>
    </div>
  );
};

export default SolutionDisplay;