# -*- coding: UTF-8 -*-
#
# Author: Raphael Rabelo de Oliveira
# Website: http://rabelo.ninja
# Github: http://github.com/rabeloo
#
import boto3, re, sys
from zabbix_api import ZabbixAPI
from datetime import datetime

# Set the zabbix server informations
ZABBIX_SERVER_URL = 'http://url.to.zabbix'
ZABBIX_API_USER = '<SET_USER>'
ZABBIX_API_PASSWORD = '<SET PASSWORD>'
ZABBIX_GROUP_ID = '182'

# Set the SQS endpoint url to read messages
queueUrl='<SET_SQS_ENDPOINT>'

def eventDate():
    return str(datetime.now())

def sess(profile, region, client):
    sess = boto3.session.Session(profile_name=profile,region_name=region)
    return sess.client(client)

def readMsg(queueUrl, profileName, region):
    sqs = sess(profileName, region, 'sqs')
    message = sqs.receive_message(QueueUrl=queueUrl, WaitTimeSeconds=10)
    if message.get('Messages'):
        for msg in message.get('Messages'):
          if ( msg.has_key('Body') and msg.has_key('ReceiptHandle') ):
            instList = re.findall('i-[a-z0-9]{8,17}', msg['Body'])
            res = zabbix(list(set(instList)), msg['ReceiptHandle']) if instList else sys.exit(0)
            sys.exit(0) if res == 1 else delMsg(queueUrl, profileName, region, msg['ReceiptHandle'])
    else:
        print '[%s] No messages on queue' % eventDate()
        sys.exit(0)

def zabbix(instList, masHandle):
    zapi = ZabbixAPI(server="ZABBIX_SERVER_URL/api_jsonrpc.php")
    zapi.login(ZABBIX_API_USER, ZABBIX_API_PASSWORD)
    for instId in instList:
         if re.match('i-[a-z0-9]{8,17}', instId) is not None:
            hostInfo = zapi.host.get({ "output": ["host"], "groupids": ZABBIX_GROUP_ID, "selectInventory": ["tag"], "searchInventory": { "tag": instId }})
         else:
            print "[%s] The value (%s) doesn't match with instance-id pattern" % (eventDate(), instId)
            sys.exit(0)

    if hostInfo:
       for host in hostInfo:
           if host.has_key("hostid"):
               zapi.host.update({"hostid": hostid["hostid"], "status": "1"})
               print '[%s] Host %s (%s) was disabled from Zabbix' % (eventDate(), host['host'], instId)
               return 0
    else:
       print "The instance-id (%s) don't found ind Zabbix" % instId
       return 1

def delMsg(queueUrl, profileName, region, msgHandler):
    sqs = sess(profileName, region, 'sqs')
    sqs.delete_message(QueueUrl=queueUrl, ReceiptHandle=msgHandler)

readMsg(queueUrl, 'zabbix_deregister', 'sa-east-1')
