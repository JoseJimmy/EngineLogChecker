import tkinter
from tkinter import filedialog
import pandas as pd
from os import makedirs,path
from configparser import ConfigParser
from Df_ProcessFns import MeanVar_NPercentile,LabelTestDataDf,CreateFltDict, GetStepFltDuration
from Mdf_InterfaceFns import GetSignalsLogged,GetDatafromMdf_asDF,FetchMdfHeader,getTestLogFileNames
from Excel_InterfaceFns import writetoExeclSheet
pd.set_option('use_inf_as_na', True)

def main():
    """
    EP_Main_01 : Initialise data structres /Read parameters
    """

    parser = ConfigParser()
    parser.read("conf.py")


#EP_Main_01_01
    SignalGroups = dict()
    for k, v in parser.items('SignalGroups'):
        signalGrp = k.strip()
        SignalGroups[k] = []
        for var in v.split(','):
            SignalGroups[k].append(var.strip())

#EP_Main_01_02
    Settings = dict()
    for k, v in parser.items('Settings'):
        Settings[k] = v.strip()

    start_prctle = float(Settings['sample_start_prctle'])
    end_prctle = float(Settings['sample_end_prctle'])
    highlight_thres = float(Settings['deviation_highlight_thres_perc'])
    DataDump = bool(Settings['datadump'])

    # EP_Main_01_03

    TestStepLabels = ['FLC_SteadyState_900Rpm', 'FLC_SteadyState_1000Rpm', 'FLC_SteadyState_1100Rpm',
                      'FLC_SteadyState_1200Rpm',
                      'FLC_SteadyState_1300Rpm', 'FLC_SteadyState_1400Rpm', 'FLC_SteadyState_1500Rpm',
                      'FLC_SteadyState_1600Rpm',
                      'FLC_SteadyState_1700Rpm', 'FLC_SteadyState_1800Rpm', 'FLC_SteadyState_1900Rpm',
                      'FLC_SteadyState_2000Rpm',
                      'StepResponse_SteadyState1200', 'StepResponse_SteadyState1900']
    Sw_info_table = pd.DataFrame([])
    Signaltracker = pd.DataFrame([], columns=['Signals'])
    MeanDfs = dict()
    VarDfs = dict()
    LogDataset = dict()

    SigList = ['Engine_speed', 'Pedal.Value']
    for item in SignalGroups.keys():
        SigList += SignalGroups[item]
    """
    EP_Main_02 : GUI Stuff - Get file/folder/baseline info from user  and set up folder structure and create filenames   
    """

    tkinter.Tk().withdraw()

    print("\nSelect folder location of MDF/DAT files ")
    testlogDir = filedialog.askdirectory(title="Select Test log Directory ")
    txt=testlogDir.replace('/','\\')
    print("Selected - %s\n"%txt)
    datfiles = getTestLogFileNames(testlogDir)
    print("Select a dat file to set as baseline file ")

    baselineFile = filedialog.askopenfilename(initialdir=testlogDir, title="Select a Log file to use as baseline",
                                              filetypes=(("dat files", "*.dat"), ("all files", "*.*")))
    baselineFile = path.basename(baselineFile)
    txt=baselineFile.replace('/','\\')
    print("Selected - %s\n"%txt)

    ReportPath = path.join(testlogDir, 'report')
    if(DataDump==True):
        DataDumpPath = path.join(ReportPath, 'data')
        try:
            makedirs(DataDumpPath)
        except:
            pass
    try:
        makedirs(ReportPath)
    except:
        pass

    """
    EP_Main_03 : Read data from MDF / Label it and populate Fault dictionary
    """
    rawExcelFileName = path.join(ReportPath, 'EpotData_raw.xlsx')
    baselinedExcelFileName = path.join(ReportPath, 'EpotData_baselined.xlsx')
    fltdictPath = path.join(ReportPath, 'Fault_dict.txt')
    fltdict = CreateFltDict(fltdictPath)

    for idx, filename in enumerate(datfiles):
        print("Getting Data and Labelling - %s...." % path.basename(filename),end='')
        Signaltracker = GetSignalsLogged(Signaltracker, filename)
        header = FetchMdfHeader(filename)
        SW_id = header['A2L']
        curfile = path.basename(filename)
        if curfile == baselineFile:
            SW_id = SW_id + '\n(Baseline)'
            baseline = SW_id

        row = pd.DataFrame(header, index=[idx])
        Sw_info_table = Sw_info_table.append(row)
        temp_df = GetDatafromMdf_asDF(filename, SigList, SampleTime=0.05)  # getting
        temp_df = LabelTestDataDf(temp_df)
        temp_df["TestStepLabel_code"] = temp_df["TestStepLabel"].astype('category')
        temp_df["TestStepLabel_code"] = temp_df["TestStepLabel_code"].cat.codes
        temp_df["TestRegime_code"] = temp_df["TestRegime"].astype('category')
        temp_df["TestRegime_code"] = temp_df["TestRegime_code"].cat.codes

        LogDataset[SW_id] = temp_df.copy(deep=True)

        if (DataDump == True):
            csv_filename=header['A2L']+'.csv'
            csv_filename = path.join(DataDumpPath, csv_filename)
            temp_df.to_csv(csv_filename,index=False)

        print('done')

    print('\nSetting %s as baseline\n' % (baseline.split('\n')[0]))
    Sw_info_table = Sw_info_table.sort_values(['Time'])



    """
    EP_Main_04 : For each variable, Create sepearet dataframe for individual dat files and calculate Mean/Var  
    """


    for VarGroupName in SignalGroups.keys():
        print(' ')
        for vno, Var in enumerate(SignalGroups[VarGroupName]):

            vno_total = len(SignalGroups[VarGroupName])
            print("Processing %s - label# %d/%d of SignalGroup %s .." % (Var, vno + 1, vno_total, VarGroupName), end='')
            ResultsMean = pd.DataFrame({'TestStepLabel': TestStepLabels}, index=TestStepLabels)
            ResultsVar = pd.DataFrame({'TestStepLabel': TestStepLabels}, index=TestStepLabels)
            ResultsMean['TestStepLabel'] = ResultsMean.index
            ResultsVar['TestStepLabel'] = ResultsVar.index


            for id_key in LogDataset.keys():
                # data_df = LogDataset[id_key][Var].copy(Deep=True)
                varList = ['timestamps','TestStepLabel'] + [Var]
                TestDfwithLabel = LogDataset[id_key][varList].copy(deep=True)

                filt_cond = TestDfwithLabel['TestStepLabel'].str.contains('FLC_SteadyState_')
                filt_cond = filt_cond | TestDfwithLabel['TestStepLabel'].str.contains('StepResponse_SteadyState')
                MeanValList, _2StdDevValList = [], []
                FLC_grps = TestDfwithLabel[filt_cond].groupby('TestStepLabel')

                for StepGrp in FLC_grps:
                    step = StepGrp[0]
                    testStepDf = StepGrp[1]
                    testStepDf = testStepDf.sort_index()

                    if len(testStepDf) > 750: #
                        idx = testStepDf[testStepDf['timestamps'].diff(1) > 10].index.values
                        df1 = testStepDf[testStepDf.index.values < idx]
                        df2 = testStepDf[testStepDf.index.values >= idx]
                        mn1, stdev1 = MeanVar_NPercentile(df1[Var], start_prctle, end_prctle)
                        mn2, stdev2 = MeanVar_NPercentile(df2[Var], start_prctle, end_prctle)
                        if stdev1 >= stdev2:
                            FuelMean = mn1
                            FuelStdDev = stdev1
                        else:
                            FuelMean = mn2
                            FuelStdDev = stdev2
                    else:
                        FuelMean, FuelStdDev = MeanVar_NPercentile(testStepDf[Var], start_prctle, end_prctle)

                    MeanValList.append([step, FuelMean])
                    _2StdDevValList.append([step, FuelStdDev])

                    meanFuelDf = pd.DataFrame(MeanValList, columns=['TestStepLabel', id_key])
                    _2StdDevFuelDf = pd.DataFrame(_2StdDevValList, columns=['TestStepLabel', id_key]).fillna('No Data')

                ResultsMean = pd.concat([ResultsMean, meanFuelDf.set_index('TestStepLabel')], axis=1)
                ResultsVar = pd.concat([ResultsVar, _2StdDevFuelDf.set_index('TestStepLabel')], axis=1)
            MeanDfs[Var] = ResultsMean
            VarDfs[Var] = ResultsVar
            print('done')
    """
    EP_Main_04 : Tabulate fault duration for each data set 
    """

    FaultStat_flc = GetStepFltDuration(testlogDir, 'FLC')
    FaultStat_step = GetStepFltDuration(testlogDir, 'StepResponse')

    FaultStat_flc = FaultStat_flc[FaultStat_flc.Faults != 0]
    FaultStat_flc = FaultStat_flc.fillna(0)
    FaultStat_flc = FaultStat_flc.replace({"Faults": fltdict})

    FaultStat_step = FaultStat_step[FaultStat_step.Faults != 0]
    FaultStat_step = FaultStat_step.fillna(0)
    FaultStat_step = FaultStat_step.replace({"Faults": fltdict})

    tables = [MeanDfs,VarDfs,Sw_info_table,Signaltracker,FaultStat_flc,FaultStat_step]
    parameters = [highlight_thres,baseline,SignalGroups]
    """
    EP_Main_05 : Write to excel files - Raw summary data and Baselined summary data 
    """

    writetoExeclSheet(baselinedExcelFileName,tables,parameters,Rawdata=False)
    writetoExeclSheet(rawExcelFileName,tables,parameters,Rawdata=True)


if __name__ == '__main__':
    main()
