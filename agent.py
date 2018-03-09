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
debug = False
dump = True
clone = False
olist = None
dumpdata = [{}]
dd_lock = pygics.Lock()

class ObjectHandler(acidipy.Event):
    
    def __handle_delta__(self, status, obj):
        if status == 'created': dumpdata[0][self.class_name][obj['dn']] = obj
        elif status == 'deleted': dumpdata[0][self.class_name].pop(obj['dn'])
        else:
            for key, val in obj.items(): dumpdata[0][self.class_name][obj['dn']][key] = val
    
    def __handle_event__(self, status, obj):
        logstash_sock.send(json.dumps(obj) + '\n')
    
    def handle(self, status, obj):
        if self.class_name == 'healthInst': obj['cur'] = int(obj['cur'])
        if obj['modTs'] == 'never': obj.pop('modTs')
        obj['class_name'] = self.class_name
        dd_lock.on()
        if dump: self.__handle_delta__(status, obj)
        else: self.__handle_event__(status, obj)
        dd_lock.off()
        if debug: print 'subscribe|%s|%s' % (self.class_name, str(obj))

class Forwarder(pygics.Task):
    
    def __init__(self):
        pygics.Task.__init__(self, tick=refresh)
        if dump: self.start()
        else: self.__init_event__()
    
    def __dump__(self):
        if debug: print 'update dump --> ',
        try:
            dumpdata[0] = {}
            for class_name in olist:
                dumpdata[0][class_name] = {}
                objs = apic_ctrl.Class(class_name).list(detail=True)
                for obj in objs:
                    if class_name == 'healthInst': obj['cur'] = int(obj['cur'])
                    if obj['modTs'] == 'never': obj.pop('modTs')
                    obj['class_name'] = class_name
                    dumpdata[0][class_name][obj['dn']] = obj
                if not clone: apic_ctrl.Class(class_name).event(ObjectHandler())
        except Exception as e:
            if debug: 
                print '[ FAILED ]'
                print str(e)
            logstash_sock.close()
            apic_ctrl.close()
            exit(1)
        if debug: print '[ OK ]'
    
    def __init_event__(self):
        if debug: print 'subscribe event --> ',
        try:
            for class_name in olist: apic_ctrl.Class(class_name).event(ObjectHandler())
        except Exception as e:
            if debug:
                print '[ FAILED ]'
                print str(e)
            logstash_sock.close()
            apic_ctrl.close()
            exit(1)
        if debug: print '[ OK ]'
        
    def __run__(self):
        if not clone: dd_lock.on()
        if dumpdata[0] == {}: self.__dump__()
        else: self.__dump__()
        for cdata in dumpdata[0].values():
            for data in cdata.values():
                msg = json.dumps(data) + '\n'
                logstash_sock.send(msg)
        if not clone: dd_lock.off()

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='debug mode')
    parser.set_defaults(debug=False)
    parser.add_argument('-l', '--logstash', help='logstash ip address', required=True)
    parser.add_argument('-c', '--clonemode', dest='clone', action='store_true', help='clone dump mode : always retrieving all object from ACI to send to logstash. ignoring eventmode argument.')
    parser.set_defaults(clone=False)
    parser.add_argument('-e', '--eventmode', dest='dump', action='store_false', help='event trigger mode : sending just delta object to logstash. ignoring refresh argument.')
    parser.set_defaults(dump=True)
    parser.add_argument('-r', '--refresh', default=30, help='refresh seconds of dump mode')
    parser.add_argument('-a', '--apic', help='apic ip address', required=True)
    parser.add_argument('-u', '--username', help='apic user', required=True)
    parser.add_argument('-p', '--password', help='apic password', required=True)
    parser.add_argument('-o', '--objects', nargs='+', help='inspect target objects', required=True)
    
    args = parser.parse_args()
    debug = args.debug
    logstash_ip = args.logstash
    refresh = int(args.refresh)
    clone = args.clone
    dump = True if clone else args.dump
    apic_ip = args.apic
    apic_user = args.username
    apic_pass = args.password
    olist = args.objects
    
    if debug: 
        print 'setting is ...'
        print 'debug :', debug
        print 'logstash :', logstash_ip
        print '  dump :', dump
        print '  clone :', clone
        print '  dump-refresh :', refresh
        print 'apic :', apic_ip
        print '  username :', apic_user
        print '  password :', apic_pass
        print 'objects :', olist
        print ''
    
    if debug: print 'try to connect APIC --> ',
    try:
        apic_ctrl = acidipy.Controller(apic_ip, apic_user, apic_pass)
    except Exception as e:
        if debug:
            print '[ FAILED ]'
            print str(e)
        exit(1)
    else:
        if debug: print '[ OK ]'
    
    if debug: print 'try to connect Logstash --> ',
    try:
        logstash_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logstash_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        logstash_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        logstash_sock.connect((logstash_ip, 8929))
    except Exception as e:
        if debug: 
            print '[ FAILED ]'
            print str(e)
        apic_ctrl.close()
        exit(1)
    else:
        if debug: print '[ OK ]'

    Forwarder()
    
    pygics.Task.idle()
