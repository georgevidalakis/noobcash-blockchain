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

def highlight(string):
    '''Underline `string`.'''
    return f'\033[4m{string}\033[0m'

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
    '''Return receiver index and amount
    from transactions txt.'''
    _idx, _amount = row.split()
    return int(_idx[2:]), int(_amount)

def shorten_id(tid):
    '''Printable SHA hashes.'''
    return f'{tid[:4]}...{tid[-3:]}'


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
#with open(os.devnull, 'w') as fp:
with open('log.txt', 'w') as fp:
    APP = subprocess.Popen(CMD_NODE, shell=True, stdout=fp, stderr=fp)
time.sleep(3) # wait for app to launch

HTTP = urllib3.PoolManager()

### if bootstrap, notify app to send wallets and transactions

WAIT_MSG = 'Waiting for network to be established...'
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
    print(nbc_cmd('\nStarting script\n'))

    lines = open(ARGS.script).readlines()
    rows = map(get_row, lines)
    
    timestamp = time.time()

    for row in rows:
        idx, amount = row

        # Uncomment next 2 lines to run given scripts with <5 / <10 nodes
        #if idx >= NODES:
        #    continue

        transaction = {'receiver_idx': idx, 'amount': amount}
        # print(nbc_cmd('Sending ') + str(amount) + \
        #       nbc_cmd(f' NBC{"s" if amount > 1 else ""} to node ') + str(idx))

        try:
            status = HTTP.request('POST', f'{URL}/black_hat_purchase',
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps(transaction)).status
        except Exception:
            continue # avoid "Remote end closed connection without response"

        if status != 200:
            print(error('Error while executing script!'))
            os.system(f'kill $(lsof -t -i:{PORT})')
            break
    
    duration = time.time() - timestamp
    print(f'Duration of transactions\' execution: {duration:.2f}sec.')

    try:
        if status == 200:
            print(nbc_cmd('\nFinished script. It may take some time\
                \nfor all nodes to complete their script\n'))
    except:
        print(nbc_cmd('\nFinished script. It may take some time\
                \nfor all nodes to complete their script\n'))

# actual cli loop

HELP = '''This is the NOOBCASH command line interface.

To launch shell, execute cli.py [-h] [-p PORT] [-b] [-c CAPACITY] [-n NODES] [-d DIFFICULTY]
                                [-a BOOTSTRAP_ADDRESS] [-s SCRIPT]

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
                        Bootstrap's ip+port
  -s SCRIPT, --script SCRIPT
                        filename of transactions to execute

While using the shell, use following commands:
  help                  show this help message
  view                  show all transactions in the last
                        validated block of blockchain
  view_blockchain       show all transactions in the
                        current blockchain
  balance               show current balance
  balances              show balances of all nodes as
                        reflected in blockchain  
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
                        nbc_cmd(f' NBC coin{"s" if AMOUNTI > 1 else ""} to node ') + IDX)
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
            t_sum = f'\t{nbc_cmd("From")}: {transaction["sender"]}, ' + \
                    f'{nbc_cmd("To")}: {transaction["receiver"]}, ' + \
                    f'{nbc_cmd("Amount")}: {transaction["amount"]}'
            print(t_sum)

    elif CMD == 'view_blockchain':
        print(nbc_cmd('Current blockchain:\n'))
        BLOCKCHAIN = json.loads(HTTP.request('GET', f'{URL}/view_blockchain',
                                             headers={'Accept': 'application/json'}).data)

        transaction = BLOCKCHAIN[0]['transactions'][0]
        t_sum = f'\t\t{nbc_cmd("From")}: {transaction["sender"]}, ' + \
                f'{nbc_cmd("To")}: {transaction["receiver"]}, ' + \
                f'{nbc_cmd("Amount")}: {transaction["amount"]}'
        print(nbc_cmd('\tBlock no.'), end='')
        print(f'0:\n{t_sum}')

        for index, block in enumerate(BLOCKCHAIN[1:]):
            order = ['st', 'nd', 'rd', 'th']
            print(nbc_cmd('\tBlock no.'), end='')
            print(f'{index+1}:')
            for transaction in block['transactions']:
                t_sum = f'\t\t{nbc_cmd("ID")}: {shorten_id(transaction["transaction_id"])}, ' + \
                        f'{nbc_cmd("From")}: {transaction["sender"]}, ' + \
                        f'{nbc_cmd("To")}: {transaction["receiver"]}, ' + \
                        f'{nbc_cmd("Amount(s)")}: ' + \
                        f'{", ".join(map(str, transaction["amounts"]))}, ' + \
                        f'{nbc_cmd("Inputs")}: ' + \
                        f'{", ".join(map(shorten_id, transaction["transaction_inputs"]))}'
                print(t_sum)

    elif CMD == 'balance':
        BALANCE = json.loads(HTTP.request('GET', f'{URL}/balance',
                                          headers={'Accept': 'application/json'}).data)
        print(str(BALANCE) + ' ' + nbc_cmd('NBC coins'))

    elif CMD == 'balances':
        BALANCES = json.loads(HTTP.request('GET', f'{URL}/balances',
                                           headers={'Accept': 'application/json'}).data)

        print(', '.join([str(BALANCES[k]) if int(k) != MY_ID else highlight(BALANCES[k]) \
            for k in BALANCES]) + ' -> ' + str(sum(BALANCES.values())) + \
            nbc_cmd(' NBC coins'))

    elif CMD == 'help':
        print(nbc_cmd(HELP))

    elif CMD == 'exit':
        break

    else:
        print(error(f'Nonexistent command: {CMD}. Try typing: help'))

    print()

os.system(f'kill $(lsof -t -i:{PORT})')