#! python3

import time
import datetime
vTimeFormat: str = '%Y-%m-%d %H:%M:%S'

import regex

import os
import atexit

import uuid

import logging

logging.basicConfig(
    level = logging.DEBUG,
    format = '[%(levelname)s][%(asctime)s]{ %(message)s }',
    filename = 'logs/' + str(int(time.time())) + '.txt'
)
logging.getLogger().addHandler(logging.StreamHandler())
logging.info('logging started!')

import OutlineApi

vOutlineApiUrl: str = os.environ.get('vOutlineApiUrl', '')
if not vOutlineApiUrl:
    raise Exception('could not find environment variable vOutlineApiUrl!!!')
vOutlineCertSha256: str = os.environ.get('vOutlineCertSha256', '')
if not vOutlineCertSha256:
    raise Exception('could not find environment variable vOutlineCertSha256!!!')
vOutlineConnection = OutlineApi.tConnection(vApiUrl = vOutlineApiUrl, vCertSha256 = vOutlineCertSha256)
vOutlineServerInfo: dict = vOutlineConnection.fGetServerInfo()
logging.debug(f'the outline server info:vOutlineServerInfo')

import json

vDbObject = json.load(open('data/DataBase.json', 'r'))

vDbPkeyToDataTable: dict[str, dict] = vDbObject.get('DbPkeyToDataTable', {}) # { TimeSince, DaysLimit, TimeStart }
vDbPkeyToOkeyTable: dict[str, str] = vDbObject.get('DbPkeyToOkeyTable', {})
vDbPkeyToUserTable: dict[str, str] = vDbObject.get('DbPkeyToUserTable', {})
vDbUserToListTable: dict[str, list] = vDbObject.get('DbUserToListTable', {}) # list[PkeyIndex]
def fDbSave():
    vDbObject['DbPkeyToDataTable'] = vDbPkeyToDataTable
    vDbObject['DbPkeyToOkeyTable'] = vDbPkeyToOkeyTable
    vDbObject['DbPkeyToUserTable'] = vDbPkeyToUserTable
    vDbObject['DbUserToListTable'] = vDbUserToListTable
    vDbObject.close()
    vJson = {
        'DbPkeyToDataTable': vDbPkeyToDataTable,
        'DbPkeyToOkeyTable': vDbPkeyToOkeyTable,
        'DbPkeyToUserTable': vDbPkeyToUserTable,
        'DbUserToListTable': vDbUserToListTable,
    }
    json.dump(vJson, open('data/DataBase.json', 'w'))
    print('the database have been saved')
atexit.register(fDbSave)

def fCreatePkey(vDaysLimit: int) -> str:
    vPkeyIndex = str(uuid.uuid4())
    vDbPkeyToDataTable[vPkeyIndex] = {
        'TimeSince': int(time.time()),
        'DaysLimit': vDaysLimit,
        'TimeStart': None,
    }
    return vPkeyIndex
### fCreatePkey
def fDeletePkey(vPkeyIndex: str):
    vDbPkeyToDataTable.pop(vPkeyIndex)
    vOkeyIndex: str | None = vDbPkeyToOkeyTable.get(vPkeyIndex)
    if vOkeyIndex:
        vOutlineConnection.fDeleteKey(vOkeyIndex)
        vDbPkeyToOkeyTable.pop(vPkeyIndex)
    vUserFound: str | None = vDbPkeyToUserTable.get(vPkeyIndex)
    if vUserFound:
        vDbUserToListTable[vUserFound].remove(vPkeyIndex)
        vDbPkeyToUserTable.pop(vPkeyIndex)
### fDeletePkey

def fLaunchPkey(vPkeyIndex: str, vUserIndex: str) -> str:
    vUserFound: str | None = vDbPkeyToUserTable.get(vPkeyIndex)
    if vUserFound:
        raise Exception(f'the pkey "{vPkeyIndex}" is already bound to another user "{vUserFound}"!')
    vDbPkeyToDataTable[vPkeyIndex]['TimeStart'] = int(time.time())
    vDbPkeyToUserTable[vPkeyIndex] = vUserIndex
    vOkeyIndex = str(uuid.uuid4())
    vOkeyEntry: OutlineApi.tOutlineKey = vOutlineConnection.fCreateKey(vIndex = vOkeyIndex, vTitle = vPkeyIndex)
    vDbPkeyToOkeyTable[vPkeyIndex] = vOkeyIndex
    return vOkeyIndex
