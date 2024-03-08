#! python3

import logging

import typing
from dataclasses import dataclass

import requests
import requests.adapters
import urllib3
import urllib3.exceptions
from urllib3 import PoolManager
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import dotenv
try:
    dotenv.load_dotenv('conf/.env')
except Exception as vError:
    logging.error('.env file is not found;' + str(vError))

@dataclass
class tOutlineKey:

    vIndex: str
    vTitle: str
    vPassw: str

    vAUrl: str
    vPort: int
    vMeth: str

    vDataSpent: int
    vDataLimit: typing.Optional[int]

    def __init__(self, vResponse: dict, vMetrics: dict | None = None):
        self.vIndex = vResponse['id']
        self.vTitle = vResponse['name']
        self.vPassw = vResponse['password']

        self.vAUrl = vResponse['accessUrl']
        self.vPort = vResponse['port']
        self.vMeth = vResponse['method']

        if vMetrics:
            vMetricsDataTable = vMetrics['bytesTransferredByUserId']
            self.vDataSpent = vMetricsDataTable.get(vResponse['id'], 0)
        else:
            self.vDataSpent = 0
        self.vDataLimit = vResponse.get("dataLimit", {}).get("bytes")
##### tOutlineKey:


class tOutlineServerError(Exception):
    pass
##### tOutlineServerError

class tOutlineLibraryError(Exception):
    pass
##### OutlineLibrary


class tFingerprintAdapter(requests.adapters.HTTPAdapter):
    '''
    this adapter injected into the requests session
    will check that the fingerprint for the certificate matches
    for every request
    '''

    def __init__(self, vFingerprint=None, **vArgs):
        self.vFingerprint = str(vFingerprint)
        super(tFingerprintAdapter, self).__init__(**vArgs)

    def fInitPoolManager(self, vConnectionArray, vSizeMax, vIsBlock=False):
        self.vPoolManager = PoolManager(
            num_pools = vConnectionArray,
            maxsize = vSizeMax,
            block = vIsBlock,
            assert_fingerprint = self.vFingerprint,
        )
##### class tFingerprintAdapter


class tConnection:

    vSession: requests.Session

    def __init__(self, vApiUrl: str, vCertSha256: str):
        self.vApiUrl = vApiUrl

        if vCertSha256:
            self.vSession = requests.Session()
            self.vSession.mount(prefix = "https://", adapter = tFingerprintAdapter(vCertSha256))
        else:
            raise tOutlineLibraryError(
                "No certificate SHA256 provided. Running without certificate is no longer supported"
            )
