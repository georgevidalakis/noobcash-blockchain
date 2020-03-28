'''Cryptocurrency transaction handler of a node in the network.'''

import os
import sys
import signal
import json
from typing import Union
from multiprocessing.dummy import Pool as ThreadPool
import threading
import wrapt
import urllib3
import numpy as np
from Crypto.Signature import PKCS1_v1_5

from ordered_set import OrderedSet

from noobcash.block import Block
from noobcash.wallet import Wallet
from noobcash.transaction import Transaction
from noobcash.blockchain import Blockchain
from noobcash.helpers import (
    pubk_to_key, object_dict_deepcopy, get_len_from_address,
    first_contact_data, send_dict_to_address, generate_wallet
)
from noobcash.transaction_queue import TransactionQueue

BLOCK_LOCK = threading.RLock()
TRANSACTION_LOCK = threading.RLock()

NUM_OF_THREADS = 2

# @wrapt.synchronized
class Node:
    '''Cryptocurrency transaction handler of a node in the network.'''

    def __init__(self, bootstrap_address: str, capacity: int,
                 difficulty: int, port: int, nodes=0, is_bootstrap=False):
        '''Initialize `Node` object.

        Arguments:

        * `bootstrap_address`: ip+port of bootstrap (considered known a priori).

        * `capacity`: capacity of a block in blockchain.

        * `difficulty`: difficulty of mining a block.

        * `port`: port listening to.

        * `nodes`: number of nodes in the network (considered known a priori).

        * `is_bootstrap`: if this node is the bootstrap.'''

        wallet = generate_wallet(port)

        # validated transactions
        self.transaction_queue = TransactionQueue()
        # transactions not reflected in wallets of ring
        self.unprocessed_transaction_queue = TransactionQueue()

        self.miner_pid = None

        self.capacity = capacity

        self.difficulty = difficulty

        self.nodes = nodes


        if is_bootstrap:
            self.my_id = 0
            # information for every node (its address (ip:port),
            # its public key, its balance, its utxos)
            # should be modified with TRANSACTION_LOCK
            self.ring = {
                self.my_id: wallet
            }
            # backup containing info as it appears in the blockchain
            # Should be modified with BLOCK_LOCK
            self.ring_bak = object_dict_deepcopy(self.ring)
            # public key to index correspondence
            self.pubk2ind = {pubk_to_key(self.my_wallet().public_key): self.my_id}
            self.blockchain = self.init_bootstrap_blockchain()
        else:
            self.bootstrap_address = bootstrap_address
            self.my_id, self.blockchain = first_contact_data(self.bootstrap_address, wallet)
            # information for every node (its address (ip:port),
            # its public key, its balance, its utxos)
            self.ring = {
                self.my_id: wallet
            }
            # public key to index correspondence
            self.pubk2ind = {pubk_to_key(self.my_wallet().public_key): self.my_id}

    def my_wallet(self):
        '''Get node's `Wallet`

        Returns:

        * `Wallet` w/ private key.'''
        return self.ring[self.my_id]

    def init_bootstrap_blockchain(self):
        '''Initialize the blockchain of the bootstrap node.'''

        genesis_transaction = Transaction(recipient_pubk=self.my_wallet().public_key,
                                          value=100*self.nodes, my_wallet=None)
        self.add_utxos(genesis_transaction.transaction_outputs, self.ring)
        self.add_utxos(genesis_transaction.transaction_outputs, self.ring_bak)
        return Blockchain(genesis_transaction=genesis_transaction)

    def register_node_to_ring(self, wallet_dict: dict):
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
        index = self.pubk2ind.get(pubk_to_key(node_wallet.public_key), len(self.pubk2ind))
        self.pubk2ind[pubk_to_key(node_wallet.public_key)] = index
        self.ring[index] = node_wallet
        self.ring_bak[index] = node_wallet.deepcopy()

        info = dict(
            blockchain=self.blockchain.to_dict(),
            id=index
        )

        return info

    def create_initial_transactions(self):
        '''Bootstrap creates 100 NBC coin transactions to be sent
        to every node in the network. To be broadcasted from API.

        Returns:

        * `list` of `Transaction`s.'''

        transactions = []

        for k in self.ring:
            if k != self.my_id:
                transaction = self.create_transaction(receiver_idx=k, amount=100)
                transactions.append(transaction)

        return transactions

    def broadcast_wallets(self):
        '''As the bootstrap, broadcast the wallet of every node
        to all the nodes. All the nodes are sent to every node.

        Returns:

        * `True` if all nodes responded with a 200 code.'''

        broadcast_message = {
            k: self.ring[k].to_dict() for k in self.ring
        }

        pool = ThreadPool(NUM_OF_THREADS)
        request_params_list = [
            (broadcast_message, f'{self.ring[receiver_idx].address}/wallets') \
                for receiver_idx in self.ring if receiver_idx != self.my_id
        ]
        results = pool.map(send_dict_to_address, request_params_list)
        pool.close()
        pool.join()

        return all(results)

    def receive_wallets(self, wallet_dict: dict):
        '''Receive all wallets from the bootstrap and
        copy to ring and backup. Also, process all transactions
        received before receiving the wallets.

        Arguments:

        * `wallet_dict`: `dict` with indices as key values
        and `Wallet` `dicts` as values.'''

        self.ring = {
            int(idx): Wallet.from_dict(wallet_dict[idx]) \
                if int(idx) != self.my_id else self.my_wallet() \
                for idx in wallet_dict
        }
        self.pubk2ind = {
            pubk_to_key(self.ring[idx].public_key): idx for idx in self.ring
        }
        self.ring_bak = object_dict_deepcopy(self.ring)

        while self.valid_chain(self.blockchain) is None:
            self.my_id, self.blockchain = first_contact_data(self.bootstrap_address,
                                                             self.my_wallet())

        # process transactions received before wallets
        self.process_transactions()

    def send_bogus_transaction(self, receiver_idx: int, amount: int):
        '''Create bogus transaction. NOTE: sender is this node,
        transaction is not broadcasted for consistency with
        `create_transaction`.

        Arguments:

        * `receiver_idx`: receiver index in `ring` (chosen because
        of cli).

        * `amount`: (`int`) NBCs transfered.

        Returns:

        * Fake `Transaction`.'''

        transaction = Transaction(recipient_pubk=self.ring[receiver_idx].public_key,
                                  value=amount, my_wallet=None)

        transaction.sender_pubk = self.my_wallet().public_key
        transaction.transaction_id = transaction.make_hash()
        transaction.signature = transaction.sign_transaction(self.my_wallet().private_key)

        return transaction

    @wrapt.synchronized(TRANSACTION_LOCK)
    def create_transaction(self, receiver_idx: int, amount: int):
        '''Create transaction, update wallets and queue.
        NOTE: sender is this node, transaction is not broadcasted.

        Arguments:

        * `receiver_idx`: receiver index in `ring` (chosen because
        of cli).

        * `amount`: (`int`) NBCs transfered.

        Returns:

        * `Transaction` if succesfully created, else `None`.'''

        receiver_wallet = self.ring[receiver_idx]
        try:
            # here we also update our wallet
            transaction = Transaction(recipient_pubk=receiver_wallet.public_key,
                                      value=amount, my_wallet=self.my_wallet())
        except TypeError: # Reject transaction, not enough cash
            return None

        # NOTE: broadcast transaction from API so not inside lock
        # self.broadcast_transaction(transaction)
        self.add_utxos(transaction.transaction_outputs, self.ring)
        self.transaction_queue.append(transaction)

        if len(self.transaction_queue) >= self.capacity:
            self.mine_block()

        return transaction

    def add_utxos(self, transaction_outputs: list, ring: dict):
        '''Add unspent transactions to respective wallets.

        Arguments:

        * `transaction_outputs`: iterable of `TransactionOutput` objects.

        * `ring`: `Wallet` of nodes.'''

        for tro in transaction_outputs:
            ring[self.pubk2ind[pubk_to_key(tro.receiver_public_key)]].add_utxo(tro)

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
        results = pool.map(send_dict_to_address, request_params_list)
        pool.close()
        pool.join()

        return all(results)

    @wrapt.synchronized(TRANSACTION_LOCK)
    def receive_transaction(self, transaction: Union[dict, Transaction]):
        '''Validate `transaction`, update `ring` and add to queue. Call
        miner if necessary and possible.

        Arguments:

        `transaction`: `dict` directly from `to_dict()` or `Transaction`.'''

        if isinstance(transaction, dict):
            transaction = Transaction.from_dict(transaction)

        # if ring is incomplete and not bootstrap
        # append to unprocessed
        if len(self.ring) < self.nodes and self.my_id != 0:
            self.unprocessed_transaction_queue.append(transaction)
            return

        if not self.validate_transaction(transaction, self.ring):
            return

        self.add_utxos(transaction.transaction_outputs, self.ring)
        self.transaction_queue.append(transaction)

        if len(self.transaction_queue) >= self.capacity:
            self.mine_block()

    @wrapt.synchronized(TRANSACTION_LOCK)
    def process_transactions(self):
        '''Process transaction in the `unprocessed_transaction_queue`.'''

        for tra in self.unprocessed_transaction_queue:
            if not self.validate_transaction(tra, self.ring):
                continue
            self.add_utxos(tra.transaction_outputs, self.ring)
            self.transaction_queue.append(tra)

        self.unprocessed_transaction_queue.empty()

        if len(self.transaction_queue) >= self.capacity:
            self.mine_block()

    def validate_transaction(self, transaction: Transaction, ring: dict):
        '''Validate received transaction.

        Arguments:

        * `transaction`: [Reconstructed from `dict`] `Transaction`.

        * `ring`: ring of `Wallet`s the validation is based upon.

        Returns:

        * `True` if valid.'''

        # signature
        if not PKCS1_v1_5.new(transaction.sender_pubk).\
            verify(transaction.make_hash(as_str=False), transaction.signature):
            return False

        # double spending
        if len(set(transaction.transaction_inputs)) < len(transaction.transaction_inputs):
            return False

        # check ids are the same, note that utxos can be 1 or 2
        if not all([utxo.transaction_id == transaction.transaction_id \
            for utxo in transaction.transaction_outputs]):
            return False

        # check if transaction inputs exist
        amount = 0
        for utxo in transaction.transaction_outputs:
            if utxo.amount < 0:
                return False
            amount += utxo.amount

        return ring[self.pubk2ind[pubk_to_key(transaction.sender_pubk)]]\
            .check_and_remove_utxos(transaction.transaction_inputs, amount)

    def miner(self):
        '''Function that mines the first `capacity` transactions
        in the `transaction_queue`. Meant to operate as separate
        process. Sends the mined block through the API. Commits
        suicide so as not to continue the process.'''

        block = Block(self.blockchain)

        block.add_transactions(self.transaction_queue[:self.capacity])
        block.mine(self.difficulty)

        send_dict_to_address((block.to_dict(),
                              f'127.0.0.1:{self.my_wallet().address.split(":")[-1]}' + \
                                  '/mined_block'))

        # su-su-suicide
        sys.exit(0)

    def mine_block(self):
        '''High-level function to call when being ready
        to mine.'''

        if self.miner_pid is not None:
            # miner is already mining
            return

        try:
            pid = os.fork()
        except:
            return
        if pid == 0: # child
            self.miner()
        else: # father
            self.miner_pid = pid

    def kill_miner(self):
        '''If miner is active, kill it (`SIGKILL`).'''

        if self.miner_pid is not None:
            os.kill(self.miner_pid, signal.SIGKILL)
            self.miner_pid = None

    @wrapt.synchronized(BLOCK_LOCK)
    def check_my_mined_block(self, block_dict: dict):
        '''Check block returned from miner and its coherence
        with the current blockchain. Append if everything
        is proper. Renew miner. NOTE: block is not broadcasted.

        Arguments:

        * `block_dict`: `dict` directly from `to_dict()`.

        Returns:

        * The mined block or `None` if not appended.'''

        block = Block.from_dict(block_dict)

        if block.previous_hash == self.blockchain.get_block_hash(-1):

            block_transactions, _ = self.transaction_queue.split(self.capacity, assign=1)
            # allow miner to be recalled now that the transaction queue is up-to-date
            self.miner_pid = None

            for tra in block_transactions:
                self.add_utxos(tra.transaction_outputs, ring=self.ring_bak)
                self.ring_bak[self.pubk2ind[pubk_to_key(tra.sender_pubk)]]\
                    .remove_utxos(tra.transaction_inputs)

            # NOTE: broadcast block from API so not inside lock
            # self.broadcast_block(block)

            self.blockchain.append_block(block)

        else:
            # new blockchain/block received and miner was not killed in time
            # enable to recall, but transaction queue is new so dont meddle
            self.miner_pid = None
            block = None

        if len(self.transaction_queue) >= self.capacity:
            self.mine_block()

        return block

    def broadcast_block(self, block: Block):
        '''Broadcast mined block to all nodes.

        Arguments:

        * `block`: `Block` with proof-of-work.'''

        broadcast_message = block.to_dict()
        pool = ThreadPool(NUM_OF_THREADS)
        request_params_list = [
            (broadcast_message, f'{self.ring[receiver_idx].address}/block') \
                 for receiver_idx in self.ring if receiver_idx != self.my_id
        ]
        results = pool.map(send_dict_to_address, request_params_list)
        pool.close()
        pool.join()

        return all(results)

    def valid_proof(self, block: Block, ring: dict):
        '''Validate `block` and renew wallets of `ring` based
        on it. Revert `ring` if block is not valid.

        Arguments:

        * `block`: `Block` to be validated.

        * `ring`: ring of `Wallet`s.

        Return:

        * Whether `block` is valid.'''

        if not block.validate_hash(self.difficulty):
            return False

        ring_bak_bak = object_dict_deepcopy(ring)

        try:
            for tra in block.list_of_transactions:
                if not self.validate_transaction(tra, ring):
                    raise ValueError
                self.add_utxos(tra.transaction_outputs, ring)
        except ValueError:
            for k in ring: # change values, not pointer
                           # no deepcopy for efficiency
                ring[k] = ring_bak_bak[k]
            return False

        return True

    def valid_chain(self, blockchain):
        '''Validate `blockchain` and renew both rings along
        with it.

        Arguments:

        * `blockchain`: `Blockchain` to be validated.

        Returns:

        * Whether `blockchain` is valid.'''

        # check for the longer chain across all nodes
        new_ring = {k: Wallet.from_dict(self.ring[k].to_dict()) for k in self.ring}
        new_ring[self.my_id].private_key = self.my_wallet().private_key

        # add genesis transaction
        genesis_tra = blockchain.chain[0].list_of_transactions[0]
        self.add_utxos(genesis_tra.transaction_outputs, new_ring)

        for block in blockchain.chain[1:]:
            if not self.valid_proof(block, new_ring):
                return None

        return new_ring

    def longest_blockchain_info(self):
        '''Get length and index of node with the longest blockchain.'''

        pool = ThreadPool(NUM_OF_THREADS)
        urls = [
            f'{self.ring[receiver_idx].address}/length' \
                for receiver_idx in self.ring if receiver_idx != self.my_id
        ]
        blockchain_lengths = pool.map(get_len_from_address, urls)
        pool.close()
        pool.join()

        # NOTE: Consider returning the whole list to be able to loop in case of lying

        node_with_longest_chain = np.argmax(blockchain_lengths)
        max_blockchain_len = blockchain_lengths[node_with_longest_chain]

        if node_with_longest_chain >= self.my_id:
            # renew index because ours is not included in the list returned
            node_with_longest_chain += 1

        return node_with_longest_chain, max_blockchain_len

    def resolve_conflicts(self):
        '''Try and get longest chain from the network. If
        new blockchain is indeed found, renew rings and
        transaction queues.

        Returns:

        * `True` is new blockchain is embraced.'''

        node_with_longest_chain, max_blockchain_len = self.longest_blockchain_info()

        if len(self.blockchain) > max_blockchain_len:
            return False

        if len(self.blockchain) == max_blockchain_len and \
            self.my_id < node_with_longest_chain:
            return False

        url = f'{self.ring[node_with_longest_chain].address}/blockchain'

        http = urllib3.PoolManager()
        response = http.request('GET', url, headers={'Accept': 'application/json'})

        blockchain = Blockchain.from_dict(json.loads(response.data))

        # renews both rings
        new_ring = self.valid_chain(blockchain)
        if new_ring is None:
            return False

        # acquire TRANSACTION_LOCK
        self.accept_foreign_blockchain(new_ring, blockchain)

        return True

    @wrapt.synchronized(TRANSACTION_LOCK)
    @wrapt.synchronized(BLOCK_LOCK) # redundant as this function was specifically designed
                                    # to be used inside a BLOCK_LOCK to get TRANSACTION_LOCK
                                    # include for consistency
    def accept_foreign_blockchain(self, new_ring, blockchain):
        '''Wrapper around commands that require the TRANSACTION_LOCK
        when a new blockchain is accepted.

        Arguments:

        * `new_ring`: the state of the ring of the newly
        received `blockchain`.

        * `blockchain`: the newly received `Blockchain`.'''

        # keep transactions that have been sent to us
        # but do not exist in the received blockchain

        self.kill_miner()

        self.ring_bak = object_dict_deepcopy(new_ring)
        self.ring = object_dict_deepcopy(new_ring)

        transactions_dif = self.blockchain.set_of_transactions()\
            .union(OrderedSet(self.transaction_queue.transactions()))\
            .union(OrderedSet(self.unprocessed_transaction_queue.transactions())) - \
            blockchain.set_of_transactions()

        self.unprocessed_transaction_queue.set(list(transactions_dif))
        self.transaction_queue.empty()

        self.blockchain = blockchain

        # renew ring to be able to receive new transactions
        # based on the ones we have already received
        self.process_transactions()

    @wrapt.synchronized(BLOCK_LOCK)
    def receive_block(self, block_dict: dict):
        '''Check if block is redundant to handle, proper to append
        to the blockchain (and kill miner) or ask for new blockchain.

        Arguments:

        * `block_dict`: `dict` directly from `to_dict()`.

        Returns:

        * `True` if new block is accepted (even if it requires a new blockchain).'''

        block = Block.from_dict(block_dict)
        # NOTE: check capacity?

        if block.previous_hash in self.blockchain.hashes_set and \
            block.previous_hash != self.blockchain.get_block_hash(-1):
            return False

        if block.previous_hash != self.blockchain.get_block_hash(-1):
            return self.resolve_conflicts()

        if self.valid_proof(block, self.ring_bak): # use bak to validate
                                                   # if valid, ring_bak is updated
            # acquire TRANSACTION_LOCK
            self.accept_foreign_block(block)

            return True

        return False

    @wrapt.synchronized(TRANSACTION_LOCK)
    def accept_foreign_block(self, block):
        '''Wrapper around commands that require the TRANSACTION_LOCK
        when a new block is accepted (not a new blockchain).

        Arguments:

        * `block`: the newly accepted `Block`.'''

        # logic: removed transactions of block from queue
        # & update ring wrt transactions never seen before
        # without adding them to the queue, while preserving
        # their order with OrderedSet

        self.kill_miner()
        self.blockchain.append_block(block)
        tra_queue_set = OrderedSet(self.transaction_queue.transactions())
        rec_tra_set = OrderedSet(block.list_of_transactions)

        self.transaction_queue.set(list(tra_queue_set - rec_tra_set))
        unknown_tra = list(rec_tra_set - tra_queue_set)
        for tra in unknown_tra:
            # add to ring but do not append to queue
            # they already in blockchain
            self.validate_transaction(tra, self.ring)
            self.add_utxos(tra.transaction_outputs, self.ring)
