#! python3

import sys

vSourcePath: str
vOutputPath: str = '/srv/OutlineVpnBot/conf/Text.csv.xlsx'
vArgArray = sys.argv
vArgCount = len(vArgArray) - 1
if vArgCount == 1:
    vSourcePath = vArgArray[1]
else:
    vSourcePath = 'conf/Text.csv.xlsx'
    #raise Exception('only one cli argument expected! the path to the file to copy')

import paramiko
from scp import SCPClient

vSshClient: paramiko.SSHClient = paramiko.SSHClient()
vSshClient.load_system_host_keys()
vSshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())

vHostName = 'nikozdev.net' #'46.226.162.47'
vHostPort = 22
vUserName = 'root'
vUserPass = None
vSshClient.connect(vHostName, vHostPort, vUserName, vUserPass)
vTransport: paramiko.Transport | None = vSshClient.get_transport()
if not vTransport:
    raise Exception('failed to get the ssh client transport')

vScpClient = SCPClient(vTransport)
vScpClient.put(vSourcePath, vOutputPath, recursive = False, preserve_times = False)
vSshStdI, vSshStdO, vSshStdE = vSshClient.exec_command(f'chown main:main {vOutputPath}')
print('[stdout]:\n' + vSshStdO.read().decode('utf-8'), file = sys.stdout, end = '')
print('[stderr]:\n' + vSshStdE.read().decode('utf-8'), file = sys.stderr, end = '\n')
vSshStdI.close()
vSshStdI, vSshStdO, vSshStdE = vSshClient.exec_command('systemctl restart OutlineVpnBot.service')
print('[stdout]:\n' + vSshStdO.read().decode('utf-8'), file = sys.stdout, end = '')
print('[stderr]:\n' + vSshStdE.read().decode('utf-8'), file = sys.stderr, end = '\n')
vSshStdI.close()
