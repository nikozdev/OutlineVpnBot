#! python3

import sys

import logging
logging.basicConfig(level = logging.DEBUG, format = '[%(levelname)s][%(asctime)s]{ %(message)s }')

vArgArray: list[str] = sys.argv
vArgCount: int = len(vArgArray) - 1
logging.debug('the argument array is:\n' + str(vArgArray))
if vArgCount != 1:
    raise Exception('1 command line argument required: input path; we have ' + str(vArgCount))

vSourcePath: str = vArgArray[1]
if False:
    vSourceFile = open(vSourcePath, 'r')
    import csv
    vSourceCsv = csv.reader(vSourceFile)
    for vIndex, vSourceRow in enumerate(vSourceCsv):
        print(vIndex, vSourceRow)
    vSourceFile.close()
else:
    import openpyxl
    vSourceWb = openpyxl.load_workbook(vSourcePath)
    vSourceWs = vSourceWb.active
    if not vSourceWs:
        raise Exception('could not find a sheet')
    for vRow in vSourceWs.iter_rows(min_row = 1, min_col=1):
        print(vRow[0].value, vRow[1].value.replace('\n', '<\\n>'))
