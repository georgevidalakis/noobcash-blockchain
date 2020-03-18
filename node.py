from block import Block
from wallet import Wallet
from transaction import Transaction
from blockchain import Blockchain

import wrapt
import json
import queue
import urllib3
import jsonpickle
import numpy as np
from Crypto.Hash import SHA
from Crypto.Signature import PKCS1_v1_5
from multiprocessing.dummy import Pool as ThreadPool

from helpers import pubk_from_dict, pubk_to_dict

NUM_OF_THREADS = 3

class Node:
    '''Cryptocurrency transaction handler of a node in the network.'''

    def __init__(self, bootstrap_address: str, capacity: int, difficulty: int, port: int, n=0, is_bootstrap=False):
        '''Initialize `Node` object.

        Arguments:

        '''

        wallet = self.generate_wallet(port)

        if is_bootstrap:
            self.my_id, self.blockchain = 0, self.init_bootstrap_blockchain(n)
        else:
            self.my_id, self.blockchain = self.first_contact_data(bootstrap_address)

        # information for every node (its address (ip:port), its public key, its balance, its utxos)
        self.ring = {
            self.my_id: wallet
        }
        self.pubk2ind = dict() # public key to index correspondence

        self.transaction_queue = []

        self.capacity = capacity

        self.difficulty = difficulty

    def my_wallet(self):
        '''Get node's `Wallet`

        Returns:

        * `Wallet` w/ private key.'''

        return self.ring[self.my_id]


    def init_bootstrap_blockchain(self, n):
        '''Initialize the blockchain of the bootstrap node.

        Arguments:

        * `n`: Final number of nodes in the network
        (assumed to be known from the start).'''

        genesis_transaction = Transaction(recipient_pubk=self.my_wallet().public_key,
                                          amount=100*n, my_wallet=None)
        return Blockchain(received_blockchain=None,
                          genesis_transaction=genesis_transaction)
    
    def first_contact_data(self, bootstrap_address: str):
        '''Contact bootstrap to register into the network
        and handle the data in the response. MUST send wallet
        information and get index and current blockchain.

        Arguments:

        * `bootstrap_address`: ip+port of bootstrap (assumed
        to be known from the start).

        Returns:

        * ([ascending] ID of node in the network, validated bootstrap's blockchain).'''

        myinfo = self.wallet.to_dict()

        http = urllib3.PoolManager()

        # we are contacting the bootstrap
        # loop until we get proper chain
        while True:
            response = json.loads(http.request('POST', f'{bootstrap_address}/node',
                                               headers={'Content-Type': 'application/json'},
                                               body=myinfo).body)
            # blockchain in response is (ordered) list of blocks
            blockchain = Blockchain.from_dict(response['blockchain'])
            if self.valid_chain(chain=blockchain):
                break

        return response['id'], blockchain

    def generate_wallet(self, port: int):
        '''Generate this node's wallet.

        Arguments:

        * `port`: integer port where node is listening.

        Returns:

        * This node's `Wallet`.'''

        return Wallet(port=port, this_node=True)

    def register_node_to_ring(self, wallet_dict):
        '''Handle request to enter the network. The bootstrap node
        should register the node in `ring` and respond with index and
        current blockchain.

        Arguments:

        * `wallet_dict`: `dict` directly from `.to_dict()`.

        Returns:

        * `dict` with ['id', 'blockchain'].'''

        node_wallet = Wallet.from_dict(wallet_dict)
        # if node has already contacted before to register
        # do not produce new index, ...
        index = self.pubk2ind.get(node_wallet.public_key, len(self.pubk2ind) + 1)
        self.pubk2ind[node_wallet.public_key] = index
        self.ring[index] = node_wallet
        # we are contacting the bootstrap
        # loop until we get proper chain

        info = dict(
            blockchain=self.blockchain.to_dict(),
            id=index
        )

        return info


    def create_transaction(self, receiver_idx: int, amount: int):
        '''Create, broadcast transaction, update wallets and queue.
        NOTE: sender is this node.

        Arguments:

        * `receiver_idx`: receiver index in `ring` (chosen because
        of cli).

        * `amount`: (`int`) NBCs transfered.'''

        receiver_wallet = self.ring[receiver_idx]
        try:
            transaction = Transaction(receiver_wallet.public_key,
                                      amount, self.my_wallet())
        except TypeError: # Reject transaction, not enough cash
            return False

        self.broadcast_transaction(transaction)
        self.add_utxos(transaction.transaction_outputs)
        self.transaction_queue.append(transaction)

    def add_utxos(self, transaction_outputs: list):
        '''Add unspent transactions to respective wallets.
        
        Arguments:
        
        * `transaction_outputs`: iterable of `TransactionOutput` objects.'''

        for to in transaction_outputs:
            self.ring[self.pubk2ind(to.receiver_public_key)].add_utxo(to)

    def send_dict_to_address(self, request_params):
        '''Send specified dict to an address.

        Arguments:

        * `request_params`: `tuple` of `dict` and `str` URL.

        Returns:

        * `True` is response status code is 200, else `False`.'''

        dict_to_broadcast, url = request_params
        http = urllib3.PoolManager()
        response = http.request('POST', url,
                                headers={'Content-Type': 'application/json'},
                                body=dict_to_broadcast)

        return (response.status == 200)

    def broadcast_transaction(self, transaction: Transaction):
        '''Broadcast transaction to everyone (but self).

        Arguments:

        `transaction`: `Transaction` to be broadcasted.

        Returns:

        * `True` is send successfully to every node.'''

        broadcast_message = transaction.to_dict()
        pool = ThreadPool(NUM_OF_THREADS)
        request_params_list = [
            (broadcast_message, f'{self.ring[receiver_idx].address}/transaction') \
                for receiver_idx in self.ring if receiver_idx != self.my_id
        ]
        results = pool.map(self.send_dict_to_address, request_params_list)
        pool.close()
        pool.join()

        return all(results)

    def validate_transaction(self, transaction: Transaction):
        '''Validate received transaction.
        
        Arguments:
        
        `transaction`: [Reconstructed from `dict`] `Transaction`.
        
        Returns:
        
        `True` if valid.'''

        # signature
        if not PKCS1_v1_5.new(transaction.sender_pubk)\
            .verify(transaction.make_hash(is_str=False), transaction.signature):
            return False

        # double spending
        if len(set(transaction.transaction_inputs)) < len(transaction.transaction_inputs):
            return False

        # check ids are the same, note that utxos can be 1 or 2
        if not all([utxo.transaction_id == transaction.transaction_id \
            for utxo in transaction.transaction_outputs]):
            return False

        # check if transaction inputs exist
        amount = sum([utxo.amount for utxo in transaction.transaction_outputs])
        return self.ring[self.pubk2ind[transaction.sender_pubk]]\
            .check_and_remove_utxo(transaction.transaction_inputs, amount)


    def create_new_block(self):
        self.pending_block = Block(self.chain)
        while not self.transaction_queue.empty():
            self.add_transaction_to_block(self.transaction_queue.get_nowait())


    @wrapt.synchronized
    def add_transaction_to_block(self, transaction: Transaction):
        # If enough transactions mine
        if self.pending_block.add_transaction(transaction) == self.capacity:
            self.mine_block()


    def mine_block(self):
        while True:
            self.pending_block.nonce = np.random.randint(2 ** 32)
            if int(self.pending_block.my_hash, 16) < 2 ** (32 - self.difficulty):
                break
        self.chain.append(self.pending_block)
        self.broadcast_block()
        self.create_new_block()

    def broadcast_block(self):
        broadcast_message = self.pending_block.to_dict()
        pool = ThreadPool(NUM_OF_THREADS)
        request_params_list = [(broadcast_message, f'{self.ring[receiver_idx].address}/block') for receiver_idx in self.ring]
        results = pool.map(self.send_dict_to_address, request_params_list)
        pool.close()
        pool.join()
        return all(results)

    def valid_proof(self, difficulty):
        pass
    
    #concencus functions

    def valid_chain(self, chain):
        #check for the longer chain across all nodes
        pass


    def resolve_conflicts(self):
        #resolve correct chain
        pass
