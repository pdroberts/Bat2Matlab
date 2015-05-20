close all
clear variables

calculate_spike_rates = true;

prefs = GeneratePreferences('Mouse', '497', '', '');
% prefs = GeneratePreferences('Mouse', '07202010', '', '');
prefs.spike_time_peak_threshold = 0.11;
experiment_data = LoadExperimentData(prefs);
test_nums = 16:34;

trace_num = 2;
num_tests = length(test_nums);
if calculate_spike_rates
    display('Calculating Spike Rates');
    % FilterSpikeTrain uses a Gaussian Kernel for smoothing
    spike_rates = FilterSpikeTrain(experiment_data, ...
                                     prefs, ....
                                     test_nums, ...
                                     trace_num);
    save ('testCorrMetrixSpikeRates', 'spike_rates');
else
    display('Loading spike Rates off Disk');
    load testCorrMetrixSpikeRates
end

display('Generating Distance Matrix');
correlation_matrix = zeros(num_tests,num_tests);
test_num1_idx = 0;
num_plot_rows = ceil(sqrt(num_tests));
num_plot_cols = num_plot_rows;
for test_num1 = test_nums
    test_num1_idx = test_num1_idx + 1;
    test_num1
    test_num2_idx = 0;
    for test_num2 = test_nums(1):test_nums(test_num1_idx)
        test_num2_idx = test_num2_idx + 1;
        [correlation ...
         std_correlation] = CalculateSpikeCorr(experiment_data, ...
                                               prefs, ...
                                               test_num1, ...
                                               trace_num, ...
                                               test_num2, ...
                                               trace_num, ...
                                               spike_rates);
        correlation_matrix(test_num1_idx, test_num2_idx) = correlation;
        correlation_matrix(test_num2_idx, test_num1_idx) = correlation;
        stdev_correlation_matrix(test_num1_idx, test_num2_idx) = std_correlation;
        stdev_correlation_matrix(test_num2_idx, test_num1_idx) = std_correlation;
    end
end

%Just plot the first trace of each test, to get a better sense for individual correlations
figure;
test_num1_idx = 0;
for test_num1 = test_nums
    test_num1_idx = test_num1_idx + 1;
    subplot(num_plot_rows,num_plot_cols,test_num1_idx);
    plot(spike_rates{test_num1,trace_num}(1,:));
    title(['Test ' int2str(test_num1)]);
end

figure;
test_num1_idx = 0;
for test_num1 = test_nums
    test_num1_idx = test_num1_idx + 1;
    subplot(num_plot_rows,num_plot_cols,test_num1_idx);
    plot(spike_rates{test_num1,trace_num}');
    title(['Test ' int2str(test_num1)]);
end

correlation_matrix(find(correlation_matrix < 0)) = 0;

figure;
imagesc(test_nums,test_nums,correlation_matrix);
title(['Mean Correlation for ' prefs.cell_id4_plot]);
colorbar

figure;
imagesc(test_nums,test_nums,stdev_correlation_matrix);
title(['Stdev of Correlation for ' prefs.cell_id4_plot]);
colorbar

for i = 1:num_tests
    test_num = test_nums(i);
    this_distance = correlation_matrix(i,i);
    this_stdev = stdev_correlation_matrix(i,i);
    matches = [];
    for j = 1:num_tests
        corr_distance = correlation_matrix(i,j);
        corr_stdev = stdev_correlation_matrix(i,j);
        if abs(this_distance - corr_distance) <= 0.3*(this_stdev + corr_stdev)
            matches = [matches test_nums(j)];
        end
    end
    display(['Cluster ' int2str(test_num) ':  ' num2str(matches)]);
end
        

%%%This performs a cluster analysis of the correlation data.
correlation_matrix = 1 - correlation_matrix;
for i = 1:length(correlation_matrix)
    correlation_matrix(i,i) = 0;
end
num_clusters = 5;
vector_correlation = squareform(correlation_matrix);
Z = linkage(vector_correlation);
T = cluster(Z,'maxclust',num_clusters);
% T = [test_nums' T];
for i = 1:num_clusters
    cluster_traces = test_nums(find(T == i));
    display(['Cluster ' int2str(i) ':  ' num2str(cluster_traces)]);
end
        

