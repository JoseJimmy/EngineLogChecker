# EngineLogChecker.
Python/Pandas based data analysis algorithm for statistical evaluation of engine performance using hypothesis testing.
The script reads MDF files using module module asammdf. The logs files from multiple engine runs from a similar or preprogrammed 
speed/torque profile can be compared. The script identifies and labels engine operating regions, samples data between user specified 
percentile window for each region and then calculate basic statistics. 

It  also does a 2 sided hypothesis test on mean value to check if perfromance are identical.And active fault duration for each region 
is tabulated for comparitive analysis. The signals to be checked can be specified in conf.py before run. All data processing done in 
Pandas and result for comarative anlaysis is written into excel file in table form. 

The picture below illustrates roughly sequence of flow in the script, see code for more details. 
![IMG](https://github.com/JoseJimmy/EngineLogChecker/blob/master/doc/LogChecker.png)

