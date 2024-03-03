#! python3

import sys
import logging

import json

import Api

logging.basicConfig(level = logging.DEBUG, format = '[%(levelname)s][%(asctime)s]{%(message)s}')
logging.info('init')

import os
vApiUrl: str = os.environ['vOutlineApiUrl']
vCertSha256: str = os.environ['vOutlineCertSha256']
vConnection = Api.tConnection(vApiUrl, vCertSha256)

logging.info('work')

vServerInfo = vConnection.fGetServerInfo()
print(vServerInfo)

for vOutlineKey in vConnection.fGetKeyArray():
    vConnection.fDeleteKey(vOutlineKey.vIndex)
