#! python3

import time
import datetime
vTimeFormat: str = '%Y-%m-%d %H:%M:%S'

import os
import threading

import uuid

import logging

logging.basicConfig(
    level = logging.INFO,
    format = '[%(levelname)s][%(asctime)s]{ %(message)s }',
#    filename = 'logs/' + str(int(time.time())) + '.txt'
    filename = 'logs/main.txt'
)
logging.getLogger().addHandler(logging.StreamHandler())
logging.info('logging started!')

import Api

vOutlineApiUrl: str = os.environ['vOutlineApiUrl']
vOutlineCertSha256: str = os.environ['vOutlineCertSha256']
vOutlineConnection = Api.tConnection(vApiUrl = vOutlineApiUrl, vCertSha256 = vOutlineCertSha256)
vOutlineServerInfo: dict = vOutlineConnection.fGetServerInfo()
logging.debug(f'the outline server info:vOutlineServerInfo')

import json

vDbPkeyToDataTable: dict[str, dict]
vDbPkeyToOkeyTable: dict[str, str] 
vDbPkeyToUserTable: dict[str, str] 
vDbUserToListTable: dict[str, list]
def fDbLoadOne(vDbName: str):
    logging.info('the database load: ' + vDbName)
    return json.load(open(f'data/{vDbName}.json', 'r', encoding = 'utf-8'))
### fDbLoadOne
def fDbLoadAll():
    global vDbPkeyToDataTable
    vDbPkeyToDataTable = fDbLoadOne('PkeyToDataTable')
    global vDbPkeyToOkeyTable
    vDbPkeyToOkeyTable = fDbLoadOne('PkeyToOkeyTable')
    global vDbPkeyToUserTable
    vDbPkeyToUserTable = fDbLoadOne('PkeyToUserTable')
    global vDbUserToListTable
    vDbUserToListTable = fDbLoadOne('UserToListTable')
fDbLoadAll()
### fDbLoadAll
def fDbSaveOne(vDbName: str, vDbTable: dict):
    json.dump(vDbTable, open(f'data/{vDbName}.json', 'w', encoding = 'utf-8'), separators = (',', ':'))
    #logging.info('the database save: ' + vDbName)
### fDbSaveOne
def fDbSaveAll():
    fDbSaveOne('PkeyToDataTable', vDbPkeyToDataTable)
    fDbSaveOne('PkeyToOkeyTable', vDbPkeyToOkeyTable)
    fDbSaveOne('PkeyToUserTable', vDbPkeyToUserTable)
    fDbSaveOne('UserToListTable', vDbUserToListTable)
    #logging.info('the database has been saved!')
### fDbSaveAll
fDbSaveAll()

