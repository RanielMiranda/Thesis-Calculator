import React from 'react';

const MeasurementDisplay = ({ dataStructure, executionTime, peakMemory }) => {
  return (
    <div className="mt-6 bg-light py-2 rounded-lg text-dark mx-auto flex items-center justify-center shadow-lg">
      <table className="card table-auto w-full text-center">
        <thead>
          <tr>
            <th>Data Structure</th>
            <th>Execution Time (ms)</th>
            <th>Peak Memory (bytes)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{dataStructure}</td>
            <td>{executionTime !== null ? executionTime.toFixed(2) : 'N/A'}</td>
            <td>{peakMemory !== null ? peakMemory.toLocaleString() : 'N/A'}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};

export default MeasurementDisplay;

