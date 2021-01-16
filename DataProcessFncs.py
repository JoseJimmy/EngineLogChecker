import json
from tkinter import filedialog

import numpy as np
import pandas as pd

from InputProcessFncs import GetFaultCodesfromA2l, getTestLogFileNames, FetchMdfHeader, GetDatafromMdf_asDF


def TestRegimeMarker(Pdl):
    TestReg = 'Warmup/Idling'
    if (Pdl > 85): TestReg = 'FLC'
    if (Pdl > 75 and Pdl <= 85): TestReg = 'StepResponse'
    return TestReg


def TestStepLabelMarker(Espd, Espd_dt, fuel_dt, TestRegime):
    label = TestRegime
    if (TestRegime == 'FLC'):
        if (Espd_dt < -0.1):
            label = 'FLC_RampDownto_%sRpm' % (str(Espd))
        if (Espd_dt == 0):
            label = 'FLC_SteadyState_%sRpm' % str(Espd)
        if (Espd_dt > 0.1 and fuel_dt > 10):
            label = 'FLC_RampUp'

    if (TestRegime == 'StepResponse'):
        if (Espd_dt == 0 and fuel_dt < 20):
            label = 'StepResponse_SteadyState' + str(Espd)
        if (Espd_dt > 0.3):
            label = 'StepResponse_RampUp'
        if (Espd_dt < -0.1):
            label = 'StepResponse_RampDown'

    return str(label)


def LabelTestDataDf(df):
    if 'timestamps' not in df:
        df.insert(loc=0, column='timestamps', value=df.index)

    df['Engine_speed_filt'] = (df['Engine_speed'].round(-1) / 100).astype(int) * 100
    df['Pedal_Value_filt'] = (df['Pedal.Value'] / 2).astype(int) * 2
    df['Actual_fuel_value_filt'] = (df['Actual_fuel_value'] / 15).astype(int) * 15

    df['Engine_speed_filt_dt'] = df[['Engine_speed_filt']].diff(2).fillna(0)
    df['Engine_speed_filt_dt'] = df['Engine_speed_filt_dt'].rolling(180).mean()
    df['Actual_fuel_value_filt_dt'] = 10 * (df[['Actual_fuel_value_filt']].diff(2))
    df['Actual_fuel_value_filt_dt'] = df[['Actual_fuel_value_filt_dt']].rolling(80).mean().fillna(0)

    df = df.fillna(0)
    if 'TestRegime' not in df:
        df['TestRegime'] = df.apply(lambda x: TestRegimeMarker(x.Pedal_Value_filt), axis=1)

    if 'TestStepLabel' not in df:
        df['TestStepLabel'] = df.apply(
            lambda x: TestStepLabelMarker(x.Engine_speed_filt, x.Engine_speed_filt_dt, x.Actual_fuel_value_filt_dt,
                                          x.TestRegime), axis=1)
    return df


def MeanVar_NPercentile(data, start_perecentile=0.2, end_perecentile=0.8):
    start = int(len(data) * start_perecentile)
    end = int(len(data) * end_perecentile)
    d_Mean = data.iloc[start:end].mean().round(2)
    d_StdDev = 2 * data.iloc[start:end].std().round(2)
    return d_Mean, d_StdDev


def get_NPercentile(data, start_perecentile=0.2, end_perecentile=0.8):
    start = int(len(data) * start_perecentile)
    end = int(len(data) * end_perecentile)
    return data.iloc[start:end]


def GetStepFltDuration(testlogDir, TestRegime='FLC'):
    print("\n")
    if (TestRegime not in ['FLC', 'StepResponse']):
        TestRegime = 'FLC'
    flt_lst = []
    for i in range(50):
        flt_lst.append('F_M_Log_index_nvv[%d]' % i)
    globalFaults = pd.DataFrame({'Faults': 0}, index=[0])
    datfiles = getTestLogFileNames(testlogDir)

    for file in datfiles:
        sig_list = flt_lst + ['Engine_speed', 'Pedal.Value', 'Actual_fuel_value']
        header = FetchMdfHeader(file)
        A2l = header['A2L']
        print('Tabulating %s active Faults duration for %s..' % (TestRegime, A2l), end='')
        fdf = GetDatafromMdf_asDF(file, sig_list, SampleTime=0.05)
        fdf = LabelTestDataDf(fdf)
        flt_df = fdf[fdf.TestRegime == TestRegime].copy(deep=True)
        temp = np.unique(flt_df[flt_lst].values, return_counts=True)
        temp = pd.DataFrame({'Faults': temp[0], A2l: temp[1] * 0.05})
        globalFaults = pd.merge(globalFaults, temp, how='outer', on='Faults')
        print('Done')
    return (globalFaults)


def CreateFltDict(filename):
    try:
        with open(filename, 'r') as file:
            fltdict = json.load(file)
            fltdict = {int(k): v for k, v in fltdict.items()}
    except:
        print("Select A2L file for extracting Fault Code dictionary")
        a2lFilename = filedialog.askopenfilename(title="Select A2L file (for Fault code decoding)",
                                                 filetypes=(("txt files", "*.A2L"), ("all files", "*.*")))

        with open(filename, 'w') as file:
            fltdict = GetFaultCodesfromA2l(a2lFilename)
            json.dump(fltdict, file)
            print("Selected - %s\n" % a2lFilename.replace('/', '\\'))

    return fltdict
