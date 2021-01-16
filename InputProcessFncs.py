import datetime
import os
import re

import pandas as pd
from asammdf import MDF


def getTestLogFileNames(dir):
    datFiles = []
    ## List of file
    for file in os.listdir(dir):
        if file.endswith(".dat"):
            datFiles.append(os.path.join(dir, file))
    datFiles.sort(key=os.path.getctime)
    return datFiles


def GetDatafromMdf_asDF(filename, SigList, SampleTime=0.01, EncodeEnums=True):
    ## Local helper
    def cleanEnumString(string):
        return string.decode().split(r'\x00')[0].strip().strip('\x00')

    ## Function body
    tempMDF = MDF()
    sigs = []
    with MDF(filename, remove_source_from_channel_names=True) as mdf:
        for var in SigList:
            try:
                # get group and Index from channel_db
                grp_idx = mdf.channels_db[var][0]
                # Fetch signal as data object
                sigs.append(mdf.get(group=grp_idx[0], index=grp_idx[1]))
                # Append to mdf
            except:
                continue

    tempMDF.append(sigs)
    df = tempMDF.to_dataframe(raster=SampleTime)

    types = df.apply(lambda x: pd.api.types.infer_dtype(x.values))
    for col in types[types == 'bytes'].index:  # String/Enum
        df[col] = df[col].apply(cleanEnumString)

    if (EncodeEnums == True):
        types = df.apply(lambda x: pd.api.types.infer_dtype(x.values))
        for col in types[types == 'string'].index:  # String/Enum
            df[col] = df[col].astype('category')
            df[col] = df[col].cat.codes

    return df


def FetchMdfHeader(filename):
    with MDF(filename, remove_source_from_channel_names=True) as mdf:
        header = mdf.header.comment

    Time = r'(?<=Date-time:).*?(?=\r)'
    Time = re.findall(Time, header)[0].strip()
    A2L = r'(?<=A2L file:).*?(?=\r)'
    A2L = re.findall(A2L, header)[0].split('=')[1].strip()
    Sw_id = r'(?<=\(RAM\):).*?(?=\r)'
    Sw_id = re.findall(Sw_id, header)[0].split('"')[1].strip()
    header = dict()
    header['Time'] = datetime.datetime.strptime(Time, '%m/%d/%Y %I:%M:%S %p')
    header['A2L'] = A2L
    header['Sw_id'] = Sw_id
    header['FileName'] = filename.split('\\')[1]
    return header


def GetSignalsLogged(tracker_df, filename):
    mdf = MDF(filename, remove_source_from_channel_names=True)
    filename = filename.split('\\')[1]
    sigs_in_mdf = list(mdf.channels_db.keys())
    sigs_in_tracker = list(tracker_df.Signals.values)
    diff = list(set(sigs_in_mdf).difference(set(sigs_in_tracker)))
    for item in diff:
        tracker_df = tracker_df.append({'Signals': item}, ignore_index=True).fillna(0)  # , ignore_index=True)
    tracker_df = tracker_df.sort_values(['Signals']).reset_index(drop=True)
    tracker_df[filename] = 0
    tracker_df.loc[tracker_df['Signals'].isin(sigs_in_mdf), filename] = 1
    return tracker_df


def GetFaultCodesfromA2l(A2lFilename):
    import re
    a2lfile = []
    with open(A2lFilename, 'r') as content_file:
        content = content_file.read()
    q = r'(?<=(TAB_VERB 2243)).*?(?=(/end COMPU_VTAB))'
    regex = re.compile(q, re.DOTALL)
    match = regex.search(content)
    res = match.group(0)
    faultCodeDict = dict()
    for line in res.split('\n')[1:-1]:
        code = int(line.strip().split()[0])
        name = line.strip().split('"')[1]
        faultCodeDict[code] = name
    return faultCodeDict
