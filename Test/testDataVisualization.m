close all
clear variables

%Create a preferences structure for the desired experimental data
prefs = GeneratePreferences('Mouse', '497', '', '');
% prefs = GeneratePreferences('Mouse', '07202010', '', '');
%Set the threshold used for spike detection. 0.11 is the default.
prefs.spike_time_peak_threshold = 0.11;
%Extract XML metadata and conver to to Matlab structure
experiment_data = LoadExperimentData(prefs);
 
%-------------------
% Test Visualization
%-------------------
%Specify the test number to visualize, this is a one tone test
test_num = 9;
% test_num = 201;
%Generate contour plot of single frequency tuning curve
VisualizeTestData(experiment_data,prefs,test_num);
%Generate image map plots of time-frequency histograms
VisualizeTestData(experiment_data,prefs,test_num,[0 1 0 0 1]);

% --------------------
% Trace Visualization
% --------------------
% Specify the test and trace number to visualize
test_num = 9;
trace_num = 6; 
% trace_num = 1; 
%Visualize the traces
VisualizeTraceData(experiment_data,prefs,test_num,trace_num);
VisualizeTraceData(experiment_data,prefs,test_num,trace_num,[0 1 1 0 0 0 0 0 0 0]);
VisualizeTraceData(experiment_data,prefs,test_num,trace_num,[0 0 0 1 1 1 1 0 0 0]);
VisualizeTraceData(experiment_data,prefs,test_num,trace_num,[0 0 0 0 0 0 0 1 1 0]);
