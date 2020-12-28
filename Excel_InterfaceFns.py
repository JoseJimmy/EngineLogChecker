
import pandas as pd
"""
Function for writing results into excel file
writetoExeclSheet(Filename,tables,parameters,Rawdata=False) 

"""

def writetoExeclSheet(Filename,tables,parameters,Rawdata=False):
    """

    :param Filename: > names of the excel file
    :param tables:  Tables of data to be written > MeanDfs,VarDfs,Sw_info_table,Signaltracker,FaultStat_flc,FaultStat_step
    :param parameters: Meta Parameters > highlight_thres,baseline,SignalGroups
    :return:
    """
    MeanDfs,VarDfs,Sw_info_table,Signaltracker,FaultStat_flc,FaultStat_step = tables
    highlight_thres,baseline,SignalGroups = parameters


    if(Rawdata): # Check if data needs top be baselined
        print('Writing to raw summary data Excel to %s...'%Filename.replace('/','\\'), end='')
    else:
        print('Writing to baselined summary data to %s...'%Filename.replace('/','\\'), end='')


    with pd.ExcelWriter(Filename) as excel_writer: #creates a file object for the excel file
        workbook = excel_writer.book
        cell_format = workbook.add_format({'bold': True, 'italic': True})
        perc_format = workbook.add_format()

        if (Rawdata == False):# Do not apply % formatting for non-baseline file
            perc_format.set_num_format('0.00%')

        # Cell format definition
        baseline_percformat = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'color': 'green',
            })
        if(Rawdata==False):
            baseline_percformat.set_num_format('0.00%')

        baseline_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'color': 'green'})

        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'bottom',
            'rotation': 90,
            'border': 1})
        # higlight values above allowed deviation in baseline sheet
        valueOOR_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})



        for grpName in SignalGroups.keys(): # Cycle through each signal group, one sheet per group
            nvars = len(SignalGroups[grpName])
            startrow = 2

            for idx, var in enumerate(SignalGroups[grpName]): # cycle through each variable in the group
                meandf = MeanDfs[var].copy(deep=True)
                vardf = VarDfs[var].copy(deep=True)
                nrow, ncol = meandf.shape

                if(Rawdata==False): # if baseline option is selected, divide values by its baseline column value
                    meandf.iloc[:, 1:] = meandf.iloc[:, 1:].div(meandf[baseline], axis=0)



                meandf = meandf.fillna('No Data') # filling out missing values

                #Write mean values  to excel file
                meandf.to_excel(excel_writer, index_label=var, sheet_name=grpName, index=False, header=False,
                                startrow=startrow, startcol=0)

                #Write 2x standard deviation to excel file
                vardf.iloc[:, 1:].to_excel(excel_writer, sheet_name=grpName, index=False, header=False,
                                           startrow=startrow, startcol=ncol + 2)

                # Start initilisation of sheet to apply formatting
                worksheet = excel_writer.sheets[grpName]
                worksheet.write_string(startrow - 1, 0, var, cell_format)

                #Apply formatting, formatting is different if baslined sheet is being written
                if (Rawdata == False):
                    worksheet.conditional_format(startrow, 1, startrow + nrow - 1, ncol - 1,
                                                 {'type': 'cell', 'criteria': '>=',
                                                  'value': (100 + highlight_thres) / 100,
                                                  'format': valueOOR_fmt})
                    worksheet.conditional_format(startrow, 1, startrow + nrow - 1, ncol - 1, {'type': 'cell',
                                                                                              'criteria': '<=',
                                                                                              'value': (
                                                                                                                   100 - highlight_thres) / 100,
                                                                                              'format': valueOOR_fmt})
                startrow = startrow + nrow + 2

            headCols = list(meandf.columns) + [' ', ' '] + list(meandf.drop(['TestStepLabel'], axis=1).columns)


            # Add write header column with bold formatting
            for col_num, value in enumerate(headCols):
                worksheet.write(0, col_num, value, header_format)
            worksheet.set_row(0, 140, header_format)
            worksheet.set_column(1, ncol + 1, 8, perc_format)
            worksheet.set_column('A:A', 31)
            worksheet.set_column('B:Z', 8)
            baseline_pos = meandf.columns.get_loc(baseline)
            worksheet.set_column(baseline_pos, baseline_pos, 8, baseline_percformat)



        Sw_info_table.to_excel(excel_writer, sheet_name='Sw_info_table', index=False)
        worksheet = excel_writer.sheets['Sw_info_table']
        worksheet.set_column('A:B', 30)
        worksheet.set_column('C:D', 60)

        Signaltracker.to_excel(excel_writer, sheet_name='TestlogSignalTracker', index=False)
        worksheet = excel_writer.sheets['TestlogSignalTracker']
        for col_num, value in enumerate(Signaltracker.columns):
            worksheet.write(0, col_num, value, header_format)

        nrow, ncol = FaultStat_flc.shape
        label = 'Fault Codes and Cumulative duration(sec) during FLC phase of test '
        FaultStat_flc.to_excel(excel_writer, index_label=label, sheet_name='FaultStats', index=False, header=False,
                               startrow=2, startcol=0)
        worksheet = excel_writer.sheets['FaultStats']
        worksheet.write_string(1, 0, label, cell_format)

        worksheet.conditional_format(2, 1, nrow + 1, ncol - 1,
                                     {'type': 'cell', 'criteria': '>', 'value': 0, 'format': valueOOR_fmt})

        label = 'Fault Codes and Cumulative duration(sec) during Step Response phase of test '
        FaultStat_step.to_excel(excel_writer, index_label=label, sheet_name='FaultStats', index=False, header=False,
                                startrow=nrow + 4,
                                startcol=0)
        worksheet.write_string(nrow + 3, 0, label, cell_format)

        worksheet.write_string(startrow - 1, 0, var, cell_format)

        nrow1, ncol = FaultStat_step.shape
        worksheet.conditional_format(nrow + 4, 1, nrow + 4 + nrow1 - 1, ncol - 1,
                                     {'type': 'cell', 'criteria': '>', 'value': 0, 'format': valueOOR_fmt})
        headCols = list(FaultStat_step.columns)
        # Add a header format.
        for col_num, value in enumerate(headCols):
            worksheet.write(0, col_num, value, header_format)
        worksheet.set_row(0, 140, header_format)
        worksheet.set_column('B:Z', 8)
        worksheet.set_column('A:A', 60)
        worksheet.set_column(baseline_pos, baseline_pos, 8, baseline_format)

    print("done")
