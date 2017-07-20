# -*- coding: utf-8 -*-
'''
Created on 2017. 7. 20.
@author: HyechurnJang
'''

import json
import socket
import pygics
import acidipy
import argparse

apic_ip = None
apic_user = None
apic_pass = None
apic_ctrl = None
logstash_ip = None
logstash_sock = None
refresh = None
olist = None
livedata = {}
ld_lock = pygics.Lock()

class Sender(pygics.Task):
    
    def __init__(self, tick):
        pygics.Task.__init__(self, tick=tick)
        self.start()
    
    def run(self):
        ld_lock.acquire()
        for cdata in livedata.values():
            for data in cdata.values():
                msg = json.dumps(data) + '\n'
                logstash_sock.send(msg)
        ld_lock.release()
        print 'sending refresh data'

class Subscriber(acidipy.SubscribeHandler):
    
    def subscribe(self, status, obj):
        if self.class_name == 'healthInst': obj['cur'] = int(obj['cur'])
        ld_lock.acquire()
        if status == 'created':
            obj['class_name'] = self.class_name
            obj['rn'] = obj['dn']
            livedata[class_name][obj['dn']] = obj
        elif status == 'deleted':
            livedata[class_name].pop(obj['dn'])
        else:
            for key, val in obj.items():
                livedata[class_name][obj['dn']][key] = val
        ld_lock.release()
        print 'subscribe :', status
        print json.dumps(obj, indent=2)
        print ''

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-l', '--logstash', help='logstash ip address', required=True)
    parser.add_argument('-a', '--apic', help='apic ip address', required=True)
    parser.add_argument('-u', '--user', help='apic user', required=True)
    parser.add_argument('-p', '--password', help='apic password', required=True)
    parser.add_argument('-r', '--refresh', default=10, help='refresh seconds')
    parser.add_argument('-o', '--objects', nargs='+', help='inspect target objects', required=True)
    args = parser.parse_args()
    logstash_ip = args.logstash
    apic_ip = args.apic
    apic_user = args.user
    apic_pass = args.password
    refresh = int(args.refresh)
    olist = args.objects
    
    print 'try to connect APIC --> ',
    try:
        apic_ctrl = acidipy.Controller(apic_ip, apic_user, apic_pass)
    except:
        print '[ FAILED ]'
        exit(1)
    else:
        print '[ OK ]'
    
    print 'try to connect Logstash --> ',
    try:
        logstash_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logstash_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        logstash_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        logstash_sock.connect((logstash_ip, 8929))
    except:
        print '[ FAILED ]'
        apic_ctrl.close()
        exit(1)
    else:
        print '[ OK ]'
    
    print 'collect initial data --> ',
    try:
        for class_name in olist:
            livedata[class_name] = {}
            results = apic_ctrl.Class(class_name).list(detail=True)
            for result in results:
                if class_name == 'healthInst': result['cur'] = int(result['cur'])
                result['class_name'] = class_name
                result['rn'] = result['dn']
                livedata[class_name][result['dn']] = result
            apic_ctrl.Class(class_name).subscribe(Subscriber())
    except:
        print '[ FAILED ]'
        logstash_sock.close()
        apic_ctrl.close()
        exit(1)
    else:
        print '[ OK ]'
    
    Sender(refresh)
    
    while True: pygics.Time.sleep(36000)
