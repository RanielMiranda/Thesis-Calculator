import React from 'react';
import { MathJax } from "better-react-mathjax";

const SolutionDisplay = ({ derivative }) => { 
  return (
    <div className="card p-6 bg-light shadow-lg rounded-lg">
      <h3 className="text-primary mb-4 font-bold text-lg">Solved Derivative:</h3>
      <div className="math-display bg-secondary py-2 rounded-lg text-dark">
        <MathJax className="text-dark">{`$$ ${derivative} $$`}</MathJax>
      </div>
    </div>
  );
};

export default SolutionDisplay;