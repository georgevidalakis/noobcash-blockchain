'''Script that defines API and runs app.'''

#import sys
import time
import json
from flask import Flask, jsonify, request#, render_template

from noobcash.node import Node
from noobcash.helpers import pubk_to_key
#from noobcash.transaction import Transaction
#from flask_cors import CORS

app = Flask(__name__)

#.......................................................................................


@app.route('/node', methods=['POST'])
def first_contact():
    '''Bootstrap: Respond to first contact.'''
    wallet_dict = json.loads(request.data)
    first_contact_dict = NODE.register_node_to_ring(wallet_dict=wallet_dict)
    return jsonify(first_contact_dict), 200

@app.route('/wallets', methods=['POST'])
def get_wallets():
    '''Node:  Receive wallets from bootstrap.'''
    # print('\nREST /wallets\n')
    wallet_dict = json.loads(request.data)
    NODE.receive_wallets(wallet_dict=wallet_dict)
    return jsonify(None), 200

@app.route('/transaction', methods=['POST'])
def receive_transaction():
    '''Receive transaction.'''
    global trxs_rec

    trxs_rec += 1
    # print('\nREST /transaction\n')
    transaction_dict = json.loads(request.data)
    # transaction_id = Transaction.from_dict(transaction_dict).transaction_id
    # print(f'\nReceived transaction with id: {transaction_id}.\n')
    NODE.receive_transaction(transaction=transaction_dict)
    return jsonify(None), 200

@app.route('/mined_block', methods=['POST'])
def handle_miner():
    '''Miner process sent a block.'''
    global block_t0, block_tf

    block_dict = json.loads(request.data)
    block = NODE.check_my_mined_block(block_dict=block_dict)
    if block is not None:
        if block_t0 == 0:
            block_t0 = time.time()
        block_tf = time.time()
        NODE.broadcast_block(block)
    return jsonify(None), 200

@app.route('/block', methods=['POST'])
def receive_block():
    '''Another node sent a block.'''
    global block_t0, block_tf

    block_dict = json.loads(request.data)
    accepted = NODE.receive_block(block_dict=block_dict)
    if accepted:
        if block_t0 == 0:
            block_t0 = time.time()
        block_tf = time.time()
    return jsonify(None), 200

@app.route('/block_time', methods=['GET'])
def block_time():
    '''Get total time for blocks.'''
    global block_t0, block_tf
    return jsonify(block_tf - block_t0), 200

@app.route('/length', methods=['GET'])
def send_blockchain_length():
    '''Return blockchain length.'''
    return jsonify(len(NODE.blockchain)), 200

@app.route('/blockchain', methods=['GET'])
def send_blockchain():
    '''Send blockchain.'''
    blockchain_dict = NODE.blockchain.to_dict()
    return jsonify(blockchain_dict), 200

@app.route('/balances', methods=['GET'])
def get_balances():
    '''Send balances.'''
    balances = dict()
    for k in NODE.ring_bak:
        balances[k] = NODE.ring_bak[k].balance
    return jsonify(balances), 200

@app.route('/view_blockchain', methods=['GET'])
def view_blockchain():
    '''Return human readable blockchain'''
    blockchain_list = []
    for block in NODE.blockchain.chain:
        human_readable = dict()
        for transaction in block.list_of_transactions:
            if isinstance(transaction.sender_pubk, int):
                # genesis block
                human_readable.setdefault('transactions', []).append(
                    dict(sender='Genesis', receiver='0',
                         amount=sum([to.amount for to in transaction.transaction_outputs]))
                )
            else:
                human_readable.setdefault('transactions', []).append(
                    dict(transaction_id=transaction.transaction_id,
                         transaction_inputs=transaction.transaction_inputs,
                         sender=NODE.pubk2ind[pubk_to_key(transaction.sender_pubk)],
                         receiver=NODE.pubk2ind[pubk_to_key(transaction.receiver_pubk)],
                         amounts=[transaction_output.amount \
                             for transaction_output in transaction.transaction_outputs])
                )
        blockchain_list.append(human_readable)
    return jsonify(blockchain_list), 200

@app.route('/balance', methods=['GET'])
def balance():
    '''Return balance of node.'''
    return jsonify(NODE.my_wallet().balance), 200

