function [figureHandle tableHandle] = ExploreTestData(experimentData)

columnHeaders = {'Number of Traces','Test Type','Test Class','Comment'};
columnWidths = {75, 100, 125, 200};

numTests = size(experimentData.test,2);
tableData = cell(numTests,4);
for rowNum = 1:numTests
    tableData{rowNum,1} = num2str(size(experimentData.test(rowNum).trace,2));
    tableData{rowNum,2} = experimentData.test(rowNum).testtype;
    tableData{rowNum,3} = experimentData.test(rowNum).full_testtype;
    tableData{rowNum,4} = experimentData.test(rowNum).comment;
end

figureHandle = figure('Name',[' Data Summary for File ' experimentData.pst_filename],'NumberTitle','off');

if getversion < 7.6 %R2008a
    figurePos = getpixelposition(figureHandle,0);
    figurePos(1:2) = 0;
    tableHandle = uitable(tableData, columnHeaders, 'Position', figurePos);
else
    tableHandle = uitable(figureHandle, 'Data', tableData, 'ColumnName', columnHeaders, 'ColumnWidth', columnWidths, 'units', 'normalized', 'position', [0 0 1 1]);
end