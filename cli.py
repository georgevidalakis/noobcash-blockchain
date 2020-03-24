'''Command line interface for cryptocurrency `noobcash`.

Usage:

python cli.py [-c CAPACITY] [-n NODES] [-d DIFFICULTY] [-a BOOTSTRAP_ADDRESS]
              [-p PORT] [-b] [-s SCRIPT]'''

import argparse
import subprocess
import os
import sys
import signal
import time
import json
import urllib3

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

def get_row(row):
    idx, amount = row.split()
    return int(idx[2:]), int(amount)

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
PARSER.add_argument('-s', '--script', type=str, help='filename of transactions to execute')

ARGS = PARSER.parse_args()

PORT = ARGS.port
URL = f'127.0.0.1:{PORT}'
BOOTSTRAP = ARGS.bootstrap
CAPACITY = ARGS.capacity
NODES = ARGS.nodes
DIFFICULTY = ARGS.difficulty
BOOTSTRAP_URL = ARGS.bootstrap_address

### end parsing

### run app

CMD_NODE = 'python noobcash/rest.py' + \
           f' -p {PORT}' + (' -b' if BOOTSTRAP else '') + \
           f' -c {CAPACITY} -n {NODES} -d {DIFFICULTY}' + \
           f' -a \'{BOOTSTRAP_URL}\''

# suppress output of flask app
with open(os.devnull, 'w') as fp:
    APP = subprocess.Popen(CMD_NODE, shell=True, stdout=fp, stderr=fp)
time.sleep(3) # wait for app to launch

HTTP = urllib3.PoolManager()

### if bootstrap, notify app to send wallets and transactions

WAIT_MSG = 'Waiting for network to be established'
NET_MSG = '\nNetwork established!\n'

if BOOTSTRAP:
    # get at /ring returns if every node has been registered
    # should broadcast transactions and wallets afterwards
    while not json.loads(HTTP.request('GET', f'{URL}/ring',
                                      headers={'Accept': 'application/json'}).data):
        print(WAIT_MSG)
        time.sleep(3)
    print(prompt(NET_MSG))
    MY_ID = 0
else:
    while True:
        MY_ID = json.loads(HTTP.request('GET', f'{URL}/id',
                                        headers={'Accept': 'application/json'}).data)
        if MY_ID != 0:
            print(prompt(NET_MSG))
            break
        print(WAIT_MSG)
        time.sleep(3)

if ARGS.script is not None:
    with open(ARGS.script, 'r') as transactions:
        line = transactions.readline()
        while line:
            idx, amount = get_row(line)
            transaction = {'receiver_idx': idx, 'amount': amount}
            status = HTTP.request('POST', f'{URL}/black_hat_purchase',
                                  headers={'Content-Type': 'application/json'},
                                  body=json.dumps(transaction)).status
            if status != 200:
                print(error('Error while executing script!'))

            transactions.readline()


# actual cli loop

HELP = '''This is the NOOBCASH command line interface.

To launch shell, execute cli.py [-h] [-p PORT] [-b] [-c CAPACITY] [-n NODES] [-d DIFFICULTY]
              [-a BOOTSTRAP_ADDRESS]

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  port to listen on
  -b, --bootstrap       whether this node is bootstrap
  -c CAPACITY, --capacity CAPACITY
                        number of transactions in a block
  -n NODES, --nodes NODES
                        number of nodes in the network
  -d DIFFICULTY, --difficulty DIFFICULTY
                        difficulty of mining
  -a BOOTSTRAP_ADDRESS, --bootstrap_address BOOTSTRAP_ADDRESS
                        Bootstrap's ip:port

While using the shell, use following commands:
  help                  show this help message
  view                  show all transactions in the last
                        validated block of blockchain
  balance               show balance
  t RECIPIENT_ID AMOUNT send AMOUNT noobcash coins to
                        RECIPIENT_ID node
  exit                  gracefully exit shell'''

while True:
    CMD = input(prompt('noobcash') + '@' + prompt(MY_ID) + '> ')
    while CMD.endswith('\\'):
        CMD = CMD[:-1] # remove last \
        CMD += input(' ' * (len(f'noobcash@{MY_ID}') - 2) + '... ')
    print()
    if CMD.startswith('t '):
        try:
            _, IDX, AMOUNT = CMD.split()
            IDXI = int(IDX)
            AMOUNTI = int(AMOUNT)

            if str(IDXI) != IDX or str(AMOUNTI) != AMOUNT:
                print(error('Wrong transaction parameters'))
            else:
                TRANSACTION = {'receiver_idx': IDXI, 'amount': AMOUNTI}
                RESPONSE = HTTP.request('POST', f'{URL}/purchase',
                                        headers={'Content-Type': 'application/json'},
                                        body=json.dumps(TRANSACTION))

                if RESPONSE.status == 200 and json.loads(RESPONSE.data):
                    print(nbc_cmd('Sending ') + AMOUNT + \
                        nbc_cmd(f' NBC{"s" if AMOUNTI > 1 else ""} to node ') + IDX)
                else:
                    print(error('Unsuccessful transaction. Aborting...\n'))
                    break
        except Exception:
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
        print(nbc_cmd(HELP))

    elif CMD == 'exit':
        break

    else:
        print(error(f'Nonexistent command: {CMD}. Try typing: help.'))

    print()

os.system(f'kill $(lsof -t -i:{PORT})')