### fLaunchPkey

def fPayoffPkey(vPkeyIndex: str) -> str:
    vData: dict = vDbPkeyToDataTable[vPkeyIndex]
    vDaysLimit: int = vData['DaysLimit']
    #vUserFound: str | None = vDbPkeyToUserTable.get(vPkeyIndex)
    fDeletePkey(vPkeyIndex)
    vPkeyIndex = fCreatePkey(vDaysLimit)
    return vPkeyIndex
### fPayoffPkey

def fReviewPkeyTable():
    vTimeNow: int = int(time.time())
    vDeleteArray: list[str] = []
    for vPkey, vData in vDbPkeyToDataTable.items():
        try:
            vTimeStart: int | None = vData.get('DaysLimit')
            if not vTimeStart:
                continue
            vDaysLimit: int = vData['DaysLimit']
            vTimeFinal: int = vTimeStart + (vDaysLimit * 60 * 60 * 24)
            if vTimeNow > vTimeFinal:
                vDeleteArray.append(vPkey)
        except Exception as vError:
            logging.error(f'failed to review the pkey "{vPkey}": ' + str(vError))
    for vPkey in vDeleteArray:
        try:
            fDeletePkey(vPkey)
        except Exception as vError:
            logging.error(f'failed to delete the pkey "{vPkey}": ' + str(vError))
### fReviewPkeyTable
fReviewPkeyTable()

import telebot
import telebot.types

vBotKey: str = os.environ.get('vTelegramBotKey', '')
if not vBotKey:
    raise Exception('could not find environment variable vTelegramBotKey!!!')

vBotReplyTable: dict[str, str] = json.load(open('conf/ReplyTable.json', 'r', encoding = 'utf-8'))

vBot: telebot.TeleBot = telebot.TeleBot(vBotKey, parse_mode = None)
vMarkupMain: telebot.types.ReplyKeyboardMarkup = telebot.types.ReplyKeyboardMarkup(resize_keyboard = True)
vMarkupMain.add(telebot.types.KeyboardButton("/myvpn"))
vMarkupMain.add(telebot.types.KeyboardButton("/activate"))
vMarkupCancel: telebot.types.ReplyKeyboardMarkup = telebot.types.ReplyKeyboardMarkup(resize_keyboard = True)
vMarkupCancel.add(telebot.types.KeyboardButton("/отмена"))

def fVetAdmin(vUser) -> bool:
    with open('conf/AdminTable.json', 'r') as vDbAdminTableFile:
        vDbAdminTableJson: dict[str, int] = json.load(vDbAdminTableFile)
        return vDbAdminTableJson.get(str(vUser.id), 0) > 0
### fVetAdmin

@vBot.message_handler(commands = ['start'])
def fHandle_Cmd_Start(vMessage):
    vBot.reply_to(vMessage, vBotReplyTable['Start'], reply_markup = vMarkupMain)
### fHandle_Cmd_Start

@vBot.message_handler(commands = ['myvpn'])
def fHandle_Cmd_MyVpn(vMessage):
    vResponse = 'MyVpn:\n'
    vUserObject = vMessage.from_user
    vUserIdStr: str = str(vUserObject.id)
    vList: list = vDbUserToListTable.get(vUserIdStr, [])
    vResponse = vBotReplyTable['MyVpn_Title']
    vResponse += vBotReplyTable['MyVpn_Keys']
    for vPkeyOrder, vPkeyIndex in enumerate(vList):
        vKeyDesc: str = vBotReplyTable['MyVpn_Keys_Iter']
        vKeyDesc = vKeyDesc.replace('{Order}', str(vPkeyOrder + 1))
        vKeyDesc = vKeyDesc.replace('{PKey}', vPkeyIndex)
        vOkeyIndex = vDbPkeyToOkeyTable[vPkeyIndex]
        vOkeyEntry = vOutlineConnection.fGetKeyEntry(vOkeyIndex)
        vKeyDesc = vKeyDesc.replace('{AUrl}', vOkeyEntry.vAUrl)
        # time
        vData: dict = vDbPkeyToDataTable[vPkeyIndex]
        vDaysLimit = vData['DaysLimit']
        vKeyDesc = vKeyDesc.replace('{DaysLimit}', str(vDaysLimit))
        vTimeStart: int = vData['TimeStart'] 
        vKeyDesc = vKeyDesc.replace('{TimeStart}', datetime.datetime.utcfromtimestamp(vTimeStart).strftime(vTimeFormat))
        vTimeUntil: int = vTimeStart + (vDaysLimit * 60 * 60 * 24)
        vKeyDesc = vKeyDesc.replace('{TimeUntil}', datetime.datetime.utcfromtimestamp(vTimeUntil).strftime(vTimeFormat))
        vKeyDesc = vKeyDesc.replace('{TimeDelta}', datetime.datetime.utcfromtimestamp(vTimeUntil - vTimeStart).strftime(vTimeFormat))
        vResponse += vKeyDesc
    vBot.reply_to(vMessage, vResponse, reply_markup = vMarkupMain)
