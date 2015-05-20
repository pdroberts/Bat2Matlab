%Create a preferences structure for the desired experimental data
prefs = GeneratePreferences('Mouse', '497', '', '');
experimentData = LoadExperimentData(prefs);

[figureHandle tableHandle] = ExploreTestData(experimentData);
[trace_figureHandle trace_tableHandle] = ExploreTraceData(experimentData,3);
