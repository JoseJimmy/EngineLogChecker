import pandas as pd
import numpy as np
import json
from tkinter import filedialog

#
#
# def FetchMdfHeader(filename):
#     with MDF(filename, remove_source_from_channel_names=True) as mdf:
#         header = mdf.header.comment
#
#     Time=  r'(?<=Date-time:).*?(?=\r)'
#     Time = re.findall(Time,header)[0].strip()
#     A2L =  r'(?<=A2L file:).*?(?=\r)'
#     A2L = re.findall(A2L,header)[0].split('=')[1].strip()
#     Sw_id = r'(?<=\(RAM\):).*?(?=\r)'
#     Sw_id = re.findall(Sw_id,header)[0].split('"')[1].strip()
#     header=dict()
#     header['Time']=datetime.datetime.strptime(Time, '%m/%d/%Y %I:%M:%S %p')
#     header['A2L']=A2L
#     header['Sw_id']=Sw_id
#     header['FileName'] = filename.split('\\')[1]
#     return header

# def GetSignalsInMdf(tracker_df,filename):
#     mdf = MDF(filename, remove_source_from_channel_names=True)
#     filename = filename.split('\\')[1]
#     sigs_in_mdf = list(mdf.channels_db.keys())
#     sigs_in_tracker=list(tracker_df.Signals.values)
#     diff = list(set(sigs_in_mdf).difference(set(sigs_in_tracker)))
#     for item in diff:
#         tracker_df=tracker_df.append({'Signals':item},ignore_index=True).fillna(0)#, ignore_index=True)
#     tracker_df = tracker_df.sort_values(['Signals']).reset_index(drop=True)
#     tracker_df[filename]=0
#     tracker_df.loc[tracker_df['Signals'].isin(sigs_in_mdf),filename]=1
#     return tracker_df
from Mdf_InterfaceFns import GetFaultCodesfromA2l, getTestLogFileNames, FetchMdfHeader, GetDatafromMdf_asDF


def TestRegimeMarker(Pdl):
    TestReg = 'Warmup/Idling'
    if(Pdl > 85): TestReg =  'FLC'
    if (Pdl >75 and Pdl <= 85): TestReg =  'StepResponse'
    return TestReg


def TestStepLabelMarker(Espd, Espd_dt,Espd_dt2, TestRegime):
    label = TestRegime
    if (TestRegime == 'FLC'):
        if (Espd_dt < -0.1):
            label = 'FLC_RampDownto_%sRpm'%(str(Espd))
        if (Espd_dt == 0):
            label = 'FLC_SteadyState_%sRpm'%str(Espd)
        if (Espd_dt > 0.1 and Espd_dt2 > 0.05):
            label = 'FLC_RampUp'

    if (TestRegime == 'StepResponse' and Espd_dt2 > 0.1):
        if (Espd_dt > 0.3 ):
            label = 'StepResponse_RampUp'
        if (Espd_dt < 0.1):
            label = 'StepResponse_RampDown'
        if (Espd_dt == 0 and Espd>1000):
            label = 'StepResponse_SteadyState' + str(Espd)
    return str(label)


def LabelTestDataDf(df):

    if 'timestamps' not in df:
        df.insert(loc=0, column='timestamps', value=df.index)

    df['Engine_speed_filt'] = (df['Engine_speed'].round(-1) / 100).astype(int) * 100
    df['Pedal_Value_filt'] = (df['Pedal.Value']/ 2).astype(int) * 2
    df['Engine_speed_filt_dt'] = df[['Engine_speed_filt']].diff(2).fillna(0)
    df['Engine_speed_filt_dt'] = df['Engine_speed_filt_dt'].rolling(200).mean()
    df['Engine_speed_filt_dt2'] = 10*(df[['Engine_speed_filt_dt']].diff(2))
    df['Engine_speed_filt_dt2'] = df[['Engine_speed_filt_dt2']].rolling(130).mean().fillna(0)

    df = df.fillna(0)
    if 'TestRegime' not in df:
        df['TestRegime'] = df.apply(lambda x: TestRegimeMarker(x.Pedal_Value_filt), axis=1)

    if 'TestStepLabel' not in df:
        df['TestStepLabel'] = df.apply(lambda x: TestStepLabelMarker( x.Engine_speed_filt,x.Engine_speed_filt_dt,x.Engine_speed_filt_dt2, x.TestRegime), axis=1)
    return df


