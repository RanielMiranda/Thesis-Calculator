import React, { useState, useMemo } from 'react';
import { MathJax } from "better-react-mathjax";

// Maps backend rule keys to human-readable explanations.
const stepExplanation = {
    "initial_expression": "This is the original function we're differentiating.",
    "constantRule": "The derivative of any constant (a number that doesn't change) is zero.",
    "variableRule": "The derivative of a variable with respect to itself is one (e.g., d/dx(x) = 1).",
    "sumRule": "The Sum Rule: Differentiate each term separately and add the results. d/dx(f(x) + g(x)) = f'(x) + g'(x).",
    "productRule": "The Product Rule: d/dx(u*v) = u*(dv/dx) + v*(du/dx).",
    "constantMultipleRule": "The Constant Multiple Rule: A constant factor can be pulled out. d/dx(c*f(x)) = c*f'(x).",
    "quotientRule": "The Quotient Rule: d/dx(u/v) = (v*(du/dx) - u*(dv/dx)) / v^2.",
    "powerRule": "The Power Rule: For u^n, the derivative is n*u^(n-1)*u'.",
    "expRule_a_u": "Exponential Rule: For a^u, the derivative is a^u * ln(a) * u'.",
    "sinRule": "The derivative of sin(u) is cos(u)*u'.",
    "cosRule": "The derivative of cos(u) is -sin(u)*u'.",
    "tanRule": "The derivative of tan(u) is sec²(u)*u'.",
    "secRule": "The derivative of sec(u) is sec(u)tan(u)*u'.",
    "cscRule": "The derivative of csc(u) is -csc(u)cot(u)*u'.",
    "cotRule": "The derivative of cot(u) is -csc²(u)*u'.",
    "expRule": "The derivative of e^u is e^u*u'.",
    "logRule": "The derivative of ln(u) is (1/u)*u'.",
    "unknownRule": "No specific rule was matched. Using SymPy's general differentiation engine as a fallback.",
    "final_derivative": "This is the final simplified derivative of the original expression.",
    "cached_subexpr": "This sub-expression was already differentiated earlier, so we are reusing the cached result for efficiency."
};

const getBaseRule = (key) => {
    if (!key) return null;
    const base = key.split('_')[0];
    if (base === 'constant' && key.includes('Multiple')) return 'constantMultipleRule';
    if (base === 'exp' && key.includes('_a_u')) return 'expRule_a_u';
    return base;
};

const safeLatex = (step) => {
    const parts = step?.parts;
    if (!parts || !Array.isArray(parts) || !parts[0] || !parts[0].latex) {
        return "";
    }
    return parts[0].latex;
};

const StepByStep = ({ steps }) => {
    const [activeRule, setActiveRule] = useState(null);
    const [hoveredExplanation, setHoveredExplanation] = useState(null);
    const [popupPosition, setPopupPosition] = useState({ top: 0, left: 0 });

    const processedSteps = useMemo(() => {
        if (!steps || steps.length === 0) return [];

        let indentLevel = 0;
        const stepData = [];

        for (const step of steps) {
            const ruleKey = step?.parts?.[0]?.explanation_key || (step.id ? step.id.split("_").slice(2).join("_") : "");
            
            // Decrease indent level when a rule's result is shown
            if (ruleKey.includes('_result') || ruleKey.includes('_fallback')) {
                indentLevel = Math.max(0, indentLevel - 1);
            }

            stepData.push({
                ...step,
                indent: indentLevel,
                baseRule: getBaseRule(ruleKey),
                ruleKey: ruleKey,
            });

            // Increase indent level when starting a new rule application
            if (ruleKey.includes('_start')) {
                indentLevel++;
            }
        }
        return stepData;
    }, [steps]);
    
    // Handlers for the explanation popup
    const handleHover = (baseRule, event) => {
        const explanation = stepExplanation[baseRule];
        if (!explanation) return;
        setHoveredExplanation(explanation);
        setPopupPosition({ top: event.clientY, left: event.clientX });
    };
    const handleMouseLeave = () => setHoveredExplanation(null);

    // Render placeholder if no steps are available
    if (!steps || steps.length === 0) {
        return (
            <div className="card p-6 bg-light shadow-lg rounded-lg mt-6 mx-auto w-full items-center flex flex-col">
                <h3 className="text-primary mb-4 font-bold text-xl md:text-2xl text-center">Step-by-Step Explanation</h3>
                <p className="text-dark">Enter an expression and click "Solve" to see the steps here.</p>
            </div>
        );
    }

    return (
        <div className="card p-6 bg-light shadow-lg rounded-lg mt-6 mx-auto w-full flex flex-col items-center pb-10">
            <h3 className="text-primary mb-6 font-bold text-xl md:text-2xl text-center">Step-by-Step Explanation</h3>
            <div className="steps-container w-full max-w-3xl" onMouseLeave={() => setActiveRule(null)}>
                {Array.isArray(processedSteps) && processedSteps.map((step, stepIndex) => (
                    <div
                        key={step.id || `step-${stepIndex}`}
                        className={`step-item relative transition-colors duration-200 rounded-md py-1 ${activeRule && step.baseRule === activeRule ? 'bg-primary/10' : ''}`}
                        style={{ paddingLeft: `${step.indent * 2.5}rem` }}
                        onMouseEnter={() => step.baseRule && setActiveRule(step.baseRule)}
                    >
                        {/* Vertical connector line for tree structure */}
                        {step.indent > 0 && (
                            <div className="absolute top-0 bottom-0 w-px bg-gray-300" style={{ left: `${step.indent * 2.5 - 1.5}rem` }}></div>
                        )}
                        {/* Horizontal connector line for tree structure */}
                        {step.indent > 0 && (
                            <div className="absolute top-1/2 -mt-px w-4 h-px bg-gray-300" style={{ left: `${step.indent * 2.5 - 1.5}rem` }}></div>
                        )}

                        <div className="step-line flex items-center text-dark text-lg">
                            <span className="w-2/5 text-sm text-gray-500 pr-4 truncate">{step.explanation_text ?? ""}</span>
                            <div
                                className="w-3/5"
                                onMouseMove={(e) => handleHover(step.baseRule, e)}
                                onMouseLeave={handleMouseLeave}
                            >
                                <MathJax inline dynamic>
                                    <span className={`cursor-default p-1 rounded ${step.baseRule ? 'hover:bg-primary/20' : ''}`}>
                                        {`\\(${safeLatex(step)}\\)`}
                                    </span>
                                </MathJax>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Explanation Popup on Hover */}
            {hoveredExplanation && (
                <div
                    className="fixed p-3 rounded-md bg-secondary text-dark shadow-xl z-20 max-w-xs text-sm border border-primarylight"
                    style={{
                        top: `${popupPosition.top}px`,
                        left: `${popupPosition.left}px`,
                        transform: 'translate(-50%, -100%)', // Position above and centered on cursor
                        pointerEvents: 'none'
                    }}
                >
                    <p>{hoveredExplanation}</p>
                </div>
            )}
        </div>
    );
};

export default StepByStep;