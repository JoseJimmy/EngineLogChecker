# EngineLogChecker.
Python/Pandas based data analysis algorithm for statistical evaluation of engine performance using hypothesis testing
The script reads MDF files using module module asammdf. The logs files from multiple engine runs from a similar/preprogrammed 
speed/torque profile can be compared. The script identifies and labels operating regions, samples data between user specified 
percentile window for each region, calculate basic statistics. 

It  also does a 2 sided hypothesis test on mean value to check if perfromance are identical. The signals to be checked can be 
specified in conf.py before run. All data processing done in Pandas and result for comarative anlaysis is written into
excel file in table form. The picture below illustrated roughly sequence of flow, see code for more details. 


![IMG](https://github.com/JoseJimmy/EngineLogChecker/blob/master/doc/LogChecker.png)