### fHandle_Cmd_MyVpn

def fHandle_Cmd_Activ_Input(vMessage):
    vUserObject = vMessage.from_user
    vUserIdStr: str = str(vUserObject.id)
    try:
        vPkeyIndex: str = vMessage.text
        vOkeyIndex: str = fLaunchPkey(vPkeyIndex, vUserIdStr)
        vOkeyEntry: OutlineApi.tOutlineKey = vOutlineConnection.fGetKeyEntry(vOkeyIndex)

        vList = vDbUserToListTable.get(vUserIdStr, [])
        vList.append(vPkeyIndex)
        vDbUserToListTable[vUserIdStr] = vList

        vResponse: str = vBotReplyTable['Activate_Success']
        vResponse = vResponse.replace('{PKey}', vPkeyIndex)
        vResponse = vResponse.replace('{AUrl}', vOkeyEntry.vAUrl)
        vBot.reply_to(vMessage, vResponse, reply_markup = vMarkupMain)
    except Exception as vError:
        logging.error('failed to activate pkey:' + str(vError))
        vResponse: str = vBotReplyTable['Activate_Failure']
        vBot.reply_to(vMessage, vResponse, reply_markup = vMarkupMain)
### fHandle_Cmd_Activ_Input
@vBot.message_handler(commands = ['activate'])
def fHandle_Cmd_Activ(vMessage):
    vBot.reply_to(vMessage, vBotReplyTable['Activate_Input'], reply_markup = vMarkupCancel)
    vBot.register_next_step_handler(vMessage, fHandle_Cmd_Activ_Input)
### fHandle_Cmd_Activ

## команды королей

def fHandle_Cmd_Create_Input(vMessage):
    try:
        vDaysLimit: int = int(vMessage.text)
        vPkeyIndex: str = fCreatePkey(vDaysLimit)
        vResponse: str = vBotReplyTable['Admin_Create_Success']
        vResponse = (vResponse.replace('{PKey}', vPkeyIndex))
        vBot.reply_to(vMessage, vResponse, reply_markup = vMarkupMain)
    except Exception as vError:
        logging.error('failed key creation: ' + str(vError))
        vBot.reply_to(vMessage, vBotReplyTable['Admin_Create_Failure'], reply_markup = vMarkupMain)
### fHandle_Cmd_Create_Input
@vBot.message_handler(commands=['admin_create'])
def fHandle_Cmd_Create(vMessage):
    if not fVetAdmin(vMessage.from_user):
        vBot.reply_to(vMessage, vBotReplyTable['Admin_Failure'])
        return
    vBot.reply_to(vMessage, vBotReplyTable['Admin_Create_Input'], reply_markup = vMarkupCancel)
    vBot.register_next_step_handler(vMessage, fHandle_Cmd_Create_Input)
### fHandle_Cmd_Create

def fHandle_Cmd_Delete_Input(vMessage):
    try:
        vPkeyIndex: str = vMessage.text
        fDeletePkey(vPkeyIndex)
        vBot.reply_to(vMessage, vBotReplyTable['Admin_Delete_Success'].replace('{PKey}', vPkeyIndex), reply_markup = vMarkupMain)
    except Exception as vError:
        logging.error('failed key deletion: ' + str(vError))
        vBot.reply_to(vMessage, vBotReplyTable['Admin_Delete_Failure'], reply_markup = vMarkupMain)