def MeanVar_NPercentile(data,  start_perecentile = 0.2,end_perecentile = 0.8):
    start = int(len(data) * start_perecentile)
    end = int(len(data) * end_perecentile)
    d_Mean = data.iloc[start:end].mean().round(2)
    d_StdDev = 2 * data.iloc[start:end].std().round(2)
    return d_Mean,d_StdDev


def GetStepFltDuration(testlogDir,TestRegime='FLC'):
    print("\n")
    if(TestRegime not in ['FLC','StepResponse']):
        TestRegime = 'FLC'
    flt_lst=[]
    for i in range(50):
        flt_lst.append('F_M_Log_index_nvv[%d]' % i)
    globalFaults = pd.DataFrame({'Faults':0},index=[0])
    datfiles = getTestLogFileNames(testlogDir)

    for file in datfiles:
        sig_list= flt_lst+ ['Engine_speed', 'Pedal.Value']
        header = FetchMdfHeader(file)
        A2l = header['A2L']
        print('Tabulating %s active Faults duration for %s..'%(TestRegime,A2l),end='')
        fdf = GetDatafromMdf_asDF(file, sig_list, SampleTime=0.05)
        fdf=LabelTestDataDf(fdf)
        flt_df = fdf[fdf.TestRegime==TestRegime].copy(deep=True)
        temp = np.unique(flt_df[flt_lst].values, return_counts=True)
        temp = pd.DataFrame({'Faults':temp[0],A2l:temp[1]*0.05})
        globalFaults = pd.merge(globalFaults, temp,how='outer',on='Faults')
        print('Done')
    return(globalFaults)


