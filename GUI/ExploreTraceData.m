function [figureHandle tableHandle] = ExploreTraceData(experimentData, testNum)

% %Create a preferences structure for the desired experimental data
% prefs = GeneratePreferences('mouse', '543', '', '');
% experimentData = LoadExperimentData(prefs);

numTraces = size(experimentData.test(testNum).trace,2);
testtype = experimentData.test(testNum).testtype;

columnHeaders{1,1} = 'Record Duration';
columnHeaders{1,2} = 'Number of Sweeps';
columnHeaders{1,3} = 'Attenuation';
columnHeaders{1,4} = 'Stimulus Duration';
columnHeaders{1,5} = 'Delay';
if strcmp(testtype,'tone')
    columnHeaders{1,6} = 'Frequency';
elseif strcmp(testtype,'twotone')
    columnHeaders{1,6} = 'Frequency 1';
    columnHeaders{1,7} = 'Frequency 2';
elseif strcmp(testtype,'vocalization')
    columnHeaders{1,6} = 'File Name';
end

tableData = cell(numTraces,size(columnHeaders,2));

for rowNum = 1:numTraces
    tableData{rowNum,1} = num2str(experimentData.test(testNum).trace(rowNum).record_duration);
    tableData{rowNum,2} = num2str(experimentData.test(testNum).trace(rowNum).num_samples);
    if ~experimentData.test(testNum).trace(rowNum).is_control
        tableData{rowNum,3} = num2str(experimentData.test(testNum).trace(rowNum).stimulus.attenuation);
        tableData{rowNum,4} = num2str(experimentData.test(testNum).trace(rowNum).stimulus.duration);
        tableData{rowNum,5} = num2str(experimentData.test(testNum).trace(rowNum).stimulus.delay);
        if strcmp(testtype,'tone')
            tableData{rowNum,6} = num2str(experimentData.test(testNum).trace(rowNum).stimulus.frequency);
        elseif strcmp(testtype,'twotone')
            tableData{rowNum,6} = num2str(experimentData.test(testNum).trace(rowNum).stimulus.frequency);
            tableData{rowNum,7} = num2str(experimentData.test(testNum).trace(rowNum).stimulus(2).frequency);
        elseif strcmp(testtype,'vocalization')
            tableData{rowNum,6} = experimentData.test(testNum).trace(rowNum).stimulus.vocal_call_file;
        end
    else
        tableData{rowNum,3} = 'N/A';
        tableData{rowNum,4} ='N/A';
        tableData{rowNum,5} ='N/A';
        if strcmp(testtype,'tone')
            tableData{rowNum,6} = 'N/A';
        elseif strcmp(testtype,'twotone')
            tableData{rowNum,6} = 'N/A';
            tableData{rowNum,7} = 'N/A';
        elseif strcmp(testtype,'vocalization')
            tableData{rowNum,6} = 'N/A';
        end
    end
end

figureHandle = figure('Name',[' Data Summary for Test ' int2str(testNum)],'NumberTitle','off');

figurePos = getpixelposition(figureHandle,1);
figurePos(1:2) = 0;

tableHandle = uitable(figureHandle, 'Data',tableData, 'ColumnNames',columnHeaders, 'Position', figurePos);