@app.route('/view', methods=['GET'])
def view_transactions():
    '''Return human readable format (`sender`, `receiver`, `amount`)
    of every transacion in the last block of the blockchain.'''
    last_block = NODE.blockchain.chain[-1]
    human_readable = dict()
    for transaction in last_block.list_of_transactions:
        if isinstance(transaction.sender_pubk, int):
            # genesis block
            human_readable.setdefault('transactions', []).append(
                dict(sender='Genesis', receiver='0',
                     amount=sum([to.amount for to in transaction.transaction_outputs]))
            )
        else:
            human_readable.setdefault('transactions', []).append(
                dict(sender=NODE.pubk2ind[pubk_to_key(transaction.sender_pubk)],
                     receiver=NODE.pubk2ind[pubk_to_key(transaction.receiver_pubk)],
                     amount=transaction.transaction_outputs[0].amount)
            )
    return jsonify(human_readable), 200

@app.route('/ring', methods=['GET'])
def broadcast_info():
    '''Notify bootstrap whether all nodes in the
    network have been registered. Also, broadcasts
    wallets and initial transactions.

    Returns:

    * `True` if all nodes registered, else `False`.'''
    global wallet_broad

    if wallet_broad == 0 and NODE.nodes == len(NODE.ring):
        wallet_broad = 42
        NODE.broadcast_wallets()
        transactions = NODE.create_initial_transactions()
        for tra in transactions:
            NODE.broadcast_transaction(tra)
        return jsonify(True), 200

    return jsonify(wallet_broad == 42), 200

@app.route('/purchase', methods=['POST'])
def create_transaction():
    '''Create transaction ordered from cli.'''
    req_dict = json.loads(request.data)
    receiver_idx = req_dict['receiver_idx']
    amount = req_dict['amount']
    transaction = NODE.create_transaction(receiver_idx=receiver_idx, amount=amount)
    if transaction is not None:
        NODE.broadcast_transaction(transaction)

    return jsonify(transaction is not None), 200

@app.route('/black_hat_purchase', methods=['POST'])
def scripted_transaction():
    '''Create transaction ordered from script.'''
    req_dict = json.loads(request.data)
    receiver_idx = req_dict['receiver_idx']
    amount = req_dict['amount']
    transaction = NODE.create_transaction(receiver_idx=receiver_idx, amount=amount)
    valid = True # in case in need of stats

    if transaction is None:
        valid = False
        transaction = NODE.send_bogus_transaction(receiver_idx=receiver_idx, amount=amount)

    try:
        NODE.broadcast_transaction(transaction)
    except:
        pass

    return jsonify(valid), 200


@app.route('/id', methods=['GET'])
def get_id():
    '''Get ID bestowed by bootstrap. Return 0
    if not yet defined (0 is reserved for bootstrap,
    so 0 must be used to check if id is set, could
    be a negative number).'''

    global trxs_rec

    try:
        if NODE.nodes - 1 > trxs_rec:
            # if not all 100 transactions received, wait!
            raise AttributeError
        return jsonify(NODE.my_id), 200
    except AttributeError:
        return jsonify(0), 200

# run it once for every node

if __name__ == '__main__':
    from argparse import ArgumentParser

    PARSER = ArgumentParser()
    PARSER.add_argument('-p', '--port', default=5000, type=int, required=False,
                        help='port to listen on')
    PARSER.add_argument('-b', '--bootstrap', default=False, action='store_true',
                        required=False, help='whether this node is bootstrap')
    PARSER.add_argument('-c', '--capacity', default=10, type=int,
                        required=False, help='number of transactions in a block')
    PARSER.add_argument('-n', '--nodes', default=5, type=int, required=False,
                        help='number of nodes in the network')
    PARSER.add_argument('-d', '--difficulty', default=3, type=int, required=False,
                        help='difficulty of mining')
    PARSER.add_argument('-a', '--bootstrap_address', default='', type=str, required=False,
                        help='Bootstrap\'s ip+port')

    ARGS = PARSER.parse_args()
    PORT = ARGS.port
    IS_BOOTSTRAP = ARGS.bootstrap
    CAPACITY = ARGS.capacity
    N_NODES = ARGS.nodes
    DIFFICULTY = ARGS.difficulty
    BOOTSTRAP_ADDRESS = ARGS.bootstrap_address

    trxs_rec = 0
    wallet_broad = 0
    block_t0 = 0
    block_tf = 0

    # NOTE: init bootstrap before others
    NODE = Node(bootstrap_address=BOOTSTRAP_ADDRESS, capacity=CAPACITY, difficulty=DIFFICULTY,
                port=PORT, nodes=N_NODES, is_bootstrap=IS_BOOTSTRAP)

    app.run(host='0.0.0.0', port=PORT)