def fCreatePkey(vTimeLimit: int) -> str:
    vPkeyIndex = str(uuid.uuid4())
    vDbPkeyToDataTable[vPkeyIndex] = {
        'TimeSince': int(time.time()),
        'TimeLimit': vTimeLimit,
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
        raise Exception(f'the pkey "{vPkeyIndex}" is bound to another user "{vUserFound}"!')
    vDbPkeyToDataTable[vPkeyIndex]['TimeStart'] = int(time.time())
    vDbPkeyToUserTable[vPkeyIndex] = vUserIndex
    vOkeyIndex = str(uuid.uuid4())
    vOkeyEntry: Api.tOutlineKey = vOutlineConnection.fCreateKey(vIndex = vOkeyIndex, vTitle = vPkeyIndex)
    vDbPkeyToOkeyTable[vPkeyIndex] = vOkeyIndex
    vList = vDbUserToListTable.get(vUserIndex, [])
    vList.append(vPkeyIndex)
    vDbUserToListTable[vUserIndex] = vList
    return vOkeyIndex
### fLaunchPkey

def fPayoffPkey(vPkeyIndex: str) -> str:
    vData: dict = vDbPkeyToDataTable[vPkeyIndex]
    vTimeLimit: int = vData['TimeLimit']
    fDeletePkey(vPkeyIndex)
    vPkeyIndex = fCreatePkey(vTimeLimit)
    return vPkeyIndex
### fPayoffPkey

def fRemakePkey(vPkeyIndex: str) -> tuple[str, str]:

    vData: dict = vDbPkeyToDataTable[vPkeyIndex]
    vTimeLimit: int = vData['TimeLimit']
    vTimeStart: int = vData['TimeStart']
    vUserFound: str  = vDbPkeyToUserTable[vPkeyIndex]

    fDeletePkey(vPkeyIndex)
    vPkeyIndex = fCreatePkey(vTimeLimit)
    vOkeyIndex = fLaunchPkey(vPkeyIndex, vUserFound)
    # after the launch function!
    vDbPkeyToDataTable[vPkeyIndex]['TimeStart'] = vTimeStart

    return vPkeyIndex, vOkeyIndex
### fRemakePkey

def fReviewPkeyTable():
    vTimeNow: int = int(time.time())
    vDeleteArray: list[str] = []
    for vPkey, vData in vDbPkeyToDataTable.items():
        try:
            vTimeStart: int | None = vData.get('TimeStart')
            if not vTimeStart:
                continue
            vTimeLimit: int = vData['TimeLimit']
            vTimeUntil: int = vTimeStart + vTimeLimit
            if vTimeNow > vTimeUntil:
                vDeleteArray.append(vPkey)
                print('DELETE KEY!!!', vTimeNow, vTimeUntil, vPkey)
        except Exception as vError:
            logging.error(f'failed to review the pkey "{vPkey}": ' + str(vError))
    for vPkey in vDeleteArray:
        try:
            fDeletePkey(vPkey)
        except Exception as vError:
            logging.error(f'failed to delete the pkey "{vPkey}": ' + str(vError))
    #logging.info('the keytable has been reviewed!')
### fReviewPkeyTable
fReviewPkeyTable()

import telebot
import telebot.types

vBotTextTable: dict[str, str] = json.load(open('conf/Text.json', 'r', encoding = 'utf-8'))

vBotKey: str = os.environ['vTelegramBotKey']
vBot: telebot.TeleBot = telebot.TeleBot(vBotKey, parse_mode = None)
vBot.set_my_commands(commands = [
    telebot.types.BotCommand('start', vBotTextTable['Start_Markup']),
    telebot.types.BotCommand('activate', vBotTextTable['Activate_Markup']),
    telebot.types.BotCommand('profile', vBotTextTable['Profile_Markup']),
    telebot.types.BotCommand('mykeys', vBotTextTable['MyKeys_Markup']),
    telebot.types.BotCommand('trouble', vBotTextTable['Trouble_Markup']),
    telebot.types.BotCommand('help', vBotTextTable['Help_Markup']),
    telebot.types.BotCommand('info', vBotTextTable['Info_Markup']),
    telebot.types.BotCommand('support', vBotTextTable['Support_Markup']),
], scope = telebot.types.BotCommandScopeDefault())

vMarkupMain: telebot.types.ReplyKeyboardMarkup = telebot.types.ReplyKeyboardMarkup(resize_keyboard = True)
vMarkupMain.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Activate_Markup'],
    callback_data = 'activate',
), telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Trouble_Markup'],
    callback_data = 'trouble',
), row_width = 2)
vMarkupMain.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Profile_Markup'],
    callback_data = 'profile',
), telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Help_Markup'],
    callback_data = 'help',
), row_width = 2)

vMarkupAdmin: telebot.types.InlineKeyboardMarkup = telebot.types.InlineKeyboardMarkup()
vMarkupAdmin.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Admin_Create_Markup'],
    callback_data = 'admin_create',
), telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Admin_Delete_Markup'],
    callback_data = 'admin_delete',
), row_width = 2)
vMarkupAdmin.add()
vMarkupAdmin.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Admin_Payoff_Markup'],
    callback_data = 'admin_payoff',
))
vMarkupAdmin.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Return_Markup'],
    callback_data = 'return',
))

