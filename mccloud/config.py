import glob, os, sys, json

from mccloud.constants import *

def read_config():
    file = CURPATH + '/config.json'
    try:
        st = os.stat(file)
    except os.error:
        print('No config.json file found. Please create it and restart!')
        exit()
    config = json.load(open(file))
    return verify_config(config)

def verify_config(json):
    required = ['BINPATH', 'ANSIBLEPATH', 'IACPATH', 'STATE', 'VAULTPASSWORD', 'PRIVATEKEY', 'PUBLICKEY']
    if 'TMPPATH' not in json:
        json['TMPPATH'] = '/tmp'
    if 'DIRECTORYPASSWORD' not in json:
        json['DIRECTORYPASSWORD'] = 'notrequired'
    for r in required:
        if r not in json:
            print('Missing ' + r + '. Please check your config!')
            exit()
    return json
