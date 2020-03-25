'''Script that defines API and runs app.'''

import json
from flask import Flask, jsonify, request#, render_template

from noobcash.node import Node
from noobcash.helpers import pubk_to_key
from noobcash.transaction import Transaction
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
    print('\nREST /wallets\n')
    wallet_dict = json.loads(request.data)
    NODE.receive_wallets(wallet_dict=wallet_dict)
    return jsonify(None), 200

@app.route('/transaction', methods=['POST'])
def receive_transaction():
    '''Receive transaction.'''
    print('\nREST /transaction\n')
    transaction_dict = json.loads(request.data)
    transaction_id = Transaction.from_dict(transaction_dict).transaction_id  # TODO: Remove line
    print(f'\nReceived transaction with id: {transaction_id}.\n')  # TODO: Remove line
    NODE.receive_transaction(transaction=transaction_dict)
    return jsonify(None), 200

@app.route('/mined_block', methods=['POST'])
def handle_miner():
    '''Miner process sent a block.'''
    block_dict = json.loads(request.data)
    NODE.check_my_mined_block(block_dict=block_dict)
    return jsonify(None), 200

@app.route('/block', methods=['POST'])
def receive_block():
    '''Another node sent a block.'''
    print('\nREST /block\n')
    block_dict = json.loads(request.data)
    NODE.receive_block(block_dict=block_dict)
    return jsonify(None), 200

@app.route('/length', methods=['GET'])
def send_blockchain_length():
    '''Return blockchain length.'''
    return jsonify(len(NODE.blockchain)), 200

@app.route('/blockchain', methods=['GET'])
def send_blockchain():
    '''Send blockchain.'''
    blockchain_dict = NODE.blockchain.to_dict()
    return jsonify(blockchain_dict), 200

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

    if NODE.nodes == len(NODE.ring):
        NODE.broadcast_wallets()
        NODE.broadcast_initial_transactions()
        return jsonify(True), 200
    return jsonify(False), 200

@app.route('/purchase', methods=['POST'])
def create_transaction():
    '''Create transaction ordered from cli.'''
    req_dict = json.loads(request.data)
    receiver_idx = req_dict['receiver_idx']
    amount = req_dict['amount']
    valid = NODE.create_transaction(receiver_idx=receiver_idx, amount=amount)
    return jsonify(valid), 200

@app.route('/black_hat_purchase', methods=['POST'])
def scripted_transaction():
    '''Create transaction ordered from script.'''
    req_dict = json.loads(request.data)
    receiver_idx = req_dict['receiver_idx']
    amount = req_dict['amount']
    valid = NODE.create_transaction(receiver_idx=receiver_idx, amount=amount)
    if not valid:
        NODE.send_bogus_transaction(receiver_idx=receiver_idx, amount=amount)

    return jsonify(valid), 200


@app.route('/id', methods=['GET'])
def get_id():
    try:
        if NODE.nodes - 1 > len(NODE.transaction_queue):
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

    # NOTE: init bootstrap before others
    NODE = Node(bootstrap_address=BOOTSTRAP_ADDRESS, capacity=CAPACITY, difficulty=DIFFICULTY,
                port=PORT, nodes=N_NODES, is_bootstrap=IS_BOOTSTRAP)

    app.run(host='0.0.0.0', port=PORT, threaded=False)