vMarkupProfile: telebot.types.InlineKeyboardMarkup = telebot.types.InlineKeyboardMarkup()
vMarkupProfile.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['MyKeys_Markup'],
    callback_data = 'mykeys',
))
vMarkupProfile.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Trouble_Markup'],
    callback_data = 'trouble',
))
vMarkupProfile.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Help_Markup'],
    callback_data = 'help',
))
vMarkupProfile.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Return_Markup'],
    callback_data = 'return',
))

vMarkupHelp: telebot.types.InlineKeyboardMarkup = telebot.types.InlineKeyboardMarkup()
vMarkupHelp.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Support_Markup'],
    callback_data = 'support',
))
vMarkupHelp.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Info_Markup'],
    callback_data = 'info',
))
vMarkupHelp.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Return_Markup'],
    callback_data = 'return',
))

vMarkupCancel: telebot.types.InlineKeyboardMarkup = telebot.types.InlineKeyboardMarkup()
vMarkupCancel.add(telebot.types.InlineKeyboardButton(
    text = vBotTextTable['Cancel_Markup'],
    callback_data = 'cancel',
))

vSpamDelay: int = 5
vSpamTableForStart: dict[int, int] = { }
vSpamTableForActivate: dict[int, int] = { }
vSpamTableForProfile: dict[int, int] = { }
vSpamTableForMyKeys: dict[int, int] = { }
vSpamTableForTrouble: dict[int, int] = { }
vSpamTableForHelp: dict[int, int] = { }
vSpamTableForInfo: dict[int, int] = { }
vSpamTableForSupport: dict[int, int] = { }
def fVetSpam(vSpamTable: dict[int, int], vUserIndex: int, vTimeDelay: int = vSpamDelay):
    vTimeStamp: int = int(time.time())
    if (vTimeStamp - vSpamTable.get(vUserIndex, 0)) > vTimeDelay:
        vSpamTable[vUserIndex] = vTimeStamp
        return False
    else:
        return True
### fVetSpam

def fVetAdmin(vUser: telebot.types.User) -> bool:
    with open('conf/AdminTable.json', 'r') as vDbAdminTableFile:
        vDbAdminTableJson: dict[str, int] = json.load(vDbAdminTableFile)
        return vDbAdminTableJson.get(str(vUser.id), 0) > 0
### fVetAdmin

def fMakeMyKeysResponse(vUserObject: telebot.types.User):
    vUserIdStr: str = str(vUserObject.id)
    vList: list = vDbUserToListTable.get(vUserIdStr, [])
    vResponse = vBotTextTable['MyKeys']
    for vPkeyOrder, vPkeyIndex in enumerate(vList):
        vKeyDesc: str = vBotTextTable['Profile_Keys_Iter']
        vKeyDesc = vKeyDesc.replace('{Order}', str(vPkeyOrder + 1))
        vKeyDesc = vKeyDesc.replace('{PKey}', vPkeyIndex)
        vOkeyIndex = vDbPkeyToOkeyTable[vPkeyIndex]
        vOkeyEntry = vOutlineConnection.fGetKeyEntry(vOkeyIndex)
        vKeyDesc = vKeyDesc.replace('{AUrl}', vOkeyEntry.vAUrl)
        # time
        vData: dict = vDbPkeyToDataTable[vPkeyIndex]
        vTimeLimit = vData['TimeLimit']
        vKeyDesc = vKeyDesc.replace('{TimeLimit.days}', str(datetime.timedelta(seconds = vTimeLimit).days))
        vTimeStart: int = vData['TimeStart'] 
        vKeyDesc = vKeyDesc.replace('{TimeStart}', datetime.datetime.utcfromtimestamp(vTimeStart).strftime(vTimeFormat))
        vTimeUntil: int = vTimeStart + vTimeLimit
        vKeyDesc = vKeyDesc.replace('{TimeUntil}', datetime.datetime.utcfromtimestamp(vTimeUntil).strftime(vTimeFormat))
        vTimeDelta: datetime.timedelta = datetime.timedelta(seconds = vTimeUntil - vTimeStart)
        vKeyDesc = vKeyDesc.replace('{TimeDelta.days}', str(vTimeDelta.days))
        vResponse += vKeyDesc
    return vResponse
