import tkinter
from configparser import ConfigParser
from os import makedirs, path
from tkinter import filedialog

import pandas as pd

from DataProcessFncs import MeanVar_NPercentile, LabelTestDataDf, CreateFltDict, GetStepFltDuration, get_NPercentile
from InputProcessFncs import GetSignalsLogged, GetDatafromMdf_asDF, FetchMdfHeader, getTestLogFileNames
from OutputFns import writetoExeclSheet

pd.set_option('use_inf_as_na', True)
from scipy.stats import ttest_ind


def main():
    """
    Reading parameters from conf.py
    """
    parser = ConfigParser()
    parser.read("conf.py")

    # Getting signal groups / adding to dict
    SignalGroups = dict()
    for k, v in parser.items('SignalGroups'):
        signalGrp = k.strip()
        SignalGroups[k] = []
        for var in v.split(','):
            SignalGroups[k].append(var.strip())

    # Getting other settings
    Settings = dict()
    for k, v in parser.items('Settings'):
        Settings[k] = v.strip()

    start_prctle = float(Settings['sample_start_prctle'])
    end_prctle = float(Settings['sample_end_prctle'])
    highlight_thres = float(Settings['pvalue_highlight_thres'])
    DataDump = bool(Settings['datadump'])

    # Defining test step that will be used for filtering/grouping for mean calculation
    TestStepLabels = ['FLC_SteadyState_900Rpm', 'FLC_SteadyState_1000Rpm', 'FLC_SteadyState_1100Rpm',
                      'FLC_SteadyState_1200Rpm',
                      'FLC_SteadyState_1300Rpm', 'FLC_SteadyState_1400Rpm', 'FLC_SteadyState_1500Rpm',
                      'FLC_SteadyState_1600Rpm',
                      'FLC_SteadyState_1700Rpm', 'FLC_SteadyState_1800Rpm', 'FLC_SteadyState_1900Rpm',
                      'FLC_SteadyState_2000Rpm',
                      'StepResponse_SteadyState1200', 'StepResponse_SteadyState1900']

    # Initialising data frames and dictionaries
    Sw_info_table = pd.DataFrame([])
    Signaltracker = pd.DataFrame([], columns=['Signals'])
    MeanDfs = dict()
    VarDfs = dict()
    LogDataset = dict()

    # These are the signals specified in conf file to be analysed
    SigListConf = []
    for item in SignalGroups.keys():
        SigListConf += SignalGroups[item]

    # Adding addtional signals to help label test steps

    SigList = SigListConf + ['Engine_speed', 'Pedal.Value', 'Actual_fuel_value']
    SigList = list(set(SigList))
    SigListConf = list(set(SigListConf))

    """
    GUI Stuff - Get file/folder/baseline info from user  and set up folder structure and create filenames   
    """
    tkinter.Tk().withdraw()
    print("\nSelect folder location of MDF/DAT files ")
    testlogDir = filedialog.askdirectory(title="Select Test log Directory ")
    txt = testlogDir.replace('/', '\\')
    print("Selected - %s\n" % txt)
    datfiles = getTestLogFileNames(testlogDir)
    print("Select a dat file to set as baseline file ")

    """
    We have the location, creating filenames and path for writing output xcel/csv files
    """

    baselineFile = filedialog.askopenfilename(initialdir=testlogDir, title="Select a Log file to use as baseline",
                                              filetypes=(("dat files", "*.dat"), ("all files", "*.*")))
    baselineFile = path.basename(baselineFile)
    txt = baselineFile.replace('/', '\\')
    print("Selected - %s\n" % txt)

    ReportPath = path.join(testlogDir, 'report')
    if (DataDump == True):
        DataDumpPath = path.join(ReportPath, 'data')
        try:
            makedirs(DataDumpPath)
        except:
            pass
    try:
        makedirs(ReportPath)
    except:
        pass
    SummaryExcelFilename = path.join(ReportPath, 'EpotData_Summary.xlsx')
    """
    Read data from MDF / Label it and populate Fault dictionary
    """

    # Create a txt file with fault code if it does not exist in reports folder
    fltdictPath = path.join(ReportPath, 'Fault_dict.txt')
    fltdict = CreateFltDict(fltdictPath)

    # Cycle through each dat files and read required signals

    for idx, filename in enumerate(datfiles):
        print("Getting Data and Labelling - %s...." % path.basename(filename), end='')
        Signaltracker = GetSignalsLogged(Signaltracker, filename)
        # extract header info
        header = FetchMdfHeader(filename)
        SW_id = header['A2L']
        curfile = path.basename(filename)
        if curfile == baselineFile:
            SW_id = SW_id + '\n(Baseline)'
            baseline = SW_id
        # Add header  info to a  dataframe containing meta ifnormation of test logs
        row = pd.DataFrame(header, index=[idx])
        Sw_info_table = Sw_info_table.append(row)

        # Reading signals from mdf file as temp_df
        temp_df = GetDatafromMdf_asDF(filename, SigList, SampleTime=0.05)  # getting
        # Add columns whch contains test labels
        temp_df = LabelTestDataDf(temp_df)
        # test label added above is strings, convert those to numeric in nuneric to allow cecking in csv file
        temp_df["TestStepLabel_code"] = temp_df["TestStepLabel"].astype('category')
        temp_df["TestStepLabel_code"] = temp_df["TestStepLabel_code"].cat.codes
        temp_df["TestRegime_code"] = temp_df["TestRegime"].astype('category')
        temp_df["TestRegime_code"] = temp_df["TestRegime_code"].cat.codes
        # Copy the df into a dictionary, where each key is a df of signals from each release
        LogDataset[SW_id] = temp_df.copy(deep=True)
        # if data dump is required, copy labelled df to data folder
        if (DataDump == True):
            csv_filename = header['A2L'] + '.csv'
            csv_filename = path.join(DataDumpPath, csv_filename)
            temp_df.to_csv(csv_filename, index=False)

        print('done')

    print('\nSetting %s as baseline\n' % (baseline.split('\n')[0]))
    Sw_info_table = Sw_info_table.sort_values(['Time'])

    """
    Calculate Mean value for each test step for each variable, df for each variable goes in ResultsMean
    which has Sw_label as columns and test steps as rows  
    
    If there are n variables, there will be n ResultsMean for each, all of them added to a dict - MeanDfs
      
    """

    for vno, Var in enumerate(SigListConf):
        vno_total = len(SigListConf)
        print("Processing %s - label # %d/%d..." % (Var, vno + 1, vno_total), end='')
        # Populate empty dataframe
        ResultsMean = pd.DataFrame({'TestStepLabel': TestStepLabels}, index=TestStepLabels)
        ResultsMean['TestStepLabel'] = ResultsMean.index

        for id_key in LogDataset.keys():
            varList = ['timestamps', 'TestStepLabel'] + [Var]
            TestDfwithLabel = LogDataset[id_key][varList].copy(deep=True)
            steps_filter = TestDfwithLabel['TestStepLabel'].isin(TestStepLabels)
            MeanValList = []
            FLC_grps = TestDfwithLabel[steps_filter].groupby('TestStepLabel')

            for StepGrp in FLC_grps:
                step = StepGrp[0]
                testStepDf = StepGrp[1]
                testStepDf = testStepDf.sort_index()

                if len(testStepDf) > 750:  #
                    idx = testStepDf[testStepDf['timestamps'].diff(1) > 10].index.values
                    df1 = testStepDf[testStepDf.index.values < idx]
                    df2 = testStepDf[testStepDf.index.values >= idx]
                    mn1, stdev1 = MeanVar_NPercentile(df1[Var], start_prctle, end_prctle)
                    mn2, stdev2 = MeanVar_NPercentile(df2[Var], start_prctle, end_prctle)
                    if stdev1 >= stdev2:
                        FuelMean = mn1
                    else:
                        FuelMean = mn2
                else:
                    FuelMean, FuelStdDev = MeanVar_NPercentile(testStepDf[Var], start_prctle, end_prctle)

                MeanValList.append([step, FuelMean])
                meanFuelDf = pd.DataFrame(MeanValList, columns=['TestStepLabel', id_key])
            ResultsMean = pd.concat([ResultsMean, meanFuelDf.set_index('TestStepLabel')], axis=1)
        MeanDfs[Var] = ResultsMean
        print('done')

    """
    Do hypothesis test to check if mean value of 2 samples are same for between the baseline and the other logs 
    Steps involved are :
    I. For every release other than baseline :
        II. For every variable : 
            a. create a dictionary which has mean value for each test steps of baseline (percentile from conf.py applied)
            b. from data set of log from loop I(SW) and loop II.(variable):
                    i. Loop through each teststep step and extract the test  sample
                    ii. Do a hypethesis test of the above sample with corresponding sample from baseline dict (step a.)
                    by function ttest_ind(test_sample, baseline_sample)
                    we do not do test if mean value of both are exactly same as function would retun a Nan
                   
    
    bdata is populated with variables as rows and test step labels as columns 
    If there are N logs to analysed there will N-1 comparisons against baseline,
    hence n-1 copies of bdata , all stored in dictionary BaselinePData as individual dataframne              
    
    """

    BaselinePData = dict()
    test_keys = list(set(LogDataset.keys()) - set([baseline]))

    for id_key in test_keys:
        bdata = pd.DataFrame(columns=['Variable'] + TestStepLabels)

        for vno, Var in enumerate(SigListConf):

            BaselineVarData = dict()
            varList = ['timestamps', 'TestStepLabel'] + [Var]
            TestDfwithLabel = LogDataset[baseline][varList].copy(deep=True)
            steps_filter = TestDfwithLabel['TestStepLabel'].isin(TestStepLabels)
            FLC_grps = TestDfwithLabel[steps_filter].groupby('TestStepLabel')
            for StepGrp in FLC_grps:
                grp_name = StepGrp[0]
                grp_data = StepGrp[1]
                grp_data = grp_data.sort_index()
                BaselineVarData[grp_name] = grp_data

            TestDfwithLabel = LogDataset[id_key][varList].copy(deep=True)
            filt_cond = TestDfwithLabel['TestStepLabel'].str.contains('FLC_SteadyState')
            filt_cond = filt_cond | TestDfwithLabel['TestStepLabel'].str.contains('StepResponse_SteadyState1200')
            filt_cond = filt_cond | TestDfwithLabel['TestStepLabel'].str.contains('StepResponse_SteadyState1900')
            FLC_grps = TestDfwithLabel[filt_cond].groupby('TestStepLabel')
            pvals = [Var]
            pval_cols = ['Variable']

            for StepGrp in FLC_grps:

                step = StepGrp[0]
                if (step not in BaselineVarData.keys()):
                    continue
                testStepDf = StepGrp[1]
                testStepDf = testStepDf.sort_index()
                baseline_sample = BaselineVarData[step][Var]
                test_sample = testStepDf[Var]
                baseline_sample = get_NPercentile(baseline_sample, start_prctle, end_prctle)
                test_sample = get_NPercentile(test_sample, start_prctle, end_prctle)
                if ((baseline_sample.mean() - test_sample.mean()) != 0):
                    ttest, pval = ttest_ind(test_sample, baseline_sample)
                else:
                    pval = 0
                pvals.append(round(pval, 3))
                pval_cols.append(step)
                df = pd.DataFrame(columns=pval_cols)
                df.loc[0] = pvals
            bdata = bdata.append(df)
        BaselinePData[id_key] = bdata

    """   
    Tabulate fault duration for each data set 
    """
    # The test logs are read again individually and for each log, active fault duration is summed up

    FaultStat_flc = GetStepFltDuration(testlogDir, 'FLC')
    FaultStat_step = GetStepFltDuration(testlogDir, 'StepResponse')

    # Remove fault code 0 (no fault) from list
    FaultStat_flc = FaultStat_flc[FaultStat_flc.Faults != 0]
    FaultStat_flc = FaultStat_flc.fillna(0)
    FaultStat_flc = FaultStat_flc.replace({"Faults": fltdict})
    FaultStat_step = FaultStat_step[FaultStat_step.Faults != 0]
    FaultStat_step = FaultStat_step.fillna(0)
    # Convert numeric fault code to fault names from dictionary
    FaultStat_step = FaultStat_step.replace({"Faults": fltdict})

    """
    Write to excel files - Raw summary data and Baselined summary data 
    """
    # Packing all dataframes and dictionaries into a list for function call to write to excel
    tables = [MeanDfs, Sw_info_table, Signaltracker, FaultStat_flc, FaultStat_step, BaselinePData]
    # Packing all variables into a list for function call to write to excel
    parameters = [highlight_thres, baseline, SignalGroups, start_prctle, end_prctle]
    # Final step - write to excel
    writetoExeclSheet(SummaryExcelFilename, tables, parameters)
    input("Results saved in %s .. Press any key to exit" % SummaryExcelFilename)


if __name__ == '__main__':
    main()
