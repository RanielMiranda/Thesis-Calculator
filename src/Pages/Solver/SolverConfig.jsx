import React, { useState } from 'react';

const SolverConfig = ({ dataStructure, setDataStructure, numTerms, setNumTerms, maxDepth, setMaxDepth, variable, setVariable }) => {
    return (
        <div className="card p-6 bg-light shadow-lg rounded-lg mt-6 text-dark">
            <h3 className="text-primary mb-4 font-bold text-lg">Solver Configuration</h3>

            {/* Data Structure Used */}
            <div className="form-group mb-4">
                <div>
                    <label className="font-semibold">Select Data Structure Type: </label>
                </div>
                <select
                    name="option"
                    value={dataStructure}
                    onChange={(e) => setDataStructure(e.target.value)}
                    className="mt-2 px-2 py-1 rounded bg-secondary"
                >
                    <option value="AST">AST</option>
                    <option value="DAG">DAG</option>
                    <option value="NLL">NLL</option>
                </select>
            </div>

            {/* Variables and Options */}
            <div className="form-group mb-4">
                <label className="font-semibold">Differentiate w.r.t: </label>
                <div className="radio-group flex flex-col">
                    {['x', 'y', 'z'].map((varName) => (
                        <label key={varName}>
                            <input
                                type="radio"
                                name="diff-variable"
                                value={varName}
                                checked={variable === varName}
                                onChange={(e) => setVariable(e.target.value)}
                            />
                            {varName}
                        </label>
                    ))}
                </div>
            </div>

            {/* Configuration for Expression Generation */}
            <div className="form-group mb-4">
                <h4 className="font-semibold text-md mb-2">Generate Expression Settings:</h4>
                <label className="block mb-2">
                    Number of terms:
                    <input
                        type="number"
                        value={numTerms}
                        onChange={(e) => setNumTerms(Number(e.target.value))}
                        className="w-full mt-1 px-2 py-1 rounded bg-secondary"
                        min="1"
                        max="5"
                    />
                </label>
                <label className="block">
                    Max Depth:
                    <input
                        type="number"
                        value={maxDepth}
                        onChange={(e) => setMaxDepth(Number(e.target.value))}
                        className="w-full mt-1 px-2 py-1 rounded bg-secondary"
                        min="1"
                        max="4"
                    />
                </label>
            </div>
        </div>
    );
};

export default SolverConfig;
