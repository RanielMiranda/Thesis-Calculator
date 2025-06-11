// StepByStep.jsx
import React, { useState, useRef } from 'react';
import { MathJax } from "better-react-mathjax";

// **UPDATED** stepExplanation map to match backend rule_keys
const stepExplanation = {
    // Backend rule keys from derivative_ast.py
    "initial_expression": "This is the original function we're differentiating.",
    "constantRule": "The derivative of any constant (a number that doesn't change) is zero.",
    "variableRule": "The derivative of a variable with respect to itself is one (e.g., d/dx(x) = 1).",
    "sumRule_start": "The Sum Rule states that the derivative of a sum of functions is the sum of their derivatives: d/dx(f(x) + g(x)) = f'(x) + g'(x).",
    "sumRule_result": "This is the sum of the derivatives of the individual terms.",
    "productRule_start": "The Product Rule states: d/dx(u*v) = u*(dv/dx) + v*(du/dx). Here, 'u' and 'v' are functions of x.",
    "productRule_dv_dx_expr": "Finding the derivative of the second term in the product.",
    "productRule_du_dx_expr": "Finding the derivative of the first term in the product.",
    "productRule_result": "Applying the product rule formula.",
    "productRule_complex": "For products with many terms, SymPy handles the expansion and differentiation.",
    "productRule_sympy_fallback": "SymPy's direct computation for complex products.",
    "constantMultipleRule_start": "The Constant Multiple Rule states: d/dx(c*f(x)) = c*f'(x), where 'c' is a constant.",
    "constantMultipleRule_result": "Applying the constant multiple rule.",
    "quotientRule_start": "The Quotient Rule states: d/dx(u/v) = (v*(du/dx) - u*(dv/dx)) / v^2. Here, 'u' is the numerator and 'v' is the denominator.",
    "quotientRule_du_dx_expr": "Finding the derivative of the numerator ('u').",
    "quotientRule_dv_dx_expr": "Finding the derivative of the denominator ('v').",
    "quotientRule_result": "Applying the quotient rule formula.",
    "quotientRule_complex_fallback": "For complex quotient expressions, SymPy performs the differentiation directly.",
    "quotientRule_sympy_fallback": "SymPy's direct computation for complex quotients.",
    "powerRule_start": "The Power Rule applies to terms in the form x^n. The general form is d/dx(u^n) = n*u^(n-1)*u'.",
    "powerRule_u_n_result": "Result of applying the power rule and chain rule to u^n.",
    "powerRule_general_start": "This is a general power rule for functions raised to functions, often solved using logarithmic differentiation.",
    "powerRule_general_sympy_fallback": "SymPy's direct computation for f(x)^g(x).",
    "chainRule_for_power_base": "Applying the chain rule for the base of the power function.",
    "sqrtRule_start": "The derivative of √u is (1/(2√u))*u'. This is a special case of the power rule where n = 1/2.", 
    "sqrtRule_result": "Result of applying the square root rule.", 
    "chainRule_for_sqrt_arg": "Applying the chain rule for the argument of the square root function.", 
    "expRule_a_u_start": "This is the derivative rule for a constant base raised to a function: d/dx(a^u) = a^u * ln(a) * u'.",
    "expRule_a_u_result": "Result of applying the exponential rule for a^u.",
    "chainRule_for_exp_a_u_exponent": "Applying the chain rule for the exponent of a^u.",
    "sinRule_start": "The derivative of sin(u) is cos(u)*u'.",
    "sinRule_result": "Result of applying the sine rule.",
    "chainRule_for_sin_arg": "Applying the chain rule for the argument of the sine function.",
    "cosRule_start": "The derivative of cos(u) is -sin(u)*u'.",
    "cosRule_result": "Result of applying the cosine rule.",
    "chainRule_for_cos_arg": "Applying the chain rule for the argument of the cosine function.",
    "expRule_start": "The derivative of e^u is e^u*u'.",
    "expRule_result": "Result of applying the exponential rule.",
    "chainRule_for_exp_arg": "Applying the chain rule for the argument of the exponential function.",
    "logRule_start": "The derivative of ln(u) is (1/u)*u'.",
    "logRule_result": "Result of applying the natural logarithm rule.",
    "chainRule_for_log_arg": "Applying the chain rule for the argument of the natural logarithm function.",
    "generalFunctionRule_start": "A general function derivative is being computed.",
    "generalFunctionRule_result": "SymPy's representation for the derivative of a generic function.",
    "unknownRule": "No specific rule was implemented for this expression. SymPy's general differentiation is used.",
    "unknownRule_sympy_fallback": "SymPy's direct computation for unhandled expressions.",
    "final_derivative": "This is the final simplified derivative of the original expression."
};

