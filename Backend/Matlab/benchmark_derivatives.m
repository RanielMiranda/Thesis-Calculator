% === MATLAB Benchmark Script ===
% Make sure your working directory is where the Python files are
% Example: cd('C:\path\to\your\project')

% Optional: if Python not found, specify manually
% pyenv('Version', 'C:\Path\to\python.exe');

% List of derivative structures (Python files, no .py)
structures = {'derivative_ast', 'derivative_dag', 'derivative_nll'};

% Test equations
expressions = {
    'sin(x)+sin(x)'
    'cos(x)+3*x**2'
    'tan(x)+4*x'
    'sin(x)+cos(x)'
    'sin(x**2)+tan(x**2)'
    '(tan(x))*(x**2+1)'
    'sin(x)*cos(x**2)+x**3'
    'tan(x**2+sin(x))+tan(x**2+sin(x))'
    '(csc(x**3)+x)*(tan(x**2)+sin(x))'
    '(csc(x**2)+x**2)/(tan(x**2+sin(x)+1))'
};

results = [];

for s = 1:length(structures)
    structure = structures{s};
    fprintf('\n=== Structure: %s ===\n', structure);

    for e = 1:length(expressions)
        expr = expressions{e};
        fprintf('Computing derivative for: %s\n', expr);

        % Run benchmark through Python
        res = py.matlab_benchmark.run_benchmark(structure, expr, 'x');

        % Extract values from Python dictionary
        time_ms = double(res{'time_ms'});
        mem_bytes = double(res{'memory_bytes'});
        latex_str = string(res{'latex'});

        % Display in console
        fprintf('   Time: %.3f ms | Memory: %.2f KB\n', time_ms, mem_bytes/1024);

        % Store in MATLAB table
        results = [results; {structure, expr, time_ms, mem_bytes, latex_str}];
    end
end

% Convert to table
T = cell2table(results, 'VariableNames', {'Structure', 'Expression', 'Time_ms', 'Memory_bytes', 'Latex'});

% Show and plot summary
disp(T);

% Example visualization
figure;
gscatter(1:height(T), T.Time_ms, T.Structure);
xlabel('Equation #');
ylabel('Execution Time (ms)');
title('Derivative Structure Time Comparison');
grid on;
