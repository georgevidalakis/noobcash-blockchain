'''Command line interface for cryptocurrency `noobcash`.

Usage:

python cli.py [-ip HOST] [-p PORT] [-b]'''

import argparse
import subprocess
import os
import sys
import signal
import time
import json
import urllib3

from flask import jsonify

def nbc_cmd(string):
    '''Turn `string` purple.'''
    return f'\033[35m{string}\033[00m'

def error(string):
    '''Turn `string` red.'''
    return f'\033[91m{string}\033[00m'

def prompt(string):
    '''Turn `string` green.'''
    return f'\033[92m{string}\033[00m'

def interrupt_handler(signal_received, frame):
    '''Handle `Ctrl-C` and `Ctrl-D`.'''

    try:
        APP
        print('Terminating Flask app.')
        os.system(f'kill $(lsof -t -i:{PORT})')
    except NameError:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, interrupt_handler)

### parse arguments at startup

PARSER = argparse.ArgumentParser()

PARSER.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
PARSER.add_argument('-b', '--bootstrap', default=False, action='store_true',
                    help='whether this node is bootstrap')
PARSER.add_argument('-c', '--capacity', default=10, type=int,
                    help='number of transactions in a block')
PARSER.add_argument('-n', '--nodes', default=5, type=int, help='number of nodes in the network')
PARSER.add_argument('-d', '--difficulty', default=3, type=int, help='difficulty of mining')
PARSER.add_argument('-a', '--bootstrap_address', default='', type=str,
                    help='Bootstrap\'s ip+port')

ARGS = PARSER.parse_args()

PORT = ARGS.port
URL = f'127.0.0.1:{PORT}'
BOOTSTRAP = ARGS.bootstrap
CAPACITY = ARGS.capacity
N = ARGS.nodes
DIFFICULTY = ARGS.difficulty
BOOTSTRAP_URL = ARGS.bootstrap_address

### end parsing

### run app

CMD_NODE = 'python noobcash/rest.py' + \
           f' -p {PORT}' + (' -b' if BOOTSTRAP else '') + \
           f' -c {CAPACITY} -n {N} -d {DIFFICULTY}' + \
           f' -a \'{BOOTSTRAP_URL}\''

# suppress output of flask app
# with open(os.devnull, 'w') as fp:
#     APP = subprocess.Popen(CMD_NODE, shell=True, stdout=fp, stderr=fp)
# time.sleep(2) # wait for app to launch

HTTP = urllib3.PoolManager()

### if bootstrap, notify app to send wallets and transactions

if BOOTSTRAP:
    # get at /ring returns if every node has been registered
    # should broadcast transactions and wallets afterwards
    while not json.loads(HTTP.request('GET', f'{URL}/ring',
                                      headers={'Accept': 'application/json'}).data):
        print('Waiting network establishment...')
        time.sleep(3)
    print('Network established!')

# actual cli loop

while True:
    CMD = input(prompt('noobcash') + '> ')
    print()
    if CMD.startswith('t '):
        try:
            _, IDX, AMOUNT = CMD.split()
            IDXi = int(IDX)
            AMOUNTi = int(AMOUNT)

            if str(IDXi) != IDX or str(AMOUNTi) != AMOUNT:
                print(error('Wrong transaction parameters'))
            else:
                transaction = {'receiver_idx': IDXi, 'amount': AMOUNTi}
                status = HTTP.request('POST', f'{URL}/purchase',
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps(transaction)).status

                if status == 200:
                    print(nbc_cmd('Sending ') + AMOUNT + nbc_cmd(f' NBC{"s" if int(AMOUNT) > 1 else ""} to node ') + IDX)
                else:
                    print(error('Unsuccessful transaction. Aborting...'))
                    break
        except:
            print(error('Wrong transaction parameters'))


    elif CMD == 'view':
        print(nbc_cmd('Last block transactions:\n'))
        BLOCK = json.loads(HTTP.request('GET', f'{URL}/view',
                                        headers={'Accept': 'application/json'}).data)

        for transaction in BLOCK['transactions']:
            t_summary = f'{nbc_cmd("From")}: {transaction["sender"]}, ' + \
                        f'{nbc_cmd("To")}: {transaction["receiver"]}, ' + \
                        f'{nbc_cmd("Amount")}: {transaction["amount"]}'
            print(t_summary)

    elif CMD == 'balance':
        BALANCE = json.loads(HTTP.request('GET', f'{URL}/balance',
                                          headers={'Accept': 'application/json'}).data)
        print(str(BALANCE) + ' ' + nbc_cmd('coins'))

    elif CMD == 'help':
        print(nbc_cmd('HELP'))

    elif CMD == 'exit':
        break

    else:
        print(error(f'Non-existent command: {CMD}. Try typing `help`.'))

    print()

os.system(f'kill $(lsof -t -i:{PORT})')