### fMakeProfileResponse

def fHandle_Msg_Start_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if fVetSpam(vSpamTableForStart, vUserObject.id):
        vBot.reply_to(vMessage, vBotTextTable['Spam_Warning'].replace('{Delay}', str(vSpamDelay)), reply_markup = vMarkupMain)
        return
    vBot.set_chat_menu_button(vMessage.chat.id, telebot.types.MenuButtonCommands('commands'))
    vBot.send_message(vMessage.chat.id, vBotTextTable['Start'], reply_markup = vMarkupMain)
### fHandle_Msg_Start_Main
@vBot.message_handler(commands = ['start'])
def fHandle_Msg_Start_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Start_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Start_Proxy

def fHandle_Msg_Profile_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if fVetSpam(vSpamTableForProfile, vUserObject.id):
        vBot.reply_to(vMessage, vBotTextTable['Spam_Warning'].replace('{Delay}', str(vSpamDelay)), reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, vBotTextTable['Profile'], reply_markup = vMarkupProfile)
### fHandle_Msg_Profile_Main
@vBot.message_handler(commands = ['profile'])
def fHandle_Msg_Profile_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Profile_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Profile_Proxy

def fHandle_Msg_MyKeys_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if fVetSpam(vSpamTableForMyKeys, vUserObject.id):
        vBot.reply_to(vMessage, vBotTextTable['Spam_Warning'].replace('{Delay}', str(vSpamDelay)), reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, fMakeMyKeysResponse(vUserObject), reply_markup = vMarkupProfile)
### fHandle_Msg_MyKeys_Main
@vBot.message_handler(commands = ['profile'])
def fHandle_Msg_MyKeys_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_MyKeys_Main(vMessage, vMessage.from_user)
### fHandle_Msg_MyKeys_Proxy

def fHandle_Msg_Trouble_Input(vMessage: telebot.types.Message):
    try:
        vPkeyIndex: str = vMessage.text or ''
        vUser: str = vDbPkeyToUserTable[vPkeyIndex]
        if vUser != str(vMessage.from_user.id):
            raise Exception('User entered Pkey which does not belong to them')
        vPkeyIndex, vOkeyIndex = fRemakePkey(vPkeyIndex)
        vOkeyEntry = vOutlineConnection.fGetKeyEntry(vOkeyIndex)
        vResponse = vBotTextTable['Trouble_Success'].replace('{PKey}', vPkeyIndex).replace('AUrl', vOkeyEntry.vAUrl)
        vBot.reply_to(vMessage, vResponse)
        fHandle_Msg_Profile_Main(vMessage, vMessage.from_user)
    except:
        logging.error('failed to activate pkey:' + str(vError))
        vResponse: str = vBotTextTable['Activate_Failure']
        vBot.reply_to(vMessage, vBotTextTable['Trouble_Failure'], reply_markup = vMarkupProfile)
### fHandle_Msg_Trouble_Input
def fHandle_Msg_Trouble_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if fVetSpam(vSpamTableForTrouble, vUserObject.id, 60):
        vBot.reply_to(vMessage, vBotTextTable['Spam_Warning'].replace('{Delay}', '60'), reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, vBotTextTable['Trouble_Input'], reply_markup = vMarkupCancel)
    vBot.register_next_step_handler(vMessage, fHandle_Msg_Trouble_Input)
### fHandle_Msg_Trouble_Main
@vBot.message_handler(commands = ['trouble'])
def fHandle_Msg_Trouble_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Trouble_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Trouble_Proxy