##### class OutlineVPN

    def fGetKeyArray(self):
        vAccessKeysResponse: requests.Response = self.vSession.get(
            url = f'{self.vApiUrl}/access-keys/',
            verify = False
        )
        vAccessKeysJson: dict = vAccessKeysResponse.json()
        if vAccessKeysResponse.status_code == 200 and 'accessKeys' in vAccessKeysJson:
            vMetricsResponse : requests.Response = self.vSession.get(
                url = f"{self.vApiUrl}/metrics/transfer",
                verify = False
            )
            vMetricsJson: dict = vMetricsResponse.json()
            if (vMetricsResponse.status_code >= 400 or "bytesTransferredByUserId" not in vMetricsJson):
                raise tOutlineServerError('unable to get mertics!')
            vResult = []
            vAccessKeysTable: dict = vAccessKeysJson['accessKeys']
            for vAccessKeyEntry in vAccessKeysTable:
                vResult.append(tOutlineKey(vAccessKeyEntry, vMetricsJson))
            return vResult
        raise tOutlineServerError('unable to retrieve keys')
    ### fGetKeyTable

    def fGetKeyEntry(self, vIndex: str) -> tOutlineKey:
        vKeyResponse: requests.Response = self.vSession.get(
            url = f"{self.vApiUrl}/access-keys/{vIndex}",
            verify = False,
        )
        if vKeyResponse.status_code == 200:
            vKeyJson: dict = vKeyResponse.json()
            vMetricsResponse: requests.Response = self.vSession.get(
                url = f"{self.vApiUrl}/metrics/transfer",
                verify = False,
            )
            vMetricsJson: dict = vMetricsResponse.json()
            if (
                vMetricsResponse.status_code >= 400
                or "bytesTransferredByUserId" not in vMetricsJson
            ):
                raise tOutlineServerError('unable to get metrics !')

            return tOutlineKey(vKeyJson, vMetricsJson)
        else:
            raise tOutlineServerError('unable to get the key entry: ' + vIndex)
    ### fGetKeyEntry

    def fCreateKey(
        self,
        vIndex: str | None = None,
        vTitle: str | None = None,
        vPassw: str | None = None,
        vMeth: str | None = None,
        vPort: int | None = None,
        vDataLimit: int | None = None,
    ) -> tOutlineKey:

        vCreateKeyData: dict = {}

        if vTitle:
            vCreateKeyData["name"] = vTitle
        if vPassw:
            vCreateKeyData["password"] = vPassw

        if vPort:
            vCreateKeyData["port"] = vPort
        if vMeth:
            vCreateKeyData["method"] = vMeth

        if vDataLimit:
            vCreateKeyData["limit"] = { "bytes": vDataLimit }

        vCreateKeyResponse: requests.Response
        if vIndex:
            vCreateKeyData["id"] = vIndex
            vCreateKeyResponse = self.vSession.put(
                url = f"{self.vApiUrl}/access-keys/{vIndex}",
                verify = False,
                json = vCreateKeyData,
            )
        else:
            vCreateKeyResponse = self.vSession.post(
                url = f"{self.vApiUrl}/access-keys",
                verify = False,
                json = vCreateKeyData,
            )

        if vCreateKeyResponse.status_code == 201:
            vCreateKeyJson = vCreateKeyResponse.json()
            return tOutlineKey(vResponse = vCreateKeyJson, vMetrics = None)

        raise tOutlineServerError('unable to create key: ' + vCreateKeyResponse.text)
    ### fCreateKey

    def fDeleteKey(self, vIndex: str) -> bool:
        vDeleteKeyResponse: requests.Response = self.vSession.delete(
            url = f"{self.vApiUrl}/access-keys/{vIndex}",
            verify = False,
        )
        return vDeleteKeyResponse.status_code == 204
    ### fDeleteKey

    def fRenameKey(self, vIndex: str, vKeyName: str):
        vRenameKeyResponse: requests.Response = self.vSession.put(
            url = f"{self.vApiUrl}/access-keys/{vIndex}/name",
            files = { "name": (None, vKeyName) },
            verify = False,
        )
        return vRenameKeyResponse.status_code == 204
    ### fRenameKey

    def fGetDataSpent(self):
        '''Gets how much data all keys have used {
            "bytesTransferredByUserId": {
                "1" : 1008040941,
                "2" : 5958113497,
                "3" : 752221577
            }
        }'''
        vDataSpentReponse: requests.Response = self.vSession.get(
            url = f"{self.vApiUrl}/metrics/transfer",
            verify = False,
        )
        vDataSpentJson: dict = vDataSpentReponse.json()
        if (vDataSpentReponse.status_code >= 400 or "bytesTransferredByUserId" not in vDataSpentJson):
            raise tOutlineServerError('unable to get metrics error')
        return vDataSpentJson
    ### fGetDataSpent

    def fSetDataLimit(self, vIndex: str, vDataLimit: int | None) -> bool:
        '''set data limit for a key (in bytes)'''

        vResponse: requests.Response
        if vDataLimit:
            vResponse = self.vSession.put(
                url = f"{self.vApiUrl}/access-keys/{vIndex}/data-limit",
                json = { "limit": { "bytes": vDataLimit } },
                verify=False,
            )
        else:
            vResponse = self.vSession.delete(
                url = f"{self.vApiUrl}/access-keys/{vIndex}/data-limit",
                verify = False,
            )
        return vResponse.status_code == 204
    ### fSetDataLimit

    def fGetServerInfo(self):
        '''Get information about the server {
            "name": "My Server",
            "serverId": "7fda0079-5317-4e5a-bb41-5a431dddae21",
            "metricsEnabled": true,
            "createdTimestampMs": 1536613192052,
            "version": "1.0.0",
            "accessKeyDataLimit": { "bytes": 8589934592 },
            "portForNewAccessKeys": 1234,
            "hostnameForAccessKeys": "example.com"
        } '''
        vResponse = self.vSession.get(f"{self.vApiUrl}/server", verify = False)
        if vResponse.status_code != 200:
            raise tOutlineServerError("Unable to get information about the server")
        return vResponse.json()
    ### fGetServerInfo

    def fSetServerName(self, vName: str) -> bool:
        '''rename the server'''
        vResponse: requests.Response = self.vSession.put(
            f"{self.vApiUrl}/name", verify = False, json = { "name": vName }
        )
        return vResponse.status_code == 204
    ### fSetServerName

    def fSetHostName(self, vHostName: str) -> bool:
        '''changes the hostname for access keys
        must be a valid hostname or IP address'''
        vResponse: requests.Response = self.vSession.put(
            f"{self.vApiUrl}/server/hostname-for-access-keys", verify = False, json = { "hostname": vHostName }
        )
        return vResponse.status_code == 204
    ### fSetHostName

    def fGetMetricStatus(self) -> bool:
        """Returns whether metrics is being shared"""
        vResponse: requests.Response = self.vSession.get(f"{self.vApiUrl}/metrics/enabled", verify = False)
        return vResponse.json()['metricsEnabled']
    ### fGetMetricStatus

    def fSetMetricStatus(self, vStatus: bool) -> bool:
        """Enables or disables sharing of metrics"""
        vResponse: requests.Response = self.vSession.put(
            url = f'{self.vApiUrl}/metrics/enabled',
            verify = False,
            json = { 'metricsEnabled': vStatus }
        )
        return vResponse.status_code == 204
    ### fSetMetricStatus

    def fSetPortForNewAccessKeys(self, vPort: int) -> bool:
        '''Changes the default port for newly created access keys
        This can be a port already used for access keys'''
        vResponse: requests.Response = self.vSession.put(
            url = f"{self.vApiUrl}/server/port-for-new-access-keys",
            verify = False,
            json = { 'port': vPort }
        )
        if vResponse.status_code == 400:
            raise tOutlineServerError('invalid port value')
        elif vResponse.status_code == 409:
            raise tOutlineServerError('the requested port was already in use by another service')
        return vResponse.status_code == 204
    ### fSetPortForNewAccessKeys

    def fSetDataLimitForAllKeys(self, vDataLimit: int | None) -> bool:
        vResponse: requests.Response
        if vDataLimit:
            vResponse = self.vSession.put(
                url = f"{self.vApiUrl}/server/access-key-data-limit",
                verify = False,
                json = { 'limit': { 'bytes': vDataLimit } }
            )
        else:
            vResponse = self.vSession.delete(
                f"{self.vApiUrl}/server/access-key-data-limit",
                verify=False,
            )
        return vResponse.status_code == 204
##### tConnection
