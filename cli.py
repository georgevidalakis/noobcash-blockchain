'''Command line interface for cryptocurrency `noobcash`.

Usage:

python cli.py [-ip HOST] [-p PORT] [-b]'''

import argparse
# import os
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

# if os.system(cmd_node) != 0:
#     print(error('Could not start app.'))
#     exit(42)
# print(cmd_node)

HTTP = urllib3.PoolManager()

### if bootstrap, notify app to send wallets and transactions

# if BOOTSTRAP:
#     # get at /ring returns if every node has been registered
#     # should broadcast transactions and wallets afterwards
#     while not json.loads(http.request('GET', f'{URL}/ring',
#                          headers={'Accept': 'application/json'}).data):
#         pass

# actual cli loop

while True:
    CMD = input(prompt('noobcash') + '> ')
    print()
    if CMD.startswith('t '):
        _, IDX, AMOUNT = CMD.split()
        if IDX != str(int(IDX)) or AMOUNT != str(int(AMOUNT)):
            print(error('Wrong transaction parameters'))
        else:
            print(nbc_cmd(f'Sending {AMOUNT} NBC{"s" if int(AMOUNT) > 1 else ""} to node {IDX}'))

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
