#! python3

import sys
import logging

import json

import OutlineApi

logging.basicConfig(level = logging.DEBUG, format = '[%(levelname)s][%(asctime)s]{%(message)s}')
logging.info('init')

import os
vApiUrl: str = os.environ.get('vOutlineApiUrl', '')
if not vApiUrl:
    raise Exception('could not find environment variable vOutlineApiUrl!!!')
vCertSha256: str = os.environ.get('vOutlineCertSha256', '')
if not vApiUrl:
    raise Exception('could not find environment variable vOutlineCertSha256!!!')
vConnection = OutlineApi.tConnection(vApiUrl, vCertSha256)

logging.info('work')

vServerInfo = vConnection.fGetServerInfo()
print(vServerInfo)

for vOutlineKey in vConnection.fGetKeyArray():
    vConnection.fDeleteKey(vOutlineKey.vIndex)