# def writetoExeclSheet(Filename,tables,parameters,Rawdata=False):
#     MeanDfs,VarDfs,Sw_info_table,Signaltracker,FaultStat_flc,FaultStat_step = tables
#     highlight_thres,baseline,SignalGroups = parameters
#
#     print('Writing to Excel...', end='')
#
#
#     with pd.ExcelWriter(Filename) as excel_writer:
#         workbook = excel_writer.book
#         cell_format = workbook.add_format({'bold': True, 'italic': True})
#         perc_format = workbook.add_format()
#         if (Rawdata == False):
#             perc_format.set_num_format('0.00%')
#
#         baseline_percformat = workbook.add_format({
#                 'bold': True,
#                 'text_wrap': True,
#                 'color': 'green',
#             })
#         if(Rawdata==False):
#             baseline_percformat.set_num_format('0.00%')
#
#         baseline_format = workbook.add_format({
#             'bold': True,
#             'text_wrap': True,
#             'color': 'green'})
#
#         header_format = workbook.add_format({
#             'bold': True,
#             'text_wrap': True,
#             'valign': 'bottom',
#             'rotation': 90,
#             'border': 1})
#         valueOOR_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
#
#
#
#         for grpName in SignalGroups.keys():
#             nvars = len(SignalGroups[grpName])
#             startrow = 2
#
#             for idx, var in enumerate(SignalGroups[grpName]):
#                 meandf = MeanDfs[var].copy(deep=True)
#                 vardf = VarDfs[var].copy(deep=True)
#                 nrow, ncol = meandf.shape
#
#                 if(Rawdata==False):
#                     meandf.iloc[:, 1:] = meandf.iloc[:, 1:].div(meandf[baseline], axis=0)
#
#
#
#                 meandf = meandf.fillna('No Data')
#                 meandf.to_excel(excel_writer, index_label=var, sheet_name=grpName, index=False, header=False,
#                                 startrow=startrow, startcol=0)
#
#                 vardf.iloc[:, 1:].to_excel(excel_writer, sheet_name=grpName, index=False, header=False,
#                                            startrow=startrow, startcol=ncol + 2)
#
#                 worksheet = excel_writer.sheets[grpName]
#
#                 worksheet.write_string(startrow - 1, 0, var, cell_format)
#
#                 if (Rawdata == False):
#                     worksheet.conditional_format(startrow, 1, startrow + nrow - 1, ncol - 1,
#                                                  {'type': 'cell', 'criteria': '>=',
#                                                   'value': (100 + highlight_thres) / 100,
#                                                   'format': valueOOR_fmt})
#                     worksheet.conditional_format(startrow, 1, startrow + nrow - 1, ncol - 1, {'type': 'cell',
#                                                                                               'criteria': '<=',
#                                                                                               'value': (
#                                                                                                                    100 - highlight_thres) / 100,
#                                                                                               'format': valueOOR_fmt})
#                 startrow = startrow + nrow + 2
#
#             headCols = list(meandf.columns) + [' ', ' '] + list(meandf.drop(['TestStepLabel'], axis=1).columns)
#             # Add a header format.
#             for col_num, value in enumerate(headCols):
#                 worksheet.write(0, col_num, value, header_format)
#             worksheet.set_row(0, 140, header_format)
#             worksheet.set_column(1, ncol + 1, 8, perc_format)
#             worksheet.set_column('A:A', 31)
#             worksheet.set_column('B:Z', 8)
#             baseline_pos = meandf.columns.get_loc(baseline)
#             worksheet.set_column(baseline_pos, baseline_pos, 8, baseline_percformat)
#
#         Sw_info_table.to_excel(excel_writer, sheet_name='Sw_info_table', index=False)
#         worksheet = excel_writer.sheets['Sw_info_table']
#         worksheet.set_column('A:B', 30)
#         worksheet.set_column('C:D', 60)
#
#         Signaltracker.to_excel(excel_writer, sheet_name='TestlogSignalTracker', index=False)
#         worksheet = excel_writer.sheets['TestlogSignalTracker']
#         for col_num, value in enumerate(Signaltracker.columns):
#             worksheet.write(0, col_num, value, header_format)
#
#         nrow, ncol = FaultStat_flc.shape
#         label = 'Fault Codes and Cumulative duration(sec) during FLC phase of test '
#         FaultStat_flc.to_excel(excel_writer, index_label=label, sheet_name='FaultStats', index=False, header=False,
#                                startrow=2, startcol=0)
#         worksheet = excel_writer.sheets['FaultStats']
#         worksheet.write_string(1, 0, label, cell_format)
#
#         worksheet.conditional_format(2, 1, nrow + 1, ncol - 1,
#                                      {'type': 'cell', 'criteria': '>', 'value': 0, 'format': valueOOR_fmt})
#
#         label = 'Fault Codes and Cumulative duration(sec) during Step Response phase of test '
#         FaultStat_step.to_excel(excel_writer, index_label=label, sheet_name='FaultStats', index=False, header=False,
#                                 startrow=nrow + 4,
#                                 startcol=0)
#         worksheet.write_string(nrow + 3, 0, label, cell_format)
#
#         worksheet.write_string(startrow - 1, 0, var, cell_format)
#
#         nrow1, ncol = FaultStat_step.shape
#         worksheet.conditional_format(nrow + 4, 1, nrow + 4 + nrow1 - 1, ncol - 1,
#                                      {'type': 'cell', 'criteria': '>', 'value': 0, 'format': valueOOR_fmt})
#         headCols = list(FaultStat_step.columns)
#         # Add a header format.
#         for col_num, value in enumerate(headCols):
#             worksheet.write(0, col_num, value, header_format)
#         worksheet.set_row(0, 140, header_format)
#         worksheet.set_column('B:Z', 8)
#         worksheet.set_column('A:A', 60)
#         worksheet.set_column(baseline_pos, baseline_pos, 8, baseline_format)
#
#     print("done")


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
            print("Selected - %s\n"%a2lFilename.replace('/', '\\'))

    return fltdict

