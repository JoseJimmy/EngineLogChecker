import pandas as pd
"""
Function for writing results into excel file
writetoExeclSheet(Filename,tables,parameters,Rawdata=False) 
"""

def writetoExeclSheet(Filename,tables,parameters):

    MeanDfs,Sw_info_table,Signaltracker,FaultStat_flc,FaultStat_step,BaselinePData = tables
    highlight_thres,baseline,SignalGroups,p_start,p_end = parameters

    print('Writing to raw summary data Excel to %s...'%Filename.replace('/','\\'), end='')
    with pd.ExcelWriter(Filename) as excel_writer: #creates a file object for the excel file
        workbook = excel_writer.book
        cell_format = workbook.add_format({'bold': True, 'italic': True})
        perc_format = workbook.add_format()



        # Cell format definition
        baseline_percformat = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'color': 'green',
            })


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


        # Light red fill with dark red text.
        red_format = workbook.add_format({'bg_color': '#FFC7CE',
                                          'font_color': '#9C0006'})

        # Green fill with dark green text.
        green_format = workbook.add_format({'bg_color': '#C6EFCE',
                                            'font_color': '#006100'})

        cell_format = workbook.add_format({'bold': True, 'italic': False})
        cell_format.set_font_color('green')
        start_row = 2

        for idx,key in enumerate(BaselinePData.keys()):

            pdata=BaselinePData[key]
            nrow=pdata.shape[0]
            ncol=pdata.shape[1]


            pdata.to_excel(excel_writer, sheet_name='Summary',header=False,index=False,
                                   startrow=start_row, startcol=0)
            worksheet = excel_writer.sheets['Summary']
            txt='%s vs %s : P-Value for 2-sided Hypothesis test on Sample Means [sample taken between %d,%d percentile of each test step] \n'%(key,baseline,100*p_start,100*p_end)
            worksheet.write_string(start_row-1, 1, txt,cell_format)
            worksheet.conditional_format(start_row, 1, start_row + nrow-1 , ncol,
                                         {'type': 'cell', 'criteria': '>=',
                                          'value': highlight_thres,
                                          'format': red_format})
            worksheet.conditional_format(start_row, 1, start_row + nrow-1 , ncol,
                                        {'type': 'cell',
                                                    'criteria': '<',
                                                    'value': highlight_thres,
                                                    'format': green_format})
            start_row=start_row+nrow+2


        worksheet = excel_writer.sheets['Summary']

        headCols = list(pdata.columns)
        # worksheet.write_string(1, 0, label, cell_format)
        # Add write header column with bold formatting
        worksheet.set_row(0, 160, header_format)
        worksheet.set_column('A:A', 30)
        worksheet.freeze_panes(1, 0)

        for col_num, value in enumerate(headCols):
            worksheet.write(0, col_num, value, header_format)


        """"
        Fault Summary 
        """
        nrow, ncol = FaultStat_flc.shape
        label = 'Fault Codes and Cumulative duration(sec) during FLC phase of test '
        startrow=2
        FaultStat_flc.to_excel(excel_writer, index_label=label, sheet_name='ActiveFaultsDuration', index=False, header=False,
                               startrow=startrow, startcol=0)
        worksheet = excel_writer.sheets['ActiveFaultsDuration']
        worksheet.write_string(1, 0, label, cell_format)

        worksheet.conditional_format(2, 1, nrow + 1, ncol - 1,
                                     {'type': 'cell', 'criteria': '>', 'value': 0, 'format': valueOOR_fmt})

        label = 'Fault Codes and Cumulative duration(sec) during Step Response phase of test '
        startrow=nrow + 4

        FaultStat_step.to_excel(excel_writer, index_label=label, sheet_name='ActiveFaultsDuration', index=False, header=False,
                                startrow=startrow,
                                startcol=0)
        worksheet.write_string(nrow + 3, 0, label, cell_format)

        # worksheet.write_string(startrow - 1, 0, var, cell_format)

        nrow1, ncol = FaultStat_step.shape
        worksheet.conditional_format(nrow + 4, 1, nrow + 4 + nrow1 - 1, ncol - 1,
                                     {'type': 'cell', 'criteria': '>', 'value': 0, 'format': valueOOR_fmt})
        headCols = list(FaultStat_step.columns)
        # Add a header format.
        for col_num, value in enumerate(headCols):
            worksheet.write(0, col_num, value, header_format)
        worksheet.set_row(0, 150, header_format)
        worksheet.set_column('B:Z', 8)
        worksheet.set_column('A:A', 60)

        """"
        Mean
        """

        for grpName in SignalGroups.keys():  # Cycle through each signal group, one sheet per group
            nvars = len(SignalGroups[grpName])
            startrow = 2

            for idx, var in enumerate(SignalGroups[grpName]):  # cycle through each variable in the group
                meandf = MeanDfs[var].copy(deep=True)
                nrow, ncol = meandf.shape



                meandf = meandf.fillna('No Data')  # filling out missing values
                sheet_name = 'SignalGroup-'+str(grpName)
                # Write mean values  to excel file
                meandf.to_excel(excel_writer, index_label=var, sheet_name=sheet_name, index=False, header=False,
                                startrow=startrow, startcol=0)
                worksheet = excel_writer.sheets[sheet_name]
                header_text = var+'  [Mean value for each test step]'
                worksheet.write_string(startrow - 1, 0, header_text, cell_format)
                startrow = startrow + nrow + 2
            headCols = list(meandf.columns)

            # Add write header column with bold formatting
            for col_num, value in enumerate(headCols):
                worksheet.write(0, col_num, value, header_format)
            worksheet.set_row(0, 140, header_format)
            worksheet.set_column(1, ncol + 1, 8, perc_format)
            worksheet.set_column('A:A', 31)
            worksheet.set_column('B:Z', 8)
            baseline_pos = meandf.columns.get_loc(baseline)
            worksheet.set_column(baseline_pos, baseline_pos, 8, baseline_percformat)

        """
        """

        Sw_info_table.to_excel(excel_writer, sheet_name='Sw_info_table', index=False)
        worksheet = excel_writer.sheets['Sw_info_table']
        worksheet.set_column('A:B', 30)
        worksheet.set_column('C:D', 60)

        Signaltracker.to_excel(excel_writer, sheet_name='TestlogSignalTracker', index=False)
        worksheet = excel_writer.sheets['TestlogSignalTracker']
        for col_num, value in enumerate(Signaltracker.columns):
            worksheet.write(0, col_num, value, header_format)

        print("done")
