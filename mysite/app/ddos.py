#!/usr/bin/env python

import requests
import json
import time
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GridSearchCV
from sklearn.externals import joblib
import time
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
import os
import asyncio
from concurrent.futures import CancelledError
from channels.db import database_sync_to_async
from app.models import Alert, Status
from django.conf import settings


class GenerateConsumer(AsyncWebsocketConsumer):
    # buka file model
    module_dir = os.path.dirname(__file__)  # get current directory
    file_path = os.path.join(module_dir, 'includes/rf_gridcv_tanpa_scaler_100-est-log2.pkl')
    # file_path = os.path.join(module_dir, 'includes/v-rf_gridcv_tanpa-scaler.pkl')    
    # with open(file_path, 'rb') as handle:
    #     model = pickle.load(handle)
    
    model = joblib.load(file_path)
    
    sflow_host = settings.SFLOW_HOST
    sflow_port = settings.SFLOW_PORT
    detection_network = settings.DETECTION_NETWORK

    rt = sflow_host+":"+sflow_port

    requests.delete(rt + '/group/ddos/json')
    requests.delete(rt + '/flow/ddos/json')

    groups = {'external': ['0.0.0.0/0'], 'internal': detection_network}
    _flows = {'keys': 'ipsource,ipdestination,ipbytes,ipprotocol,if:ipprotocol:17:udpdestinationport:tcpdestinationport,frames,null:tcpflags:000000000,if:ipprotocol:17:udpbytes:tcppayloadbytes,bytes',
              'value': 'rate:frames', 'filter': 'group:ipdestination:ddos=internal', 'log': False}

    r = requests.put(rt + '/group/ddos/json', data=json.dumps(groups))
    r = requests.put(rt + '/flow/ddos/json', data=json.dumps(_flows))

    async def getflag(self, bin_val):
        result = {'ECE': 0, 'URG': 0, 'PSH': 0,
                  'RST': 0, 'ACK': 0, 'SYN': 0, 'FIN': 0}
        if bin_val[2] == '1':
            result['ECE'] += 1
        if bin_val[3] == '1':
            result['URG'] += 1
        if bin_val[4] == '1':
            result['ACK'] += 1
        if bin_val[5] == '1':
            result['PSH'] += 1
        if bin_val[6] == '1':
            result['RST'] += 1
        if bin_val[7] == '1':
            result['SYN'] += 1
        if bin_val[8] == '1':
            result['FIN'] += 1

        return result

    async def getProto(self, proto_val):
        result = {'Protocol_0': 0, 'Protocol_6': 0, 'Protocol_17': 0}
        if int(proto_val) == 0:
            result['Protocol_0'] += 1
        if int(proto_val) == 6:
            result['Protocol_6'] += 1
        if int(proto_val) == 17:
            result['Protocol_17'] += 1

        return result

    async def triggerWorker(self, message):
        # Join room group
        message['message'] = "sent from ddos worker"
        await self.channel_layer.group_add(
            "testGroup",
            self.channel_name
        )
        print(message['command'])
        loop = asyncio.get_event_loop()
        pending = asyncio.Task.all_tasks()
        try:
            for task in pending:
                # print(task)
                if task._coro.__qualname__ == "GenerateConsumer.run":
                    task.cancel()
        except CancelledError as e:
            print(e)
        finally:    
            if message['command'] == "start":
                try:
                    asyncio.ensure_future(GenerateConsumer.run(self, message))
                except Exception as e:
                    print(e)
                finally:
                    await self.save_status(True)
            elif message['command'] == "stop":
                # Let's also cancel all running tasks:
                try:
                    asyncio.ensure_future(GenerateConsumer.run(self, message))
                except Exception as e:
                    print(e)
                finally:
                    await self.save_status(False)

    async def echo_msg(self, message):
        print("Message to WebsocketConsumer", message)
        # await self.channel_layer.send("alert-generate",json.dumps(message))

    async def alert(self, message):
        pass
        # print("Message to WebsocketConsumer", message)
        # await self.send(json.dumps(message))

    async def status(self, message):
        pass
        # print("Status : "+message["status"])

    async def dict_compare(self, d1, d2):
        d1_keys = set(d1.keys())
        d2_keys = set(d2.keys())
        intersect_keys = d1_keys.intersection(d2_keys)
        same = set(o for o in intersect_keys if d1[o] == d2[o])
        return same

    async def run(self, event):
        try:
            flows_prev = {}
            _sleep = 2
            command = event['command']
            message = event['message']
            # status = await self.get_status()
            if command == "start":
                while True:
                    predict = []
                    df = pd.DataFrame(columns=['URG Flag Cnt',	'SYN Flag Cnt',	'RST Flag Cnt',	'PSH Flag Cnt',	'Pkt Size Avg',
                                               'Flow Pkts/s',	'FIN Flag Cnt',	'ECE Flag Cnt',	'ACK Flag Cnt',	'Dst Port',
                                               'Protocol_0',	'Protocol_6',	'Protocol_17'])

                    r = requests.get(
                        GenerateConsumer.rt+'/activeflows/ALL/ddos/json?maxFlows=15', data=json.dumps(GenerateConsumer._flows))
                    flows = r.json()

                    if flows_prev == {}:
                        flows_prev = flows

                    if r.status_code != 200:
                        break

                    # if len(flows) == 0:
                    #     continue

                    if len(flows) != 0 and len(flows_prev) == len(flows):                    
                        for idx, f in enumerate(flows):
                            pred = {}
                            same = await self.dict_compare(f, flows_prev[idx])
                            if not all(x in same for x in ['agent', 'flowN', 'dataSource', 'key']):
                                key = f.get('key', None)
                                agent = f.get('agent', None)
                                ds = f.get('dataSource', None)

                                words = key.split(",")
                                flag = await self.getflag(words[6])
                                proto = await self.getProto(words[3])
                                pred['IP Source'] = words[0]
                                pred['IP Destination'] = words[1]
                                pred['Pkt Size Avg'] = int(words[7])
                                pred['URG Flag Cnt'] = int(flag.get('URG', None))
                                pred['SYN Flag Cnt'] = int(flag.get('SYN', None))
                                pred['RST Flag Cnt'] = int(flag.get('RST', None))
                                pred['PSH Flag Cnt'] = int(flag.get('PSH', None))
                                pred['FIN Flag Cnt'] = int(flag.get('FIN', None))
                                pred['ECE Flag Cnt'] = int(flag.get('ECE', None))
                                pred['ACK Flag Cnt'] = int(flag.get('ACK', None))
                                pred['Protocol_0'] = int(proto.get('Protocol_0', None))
                                pred['Protocol_6'] = int(proto.get('Protocol_6', None))
                                pred['Protocol_17'] = int(
                                    proto.get('Protocol_17', None))
                                pred['Dst Port'] = int(words[4])
                                pred['Flow Pkts/s'] = float(f.get('value', None))
                                pred['DataSource'] = ds
                                pred['Agent'] = agent

                                predict.append(pred)
                                # print(pred)

                    flows_prev = flows
                    # print(predict)
                    if len(predict) > 1:
                        for i, val in enumerate(predict):
                            df.loc[i] = [val.get('URG Flag Cnt'), val.get('SYN Flag Cnt')	, val.get('RST Flag Cnt')	, val.get('PSH Flag Cnt')	, val.get('Pkt Size Avg')	,
                                        val.get('Flow Pkts/s')	, val.get('FIN Flag Cnt')	, val.get('ECE Flag Cnt')	, val.get('ACK Flag Cnt')	, val.get('Dst Port')	, 
                                        val.get('Protocol_0')	, val.get('Protocol_6')	    , val.get('Protocol_17')]

                        testdata = np.array(df)

                        predicted = GenerateConsumer.model.predict(testdata)
                        df['Predicted'] = predicted
                        df['Timestamp'] = [datetime.datetime.now() for i in enumerate(predicted)]
                        df['IP Source'] = [val.get('IP Source') for i, val in enumerate(predict)]
                        df['IP Destination'] = [val.get('IP Destination') for i, val in enumerate(predict)]
                        # if file does not exist write header
                        # filepath = 'nama_file.txt'
                        # filename = ''
                        # with open(filepath) as fp:  
                        #     filename = fp.readline().strip()
                        # print("Filename : "+filename)
                        # if not os.path.isfile(filename):
                        #     df.to_csv(filename, header='column_names')
                        # else: # else it exists so append without writing the header
                        #     df.to_csv(filename, mode='a', header=False)
                        # print(predicted)
                        itemindex = np.where(predicted == 1)
                        if len(itemindex[0]) > 0:
                            _sleep = 0
                            for (x, y), value in np.ndenumerate(itemindex):
                                ts = time.time()
                                st = datetime.datetime.fromtimestamp(
                                    ts).strftime('%Y-%m-%d %H:%M:%S')
                                _msg = {
                                    "msg": message,
                                    "ip_source": str(predict[value]['IP Source']),
                                    "ip_destination": str(predict[value]['IP Destination']),
                                    "port": str(predict[value]['Dst Port']),
                                    "agent": str(predict[value]['Agent']),
                                    "datasource": str(predict[value]['DataSource']),
                                    "timestamp": st
                                }
                                await self.save_alert(_msg)
                                # await self.channel_layer.send("alert-generate",json.dumps(dict()))
                                await self.channel_layer.group_send(
                                    "testGroup",
                                    {
                                        'type': 'alert',
                                        'message': _msg
                                    })
                        else:
                            _sleep = 2

                    await self.channel_layer.group_send(
                        "testGroup",
                        {
                            'type': 'status',
                            'status': 'aktif'
                        })
                    print(str(_sleep))
                    await asyncio.sleep(_sleep)
                    # asyncio.sleep(3)
            elif command == "stop":
                while True:
                    await self.channel_layer.group_send(
                        "testGroup",
                        {
                            'type': 'status',
                            'status': 'tidak aktif'
                        })
                    await asyncio.sleep(3)
        except Exception as e:
            print(e)
            # pass
        except KeyboardInterrupt as e:
            await self.save_status(False)


    @database_sync_to_async
    def save_alert(self, params):
        alert = Alert(
            ip_source=params['ip_source'], ip_destination=params['ip_destination'], port=params['port'], agent=params['agent'], datasource=params['datasource'])
        alert.save()

    @database_sync_to_async
    def save_status(self, status):
        if Status.objects.all().count() == 0:
            Status(status=status).save()
        else:
            _status = Status.objects.all()[0]
            _status.status = status
            _status.save()