def fHandle_Msg_Activate_Input(vMessage: telebot.types.Message):
    vUserObject: telebot.types.User = vMessage.from_user
    vUserIdStr: str = str(vUserObject.id)
    try:
        vPkeyIndex: str = vMessage.text or ''
        vOkeyIndex: str = fLaunchPkey(vPkeyIndex, vUserIdStr)
        vOkeyEntry: Api.tOutlineKey = vOutlineConnection.fGetKeyEntry(vOkeyIndex)

        vResponse: str = vBotTextTable['Activate_Success']
        vResponse = vResponse.replace('{PKey}', vPkeyIndex)
        vResponse = vResponse.replace('{AUrl}', vOkeyEntry.vAUrl)

        vBot.reply_to(vMessage, vResponse, reply_markup = vMarkupMain)
    except Exception as vError:
        logging.error('failed to activate pkey:' + str(vError))
        vResponse: str = vBotTextTable['Activate_Failure']
        vBot.reply_to(vMessage, vResponse, reply_markup = vMarkupMain)
### fHandle_Msg_Activate_Input
def fHandle_Msg_Activate_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if fVetSpam(vSpamTableForActivate, vUserObject.id, 10):
        vBot.reply_to(vMessage, vBotTextTable['Spam_Warning'].replace('{Delay}', '10'), reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, vBotTextTable['Activate_Input'], reply_markup = vMarkupCancel)
    vBot.register_next_step_handler(vMessage, fHandle_Msg_Activate_Input)
### fHandle_Msg_Activate_Main
@vBot.message_handler(commands = ['activate'])
def fHandle_Msg_Activate_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Activate_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Activate_Proxy

def fHandle_Msg_Help_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if fVetSpam(vSpamTableForHelp, vUserObject.id):
        vBot.reply_to(vMessage, vBotTextTable['Spam_Warning'].replace('{Delay}', str(vSpamDelay)), reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, vBotTextTable['Help'], reply_markup = vMarkupHelp)
### fHandle_Msg_Help_Main
@vBot.message_handler(commands = ['help'])
def fHandle_Msg_Help_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Help_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Help_Proxy

def fHandle_Msg_Support_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if fVetSpam(vSpamTableForSupport, vUserObject.id):
        vBot.reply_to(vMessage, vBotTextTable['Spam_Warning'].replace('{Delay}', str(vSpamDelay)), reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, vBotTextTable['Support'], reply_markup = vMarkupHelp)
### fHandle_Msg_Support_Main
@vBot.message_handler(commands = ['support'])
def fHandle_Msg_Support_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Support_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Support_Proxy

def fHandle_Msg_Info_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if fVetSpam(vSpamTableForInfo, vUserObject.id):
        vBot.reply_to(vMessage, vBotTextTable['Spam_Warning'].replace('{Delay}', str(vSpamDelay)), reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, vBotTextTable['Info'], reply_markup = vMarkupHelp)
### fHandle_Msg_Info_Main
@vBot.message_handler(commands = ['info'])
def fHandle_Msg_Info_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Info_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Info_Proxy

def fHandle_Msg_Admin_Create_Input(vMessage: telebot.types.Message):
    try:
        vArgArray: list[str] = (vMessage.text or '').split(' ', maxsplit = 7)
        vArgCount: int = len(vArgArray)

        vPkeyCount: int
        vPkeyCount = int(vArgArray[0])

        vTimeLimit: int = int(datetime.timedelta(
            days = (int(vArgArray[1]) if (vArgCount > 1) else 0),
            hours = (int(vArgArray[2]) if (vArgCount > 2) else 0),
            minutes = (int(vArgArray[3]) if (vArgCount > 3) else 0),
            seconds = (int(vArgArray[4]) if (vArgCount > 4) else 0),
        ).total_seconds())

        vResponse: str = vBotTextTable['Admin_Create_Success'].replace('{Count}', str(vPkeyCount))
        for vIter in range(vPkeyCount):
            vPkeyIndex: str = fCreatePkey(vTimeLimit)
            vResponseIter = vBotTextTable['Admin_Create_Success_Iter']
            vResponseIter = vResponseIter.replace('{Iter}', str(vIter + 1))
            vResponseIter = vResponseIter.replace('{PKey}', vPkeyIndex)
            vResponse += vResponseIter
        vBot.reply_to(vMessage, vResponse, reply_markup = vMarkupAdmin)
    except Exception as vError:
        logging.error('failed key creation: ' + str(vError))
        vBot.reply_to(vMessage, vBotTextTable['Admin_Create_Failure'], reply_markup = vMarkupAdmin)