### fHandle_Cmd_Delete_Input
@vBot.message_handler(commands=['admin_delete'])
def fHandle_Cmd_Delete(vMessage):
    if not fVetAdmin(vMessage.from_user):
        vBot.reply_to(vMessage, vBotReplyTable['Admin_Failure'])
        return
    vBot.reply_to(vMessage, vBotReplyTable['Admin_Delete_Input'], reply_markup = vMarkupCancel)
    vBot.register_next_step_handler(vMessage, fHandle_Cmd_Delete_Input)
### fHandle_Cmd_Delete

def fHandle_Cmd_Payoff_Input(vMessage):
    try:
        vPkeyIndex: str = vMessage.text
        vPkeyIndex = fPayoffPkey(vPkeyIndex)
        vBot.reply_to(vMessage, vBotReplyTable['Admin_Payoff_Success'].replace('{PKey}', vPkeyIndex), reply_markup = vMarkupMain)
    except Exception as vError:
        logging.error('failed payoff: ' + str(vError))
        vBot.reply_to(vMessage, vBotReplyTable['Admin_Payoff_Failure'], reply_markup = vMarkupMain)
@vBot.message_handler(commands=['admin_payoff'])
def fHandle_Cmd_Payoff(vMessage):
    if not fVetAdmin(vMessage.from_user):
        vBot.reply_to(vMessage, vBotReplyTable['Admin_Failure'], reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, vBotReplyTable['Admin_Payoff_Input'], reply_markup = vMarkupCancel)
    vBot.register_next_step_handler(vMessage, fHandle_Cmd_Payoff_Input)
### fHandle_Cmd_Payoff

@vBot.message_handler(commands=['admin_keytab'])
def fHandle_Cmd_KeyTab(vMessage):
    if not fVetAdmin(vMessage.from_user):
        vBot.reply_to(vMessage, vBotReplyTable['Admin_Failure'])
        return
    vOkeyArray: list[OutlineApi.tOutlineKey] = vOutlineConnection.fGetKeyArray()
    vResponse: str = 'key tables'
    vResponse += '\nPkeyToDataTable:'
    for vPkey, vData in vDbPkeyToDataTable.items():
        vResponse += '\nPkey = ' + vPkey
        vResponse += '; TimeSince = ' + str(vData.get('TimeSince'))
        vResponse += '; DaysLimit = ' + str(vData.get('DaysLimit'))
        vResponse += '; TimeStart = ' + str(vData.get('TimeStart'))
    vResponse += '\nPkeyToOkeyTable:'
    for vPkeyIndex, vOkeyIndex in vDbPkeyToOkeyTable.items():
        vResponse += '\nPkey = ' + vPkeyIndex
        vResponse += '; Okey = ' + vOkeyIndex
    vResponse += '\nPkeyToUserTable:'
    for vPkeyIndex, vUserIndex in vDbPkeyToUserTable.items():
        vResponse += '\nPkey = ' + vPkeyIndex
        vResponse += '; User = ' + vUserIndex
    vResponse += '\nOkeyArray:'
    for vOkeyEntry in vOkeyArray:
        vResponse += '\nIndex = ' + str(vOkeyEntry.vIndex)
        vResponse += '; Title = ' + vOkeyEntry.vTitle
        vResponse += '; Passw = ' + vOkeyEntry.vPassw
        vResponse += '; AUrl = ' + vOkeyEntry.vAUrl
        vResponse += '; Port = ' + str(vOkeyEntry.vPort)
        vResponse += '; Meth = ' + vOkeyEntry.vMeth
        vResponse += '; DataSpent = ' + str(vOkeyEntry.vDataSpent)
        vResponse += '; DataLimit = ' + str(vOkeyEntry.vDataLimit)
    vBot.reply_to(vMessage, vResponse, reply_markup = vMarkupMain)
### fHandle_Cmd_KeyTab

@vBot.message_handler(commands = ['cancel'])
def fHandle_Cmd_Cancel(vMessage):
    vBot.reply_to(vMessage, vBotReplyTable['Cancel'], reply_markup = vMarkupCancel)
### fHandle_Cmd_Cancel

@vBot.message_handler(commands = ['help'])
def fHandle_Cmd_Help(vMessage):
    vBot.reply_to(vMessage, vBotReplyTable['Help'], reply_markup = vMarkupMain)
### fHandle_Cmd_Start

try:
    vBot.infinity_polling()
except KeyboardInterrupt as vError:
    logging.warning('interrupted by keyboard ! ' + str(vError))
except Exception as vError:
    logging.warning('An unexpected error happened ! ' + str(vError))
