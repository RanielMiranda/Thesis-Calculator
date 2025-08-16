import React from 'react';

const SolverConfig = ({ displayedDataStructure, setDisplayedDataStructure, numTerms, setNumTerms, maxDepth, setMaxDepth, variable, setVariable, isLoading, hasResults }) => {
    return (
        <div className="card p-6 bg-light shadow-lg rounded-lg mt-6 text-dark">
            <h3 className="text-primary mb-4 font-bold text-lg">Configuration</h3>
            
            <div className="form-group mb-4">
                <label className="font-semibold">Display Steps For:</label>
                <select
                    name="option"
                    value={displayedDataStructure}
                    onChange={(e) => setDisplayedDataStructure(e.target.value)}
                    className="mt-2 w-full px-2 py-1 rounded bg-secondary border"
                    disabled={!hasResults}
                >
                    <option value="AST">AST</option>
                    <option value="DAG">DAG</option>
                    <option value="NLL">NLL</option>
                </select>
                {!hasResults && <p className="text-xs text-dark mt-1">Solve an expression to enable.</p>}
            </div>

            <div className="form-group mb-4">
                <label className="font-semibold">Differentiate w.r.t:</label>
                <div className="flex gap-4 mt-2">
                    {['x', 'y', 'z'].map((varName) => (
                        <label key={varName} className="flex items-center gap-1">
                            <input type="radio" name="diff-variable" value={varName} checked={variable === varName} onChange={(e) => setVariable(e.target.value)} disabled={isLoading} />
                            {varName}
                        </label>
                    ))}
                </div>
            </div>

            <div className="form-group">
                <h4 className="font-semibold text-md mb-2">Expression Generation:</h4>
                <label className="block mb-2">
                    Number of terms:
                    <input type="number" value={numTerms} onChange={(e) => setNumTerms(Number(e.target.value))} className="w-full mt-1 px-2 py-1 rounded bg-secondary border" min="1" max="5" disabled={isLoading} />
                </label>
                <label className="block">
                    Max Depth:
                    <input type="number" value={maxDepth} onChange={(e) => setMaxDepth(Number(e.target.value))} className="w-full mt-1 px-2 py-1 rounded bg-secondary border" min="1" max="4" disabled={isLoading} />
                </label>
            </div>
        </div>
    );
};

export default SolverConfig;
