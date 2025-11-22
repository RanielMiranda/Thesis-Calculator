import React from 'react';
import { Ring } from 'ldrs/react'
import 'ldrs/react/Ring.css'


const MeasurementDisplay = ({ results, isLoading, progress }) => {
    const dataStructures = ['AST', 'DAG', 'NLL'];

    if (isLoading) {
        return (
            <div className="mt-6 p-6 bg-light rounded-lg shadow-lg text-center">
                <h3 className="text-primary mb-4 font-bold text-lg">Performance Benchmark</h3>
                <p className="text-dark mb-4">Running benchmarks, please wait...</p>
                <Ring
                    size="40"
                    stroke="5"
                    bgOpacity="0"
                    speed="2"
                    color="#3f7cf5"
                />

            </div>
        )
    }

    if (!results.AST.avgTime) {
        return (
            <div className="mt-6 p-6 bg-light rounded-lg shadow-lg text-center">
               <h3 className="text-primary mb-4 font-bold text-lg">Performance Benchmark</h3>
               <p className="text-dark">Click "Solve" to see benchmark results.</p>
            </div>
       );
    }

    // --- Analysis Section ---
    const analysis = {};
    let bestOverall = { name: '', score: Infinity };

    // Filter to include only data structures with valid numbers for both time and memory.
    const validDataStructures = dataStructures.filter(ds => 
        typeof results[ds].avgTime === 'number' && !isNaN(results[ds].avgTime) &&
        typeof results[ds].avgMemory === 'number' && !isNaN(results[ds].avgMemory)
    );

    if (validDataStructures.length > 0) {
        const times = validDataStructures.map(ds => results[ds].avgTime);
        const memories = validDataStructures.map(ds => results[ds].avgMemory);

        const minTime = Math.min(...times);
        const minMemory = Math.min(...memories);

        analysis.fastest = validDataStructures[times.indexOf(minTime)];
        analysis.mostEfficient = validDataStructures[memories.indexOf(minMemory)];
        
        validDataStructures.forEach(ds => {
            const timeScore = results[ds].avgTime / minTime;
            const memoryScore = results[ds].avgMemory / minMemory;
            const combinedScore = timeScore + memoryScore;
            if (combinedScore < bestOverall.score) {
                bestOverall = { name: ds, score: combinedScore };
            }
        });
        analysis.bestOverall = bestOverall.name;
    }


    return (
        <div className="mt-6 bg-light py-4 px-6 rounded-lg shadow-lg text-dark">
            <h3 className="text-primary mb-4 font-bold text-lg text-center">Performance Benchmark Results</h3>
            <table className="table-auto w-full text-center border-collapse">
                <thead>
                    <tr className="bg-secondary text-dark">
                        <th className="p-2 border-2 border-secondary">Data Structure</th>
                        <th className="p-2 border-2 border-secondary">Avg. Time (ms)</th>
                        <th className="p-2 border-2 border-secondary">Avg. Memory (bytes)</th>
                    </tr>
                </thead>
                <tbody>
                    {dataStructures.map(ds => (
                        <tr key={ds} className="hover:bg-secondary transition-colors duration-200">
                            <td className="p-2 border-2 border-secondary font-semibold">{ds}</td>
                                <td className="p-3 border-x border-b border-secondary">
                                    {results[ds].avgTime !== null ? (
                                        <span className={`${ds === analysis.fastest ? 'text-primary font-bold' : 'text-dark'}`}>
                                            {results[ds].avgTime.toFixed(2)}
                                        </span>
                                    ) : 'N/A'}
                                </td>
                                <td className="p-3 border-x border-b border-secondary">
                                    {results[ds].avgMemory !== null ? (
                                        <span className={`${ds === analysis.mostEfficient ? 'text-primary font-bold' : 'text-dark'}`}>
                                            {results[ds].avgMemory.toLocaleString()}
                                        </span>
                                    ) : 'N/A'}
                                </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            {analysis.bestOverall && (
                <div className="mt-4 p-4 bg-light rounded-lg border border-light">
                    <h4 className="font-bold text-md text-xl mb-2 text-primary">Analysis Summary:</h4>
                    <ul className="list-disc list-inside text-sm space-y-1">
                        <li><strong>Fastest:</strong> <span className="font-semibold text-xl text-primary">{analysis.fastest}</span> was the quickest to compute the derivative.</li>
                        <li><strong>Most Memory Efficient:</strong> <span className="font-semibold text-xl text-primary">{analysis.mostEfficient}</span> used the least amount of memory.</li>
                        <li><strong>Best Overall Performer:</strong> <span className="font-semibold text-xl text-primary">{analysis.bestOverall}</span> provided the best balance of speed and memory efficiency for this expression.</li>
                    </ul>
                </div>
            )}
        </div>
    );
};

export default MeasurementDisplay;
