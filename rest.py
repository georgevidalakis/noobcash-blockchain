import requests
from flask import Flask, jsonify, request, render_template
#from flask_cors import CORS

import time

from test import Test

'''
import block
import node
import blockchain
import wallet
import transaction
import wallet
'''

### JUST A BASIC EXAMPLE OF A REST API WITH FLASK



app = Flask(__name__)
#CORS(app)
#blockchain = Blockchain()
loopy = Test()


#.......................................................................................

@app.route('/test')
def test():
    loopy.inc(True)

    return request.host, 200

@app.route('/trial')
def trial():
    
    return str(loopy.a), 200

# get all transactions in the blockchain

@app.route('/transactions/get', methods=['GET'])
def get_transactions():
    transactions = blockchain.transactions

    response = {'transactions': transactions}
    return jsonify(response), 200



# run it once fore every node

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)