% List of derivative structures
structures = {'derivative_ast', 'derivative_dag', 'derivative_nll'};

% Test equations
expressions = {
    'sin(x)+sin(x)'
    'cos(x)+3*x^2'
    'tan(x)+4*x'
    'sin(x)+cos(x)'
    'sin(x^2)+tan(x^2)'
    '(tan(x))*(x^2+1)'
    'sin(x)*cos(x^2)+x^3'
    'tan(x^2+sin(x))+tan(x^2+sin(x))'
    '(csc(x^3)+x)*(tan(x^2)+sin(x))'
    '(csc(x^2)+x^2)/(tan(x^2+sin(x)+1))'
};

results = []; 

% --- BENCHMARK EXECUTION LOOP ---
for s = 1:length(structures)
    structure = structures{s};
    fprintf('\n=== Structure: %s ===\n', structure);

    for e = 1:length(expressions)
        expr = expressions{e};
        fprintf('Computing derivative for: %s\n', expr);

        % Run benchmark through Python
        try
            res = py.matlab_benchmark.run_benchmark(structure, expr, 'x');

            % Extract values from Python dictionary (Time and Memory only)
            time_ms = double(res.get('time_ms'));
            mem_bytes = double(res.get('memory_bytes'));
            
            % Display in console
            fprintf('    Time: %.3f ms | Memory: %.2f KB\n', time_ms, mem_bytes/1024);

            % Store in MATLAB table (4 columns: Structure, Expression, Time, Memory)
            results = [results; {structure, expr, time_ms, mem_bytes}];
        catch ME
            fprintf(2, 'Error calling Python for %s with structure %s: %s\n', expr, structure, ME.message);
            % Store placeholder data if Python call fails 
            results = [results; {structure, expr, NaN, NaN}];
        end
    end
end

% --- RAW DATA PROCESSING ---
T = cell2table(results, 'VariableNames', {'Structure', 'Expression', 'Time_ms', 'Memory_bytes'});

fprintf('\n\n--- Benchmark Raw Data Table (Long Format) ---\n');
disp(T);

