import requests
from flask import Flask, jsonify, request, render_template

from noobcash.node import Node
#from flask_cors import CORS

import time

'''
import block
import node
import blockchain
import wallet
import transaction
import wallet
'''

app = Flask(__name__)

#.......................................................................................

@app.route('/node', methods=['POST'])
def first_contact():
    wallet_dict = request.body
    first_contact_dict = node.register_node_to_ring(wallet_dict=wallet_dict)
    return jsonify(first_contact_dict), 200

@app.route('/wallets', methods=['POST'])
def get_wallets():
    wallet_dict = request.body
    node.receive_wallets(wallet_dict=wallet_dict)
    return jsonify(None), 200

@app.route('/transaction', methods=['POST'])
def receive_transaction():
    transaction_dict = request.body
    node.receive_transaction(transaction=transaction_dict)
    return jsonify(None), 200

@app.route('/mined_block', methods=['POST'])
def handle_miner():
    block_dict = request.body
    node.check_my_mined_block(block_dict=block_dict)
    return jsonify(None), 200

@app.route('/block', methods=['POST'])
def receive_block():
    block_dict = request.body
    node.receive_block(block_dict=block_dict)
    return jsonify(None), 200

@app.route('/length', methods=['GET'])
def send_blockchain_length():
    return len(node.blockchain), 200

@app.route('/blockchain', methods=['GET'])
def send_blockchain():
    blockchain_dict = node.blockchain.to_dict()
    return jsonify(blockchain_dict), 200

# run it once for every node

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    parser.add_argument('-b', '--bootstrap', default=False, type=bool,
                        help='whether this node is the bootstrap')
    parser.add_argument('-c', '--capacity', default=10, type=int,
                        help='number of transactions in a block')
    parser.add_argument('-n', '--nodes', default=5, type=int, help='number of nodes in the network')
    parser.add_argument('-d', '--difficulty', default=3, type=int, help='difficulty of mining')
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')


    args = parser.parse_args()
    port = args.port

    node = Node('', 5, 3, port, 10, False)


    app.run(host='0.0.0.0', port=port)