### fHandle_Msg_Admin_Create_Input
def fHandle_Msg_Admin_Create_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if not fVetAdmin(vUserObject):
        vBot.reply_to(vMessage, vBotTextTable['Admin_Failure'])
        vBot.send_message(vMessage.chat.id, vBotTextTable['Start'], reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, vBotTextTable['Admin_Create_Input'], reply_markup = vMarkupCancel)
    vBot.register_next_step_handler(vMessage, fHandle_Msg_Admin_Create_Input)
### fHandle_Msg_Admin_Create_Main
@vBot.message_handler(commands=['admin_create'])
def fHandle_Msg_Admin_Create_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Admin_Create_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Admin_Create_Proxy

def fHandle_Msg_Admin_Delete_Input(vMessage: telebot.types.Message):
    try:
        vPkeyIndex: str = vMessage.text or ''
        fDeletePkey(vPkeyIndex)
        vBot.reply_to(vMessage, vBotTextTable['Admin_Delete_Success'].replace('{PKey}', vPkeyIndex), reply_markup = vMarkupAdmin)
    except Exception as vError:
        logging.error('failed key deletion: ' + str(vError))
        vBot.reply_to(vMessage, vBotTextTable['Admin_Delete_Failure'], reply_markup = vMarkupAdmin)
### fHandle_Msg_Admin_Delete_Input
def fHandle_Msg_Admin_Delete_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if not fVetAdmin(vUserObject):
        vBot.reply_to(vMessage, vBotTextTable['Admin_Failure'])
        vBot.send_message(vMessage.chat.id, vBotTextTable['Start'], reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, vBotTextTable['Admin_Delete_Input'], reply_markup = vMarkupCancel)
    vBot.register_next_step_handler(vMessage, fHandle_Msg_Admin_Delete_Input)
### fHandle_Msg_Admin_Delete_Main
@vBot.message_handler(commands=['admin_delete'])
def fHandle_Msg_Admin_Delete_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Admin_Delete_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Admin_Delete_Proxy

def fHandle_Msg_Admin_Payoff_Input(vMessage: telebot.types.Message):
    try:
        vPkeyIndex: str = vMessage.text or ''
        vPkeyIndex = fPayoffPkey(vPkeyIndex)
        vBot.reply_to(vMessage, vBotTextTable['Admin_Payoff_Success'].replace('{PKey}', vPkeyIndex), reply_markup = vMarkupAdmin)
    except Exception as vError:
        logging.error('failed payoff: ' + str(vError))
        vBot.reply_to(vMessage, vBotTextTable['Admin_Payoff_Failure'], reply_markup = vMarkupAdmin)
### fHandle_Msg_Admin_Payoff_Input
def fHandle_Msg_Admin_Payoff_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if not fVetAdmin(vUserObject):
        vBot.reply_to(vMessage, vBotTextTable['Admin_Failure'])
        vBot.send_message(vMessage.chat.id, vBotTextTable['Start'], reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, vBotTextTable['Admin_Payoff_Input'], reply_markup = vMarkupCancel)
    vBot.register_next_step_handler(vMessage, fHandle_Msg_Admin_Payoff_Input)
### fHandle_Msg_Admin_Payoff_Main
@vBot.message_handler(commands=['admin_payoff'])
def fHandle_Msg_Admin_Payoff_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Admin_Payoff_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Admin_Payoff_Proxy

def fHandle_Msg_Admin_Help_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    if not fVetAdmin(vUserObject):
        vBot.reply_to(vMessage, vBotTextTable['Admin_Failure'])
        vBot.send_message(vMessage.chat.id, vBotTextTable['Start'], reply_markup = vMarkupMain)
        return
    vBot.reply_to(vMessage, vBotTextTable['Admin_Help'], reply_markup = vMarkupAdmin)