const StepByStep = ({ steps }) => { // steps prop comes from Solver.jsx
    const [hoveredRuleKey, setHoveredRuleKey] = useState(null);
    const [popupPosition, setPopupPosition] = useState({ top: 0, left: 0 });

    const handleHover = (explanationKey, event) => {
        if (!explanationKey || !stepExplanation[explanationKey]) {
            setHoveredRuleKey(null); // Clear if no valid explanation
            return;
        }
        setHoveredRuleKey(explanationKey);
        const rect = event.currentTarget.getBoundingClientRect();
        // Position above and centered
        setPopupPosition({
            top: event.clientY,
            left: event.clientX
        });
    };

    const handleMouseLeave = () => {
        setHoveredRuleKey(null);
    };

    if (!steps || steps.length === 0) {
        return (
            <div className="card p-6 bg-light shadow-lg rounded-lg mt-6 mx-auto w-full items-center flex flex-col">
                <h3 className="text-primary mb-4 font-bold text-xl md:text-2xl text-center">
                    Step-by-Step Explanation
                </h3>
                <p className="text-dark">Enter an expression and click "Solve" to see the steps here.</p>
            </div>
        );
    }

    return (
        <div className="card p-6 bg-light shadow-lg rounded-lg mt-6 mx-auto w-full flex flex-col items-center pb-10">
            <h3 className="text-primary mb-6 font-bold text-xl md:text-2xl text-center">
                Step-by-Step Explanation
            </h3>
            <div className="steps-container space-y-3 w-full max-w-2xl justify-center items-center">
                {steps.map((step, stepIndex) => (
                    <div key={step.id || `step-${stepIndex}`} className="step-line flex items-center text-dark text-lg font-medium">
                        {step.prefix && (
                            <MathJax inline dynamic>
                                <span className="mr-2">{`$$ ${step.prefix} $$`}</span> 
                            </MathJax>
                        )}
                        {/* Display explanation text first */}
                        {step.explanation_text && (
                            <span className="mr-2 text-base text-dark">
                                <MathJax inline dynamic>{` ${step.explanation_text} `}</MathJax>
                            </span>
                        )}
                        {step.parts.map((part, partIndex) => (
                            <MathJax inline dynamic key={part.id || `part-${stepIndex}-${partIndex}`}>
                                <span
                                    className={`step-part ${part.explanation_key ? 'cursor-pointer transition-colors duration-200 hover:text-primary' : ''} ${hoveredRuleKey === part.explanation_key ? 'text-primary font-semibold' : ''}`}
                                    onMouseEnter={(e) => part.explanation_key && handleHover(part.explanation_key, e)}
                                    onMouseLeave={handleMouseLeave}
                                >
                                    {`$$ ${part.latex} $$`}
                                </span>
                            </MathJax>
                        ))}
                    </div>
                ))}
            </div>

            {/* Explanation Popup on Hover */}
            {hoveredRuleKey && stepExplanation[hoveredRuleKey] && (
              <div
                  className="fixed p-3 rounded-md bg-secondary text-dark shadow-xl z-20 max-w-xs md:max-w-sm text-sm border border-primarylight"
                  style={{
                    top: `${popupPosition.top}px`,
                    left: `${popupPosition.left}px`,
                    transform: 'translate(-50%, -100%)',
                    pointerEvents: 'none'
                  }}
              >
                  <MathJax dynamic>
                    {/* Wrap in $$ for display math in the popup, as it's a block explanation */}
                    {` ${stepExplanation[hoveredRuleKey]} `}
                  </MathJax>
              </div>
            )}
        </div>
    );
};

export default StepByStep;