@vBot.message_handler(commands = ['admin', 'admin_help'])
def fHandle_Msg_Admin_Help_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Admin_Help_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Admin_Help_Proxy

def fHandle_Msg_Cancel_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    vBot.reply_to(vMessage, vBotTextTable['Cancel'], reply_markup = vMarkupMain)
    vBot.clear_step_handler_by_chat_id(vMessage.chat.id)
@vBot.message_handler(commands = ['cancel'])
def fHandle_Msg_Cancel_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Cancel_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Cancel_Proxy

def fHandle_Msg_Return_Main(vMessage: telebot.types.Message, vUserObject: telebot.types.User):
    vBot.clear_step_handler_by_chat_id(vMessage.chat.id)
    fHandle_Msg_Start_Main(vMessage, vUserObject)
@vBot.message_handler(commands = ['return'])
def fHandle_Msg_Return_Proxy(vMessage: telebot.types.Message):
    fHandle_Msg_Return_Main(vMessage, vMessage.from_user)
### fHandle_Msg_Return_Proxy

vQueryCallbackTable: dict = {
    'profile': fHandle_Msg_Profile_Main,
    'mykeys': fHandle_Msg_MyKeys_Main,
    'trouble': fHandle_Msg_Trouble_Main,
    'activate': fHandle_Msg_Activate_Main,
    'help': fHandle_Msg_Help_Main,
    'info': fHandle_Msg_Info_Main,
    'support': fHandle_Msg_Support_Main,
    'admin_create': fHandle_Msg_Admin_Create_Main,
    'admin_delete': fHandle_Msg_Admin_Delete_Main,
    'admin_payoff': fHandle_Msg_Admin_Payoff_Main,
    'admin_help': fHandle_Msg_Admin_Help_Main,
    'cancel': fHandle_Msg_Cancel_Main,
    'return': fHandle_Msg_Return_Main,
}
@vBot.callback_query_handler(func = lambda call: True)
def fHandle_Query(vQuery: telebot.types.CallbackQuery):
    vQueryCallbackTable[vQuery.data](vQuery.message, vQuery.from_user)
### fHandle_Query

'''
Ебанутая магия здесь тварится;
Только потому, что ебучие недоделки InlineKeyboardButton
не могут отсылать query через ReplyKeyboard сука;
Я того мир ебал;
Дополнительно обрабатывать ВСЕ текстовые сообщения
только из-за этой тупой хуеты;
'''
vMsgToCmdTable: dict = {
    vBotTextTable['Activate_Markup']: fHandle_Msg_Activate_Proxy,
    vBotTextTable['Trouble_Markup']: fHandle_Msg_Trouble_Proxy,
    vBotTextTable['Profile_Markup']: fHandle_Msg_Profile_Proxy,
    vBotTextTable['Help_Markup']: fHandle_Msg_Help_Proxy,
}
@vBot.message_handler(func = lambda message: True, content_types = [ 'text' ])
def fHandle_Msg_Text(vMessage: telebot.types.Message):
    vCmd = vMsgToCmdTable.get(vMessage.text or '')
    if vCmd:
        vCmd(vMessage)
### fHandle_Msg_Text

from ischedule import schedule, run_loop

vScheduleEvent: threading.Event = threading.Event()
def fSchedulePeriod():
    schedule(fReviewPkeyTable, interval = datetime.timedelta(minutes = 1))
    schedule(fDbSaveAll, interval = datetime.timedelta(minutes = 1))
    run_loop(stop_event = vScheduleEvent)
### fSchedulePeriod
vScheduleThread: threading.Thread = threading.Thread(target = fSchedulePeriod)

import atexit
atexit.register(fDbSaveAll)
atexit.register(fReviewPkeyTable)

try:
    vScheduleThread.start()
    vBot.infinity_polling()
except KeyboardInterrupt as vError:
    logging.warning('interrupted by keyboard ! ' + str(vError))
except Exception as vError:
    logging.warning('An unexpected error happened ! ' + str(vError))
finally:
    vScheduleEvent.set()
    vScheduleThread.join()
