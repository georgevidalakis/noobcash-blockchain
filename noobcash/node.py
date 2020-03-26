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
from noobcash.helpers import pubk_to_key, object_dict_deepcopy
from noobcash.transaction_queue import TransactionQueue

BLOCK_LOCK = threading.RLock()
TRANSACTION_LOCK = threading.RLock()

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

        * `n`: number of nodes in the network (considered known a priori).

        * `is_bootstrap`: if this node is the bootstrap.'''

        print('\nINIT\n')

        wallet = self.generate_wallet(port)

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
            self.ring = {
                self.my_id: wallet
            }
            self.ring_bak = object_dict_deepcopy(self.ring)
            # public key to index correspondence
            self.pubk2ind = {pubk_to_key(self.my_wallet().public_key): self.my_id}
            self.blockchain = self.init_bootstrap_blockchain()
        else:
            self.bootstrap_address = bootstrap_address
            self.my_id, self.blockchain = self.first_contact_data(self.bootstrap_address, wallet)
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

        print('\nINIT_BOOT_CHAIN\n')

        genesis_transaction = Transaction(recipient_pubk=self.my_wallet().public_key,
                                          value=100*self.nodes, my_wallet=None)
        self.add_utxos(genesis_transaction.transaction_outputs, self.ring)
        self.add_utxos(genesis_transaction.transaction_outputs, self.ring_bak)
        return Blockchain(genesis_transaction=genesis_transaction)

    def first_contact_data(self, bootstrap_address: str, wallet: Wallet):
        '''Contact bootstrap to register into the network
        and handle the data in the response. MUST send wallet
        information and get index and current blockchain.

        Arguments:

        * `bootstrap_address`: ip+port of bootstrap (assumed
        to be known from the start).

        * `wallet`: the node's `Wallet` (not set yet into `ring`),

        Returns:

        * ([ascending] ID of node in the network, [not validated] bootstrap's blockchain).'''

        print('\nFIRST_CONTACT\n')

        myinfo = wallet.to_dict()

        http = urllib3.PoolManager()

        # we are contacting the bootstrap
        # loop until we get proper chain
        response = json.loads(http.request('POST', f'{bootstrap_address}/node',
                                           headers={'Content-Type': 'application/json'},
                                           body=json.dumps(myinfo)).data)

        # blockchain in response is (ordered) list of blocks
        return response['id'], Blockchain.from_dict(response['blockchain'])

    def generate_wallet(self, port: int):
        '''Generate this node's wallet.

        Arguments:

        * `port`: integer port where node is listening.

        Returns:

        * This node's `Wallet`.'''

        return Wallet(port=port, this_node=True)

    def register_node_to_ring(self, wallet_dict: dict):
        '''Handle request to enter the network. The bootstrap node
        should register the node in `ring` and respond with index and
        current blockchain.

        Arguments:

        * `wallet_dict`: `dict` directly from `.to_dict()`.

        Returns:

        * `dict` with ['id', 'blockchain'].'''

        print('\nREGISTER\n')

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

    def broadcast_initial_transactions(self):
        '''Bootstrap sends 100 NBC coins to every node in the network.'''

        print('\nBROADCAST_INIT\n')

        for k in self.ring:
            if k != self.my_id:
                transaction = self.create_transaction(receiver_idx=k, amount=100)
                self.broadcast_transaction(transaction)

    def broadcast_wallets(self):
        '''As the bootstrap, broadcast the wallet of every node
        to all the nodes. All the nodes are sent to every node.

        Returns:

        * `True` if all nodes responded with a 200 code.'''


        print('\nBROADCAST WALLETS\n')

        broadcast_message = {
            k: self.ring[k].to_dict() for k in self.ring
        }

        pool = ThreadPool(self.nodes-1)
        request_params_list = [
            (broadcast_message, f'{self.ring[receiver_idx].address}/wallets') \
                for receiver_idx in self.ring if receiver_idx != self.my_id
        ]
        results = pool.map(self.send_dict_to_address, request_params_list)
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

        print('\nRECEIVE_WALLETS\n')

        self.ring = {
            int(idx): Wallet.from_dict(wallet_dict[idx]) \
                if int(idx) != self.my_id else self.my_wallet() \
                for idx in wallet_dict
        }
        self.pubk2ind = {
            pubk_to_key(self.ring[idx].public_key): idx for idx in self.ring
        }
        self.ring_bak = object_dict_deepcopy(self.ring)

        while not self.valid_chain(self.blockchain):
            self.my_id, self.blockchain = self.first_contact_data(self.bootstrap_address,
                                                                  self.my_wallet())

        # process transactions received before wallets
        self.process_transactions()

    def send_bogus_transaction(self, receiver_idx: int, amount: int):
        '''Create, broadcast bogus transaction.
        NOTE: sender is this node, transaction is not broadcasted
        for consistency with `create_transaction`.

        Arguments:

        * `receiver_idx`: receiver index in `ring` (chosen because
        of cli).

        * `amount`: (`int`) NBCs transfered.

        Returns:

        * Fake `Transaction`.'''

        print('\nBOGUS_TRANS_ENTRY\n')

        transaction = Transaction(recipient_pubk=self.ring[receiver_idx].public_key,
                                  value=amount, my_wallet=None)

        transaction.sender_pubk = self.my_wallet().public_key
        transaction.transaction_id = transaction.make_hash()
        transaction.signature = transaction.sign_transaction(self.my_wallet().private_key)

        return transaction

    @wrapt.synchronized(TRANSACTION_LOCK)
    def create_transaction(self, receiver_idx: int, amount: int):
        '''Create, broadcast transaction, update wallets and queue.
        NOTE: sender is this node.

        Arguments:

        * `receiver_idx`: receiver index in `ring` (chosen because
        of cli).

        * `amount`: (`int`) NBCs transfered.

        Returns:

        * `True` is transaction succesfully created, else `False`.'''

        print('\nCREATE_TRANSACTION_ENTRY\n')

        receiver_wallet = self.ring[receiver_idx]
        try:
            # here we also update our wallet
            transaction = Transaction(recipient_pubk=receiver_wallet.public_key,
                                      value=amount, my_wallet=self.my_wallet())
        except TypeError: # Reject transaction, not enough cash
            print('\nINVALID_TRANSACTION_CREATED_EXIT\n')
            return None

        # NOTE: broadcast transaction from API so not inside lock
        # self.broadcast_transaction(transaction)
        self.add_utxos(transaction.transaction_outputs, self.ring)
        self.transaction_queue.append(transaction)#, 303)

        if len(self.transaction_queue) >= self.capacity:
            self.mine_block()

        print('\nVALID_TRANSACTION_CREATED_EXIT\n')
        return transaction

    def add_utxos(self, transaction_outputs: list, ring: dict):
        '''Add unspent transactions to respective wallets.

        Arguments:

        * `transaction_outputs`: iterable of `TransactionOutput` objects.

        * `ring`: `Wallet` of nodes.'''

        print('\nADD_UTXOS_ENTRY\n')

        for tro in transaction_outputs:
            ring[self.pubk2ind[pubk_to_key(tro.receiver_public_key)]].add_utxo(tro)

    def send_dict_to_address(self, request_params):
        '''Send specified dict to an address.

        Arguments:

        * `request_params`: `tuple` of `dict` and `str` URL.

        Returns:

        * `True` is response status code is 200, else `False`.'''


        dict_to_broadcast, url = request_params
        print(f'\nSENDING_DICT_ENTRY (to {url})\n')
        http = urllib3.PoolManager()
        response = http.request('POST', url,
                                headers={'Content-Type': 'application/json'},
                                body=json.dumps(dict_to_broadcast))

        return response.status == 200

    def broadcast_transaction(self, transaction: Transaction):
        '''Broadcast transaction to everyone (but self).

        Arguments:

        `transaction`: `Transaction` to be broadcasted.

        Returns:

        * `True` is send successfully to every node.'''

        print('\nBROADCASTING_TRANSACTION_ENTRY\n')

        broadcast_message = transaction.to_dict()
        pool = ThreadPool(self.nodes-1)
        request_params_list = [
            (broadcast_message, f'{self.ring[receiver_idx].address}/transaction') \
                for receiver_idx in self.ring if receiver_idx != self.my_id
        ]
        results = pool.map(self.send_dict_to_address, request_params_list)
        pool.close()
        pool.join()

        return all(results)

    def validate_transaction(self, transaction: Transaction, ring: dict):
        '''Validate received transaction.

        Arguments:

        `transaction`: [Reconstructed from `dict`] `Transaction`.

        * `ring`: ring of `Wallet`s the validation is based upon.

        Returns:

        * `True` if valid.'''

        print('\nVALIDATE_TRANSACTION_ENTRY\n')

        # signature
        if not PKCS1_v1_5.new(transaction.sender_pubk).verify(transaction.make_hash(as_str=False),
                                                              transaction.signature):
            print('\nINVALID_TRANSACTION_EXIT\n')
            return False

        # double spending
        if len(set(transaction.transaction_inputs)) < len(transaction.transaction_inputs):
            print('\nINVALID_TRANSACTION_EXIT\n')
            return False

        # check ids are the same, note that utxos can be 1 or 2
        if not all([utxo.transaction_id == transaction.transaction_id \
            for utxo in transaction.transaction_outputs]):
            #print('\nINVALID_TRANSACTION_EXIT\n')
            return False

        # check if transaction inputs exist
        amount = 0
        for utxo in transaction.transaction_outputs:
            if utxo.amount < 0:
                print('\nINVALID_TRANSACTION_EXIT\n')
                return False
            amount += utxo.amount
        print(transaction)
        return ring[self.pubk2ind[pubk_to_key(transaction.sender_pubk)]]\
            .check_and_remove_utxos(transaction.transaction_inputs, amount)
        # res = ring[self.pubk2ind[pubk_to_key(transaction.sender_pubk)]]\
        #     .check_and_remove_utxos(transaction.transaction_inputs, amount)
        # if res:
        #     print('\nVALID_TRANSACTION_EXIT\n')
        # else:
        #     print('\nINVALID_TRANSACTION_EXIT\n')
        # return res

    def miner(self):
        '''Function that mines the first `capacity` transactions
        in the `transaction_queue`. Meant to operate as separate
        process. Sends the mined block through the API. Commits
        suicide so as not to continue the process.'''

        print('\nMINER_INIT\n')
        print(len(self.blockchain))
        print()
        block = Block(self.blockchain)

        block.add_transactions(self.transaction_queue[:self.capacity])
        block.mine(self.difficulty)

        self.send_dict_to_address((block.to_dict(),
                                   f'127.0.0.1:{self.my_wallet().address.split(":")[-1]}' + \
                                       '/mined_block'))

        print('\nMINER_EXIT\n')
        # su-su-suicide
        sys.exit(0)

    def mine_block(self):
        '''High-level function to call when being ready
        to mine.'''

        print('\nMINE_BLOCK_ENTRY\n')

        if self.miner_pid is not None:
            # miner is already mining
            print('\nNO_MINE_BLOCK_EXIT\n')

            return

        pid = os.fork()
        if pid == 0: # child
            self.miner()
        else: # father
            self.miner_pid = pid
        print('\nMINE_BLOCK_EXIT\n')


    @wrapt.synchronized(BLOCK_LOCK)
    def check_my_mined_block(self, block_dict: dict):
        '''Check block returned from miner and its coherence
        with the current blockchain. Append if everything
        is proper. Renew miner. NOTE: block is not broadcasted.

        Arguments:

        * `block_dict`: `dict` directly from `to_dict()`.

        Returns:

        * The mined block or `None` if not appended.'''
        print('\nCHECKMYMINEDBLOCK\n')

        block = Block.from_dict(block_dict)

        print(self.blockchain)
        print(block)

        if block.previous_hash == self.blockchain.get_block_hash(-1):
            print('\n\nMYBLOCKWINS\n\n')

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
            print('\n\nMYBLOCKLOST\n\n')
            # new blockchain/block received and miner was not killed in time
            # enable to recall, but transaction queue is new so dont meddle
            self.miner_pid = None
            block = None

        if len(self.transaction_queue) >= self.capacity:
            self.mine_block()

        print('\nCHECKMYMINEDBLOCK_EXIT')

        return block

    def broadcast_block(self, block: Block):
        '''Broadcast mined block to all nodes.

        Arguments:

        * `block`: `Block` with proof-of-work.'''

        print('\nBROADCAST_BLOCK_ENTRY\n')

        broadcast_message = block.to_dict()
        pool = ThreadPool(self.nodes-1)
        request_params_list = [
            (broadcast_message, f'{self.ring[receiver_idx].address}/block') \
                 for receiver_idx in self.ring if receiver_idx != self.my_id
        ]
        results = pool.map(self.send_dict_to_address, request_params_list)
        pool.close()
        pool.join()
        print('\nBROADCAST_BLOCK_EXIT\n')

        return all(results)

    def valid_proof(self, block: Block, ring: dict):
        '''Validate `block` and renew wallets of `ring` based
        on it. Revert `ring` if block is not valid.

        Arguments:

        * `block`: `Block` to be validated.

        * `ring`: ring of `Wallet`s.

        Return:

        * Whether `block` is valid.'''

        print('\nVALIDATE_PROOF_ENTRY\n')

        if not block.validate_hash(self.difficulty):
            print('\nVALIDATE_PROOF_HASH_EXIT\n')
            return False

        print('\nVALID HASH\n')
        ring_bak_bak = object_dict_deepcopy(ring)

        try:
            for tra in block.list_of_transactions:
                print(str(tra))
                if not self.validate_transaction(tra, ring):
                    raise ValueError
                self.add_utxos(tra.transaction_outputs, ring)
        except ValueError:
            print('FAILED_PROOF_TRAN_EXIT')
            for k in ring: # change values, not pointer
                ring[k] = ring_bak_bak[k]
            return False

        print('\nVALIDATE_PROOF_SUC_EXIT\n')
        return True

    def valid_chain(self, blockchain):
        '''Validate `blockchain` and renew both rings along
        with it.

        Arguments:

        * `blockchain`: `Blockchain` to be validated.

        Returns:

        * Whether `blockchain` is valid.'''

        print('\nVALIDATE_CHAIN_ENTRY\n')

        print(self.blockchain)
        print('\n\n')
        print(blockchain)
        print('\n\n')

        # check for the longer chain across all nodes
        new_ring = {k: Wallet.from_dict(self.ring[k].to_dict()) for k in self.ring}
        new_ring[self.my_id].private_key = self.my_wallet().private_key

        # add genesis transaction
        genesis_tra = blockchain.chain[0].list_of_transactions[0]
        self.add_utxos(genesis_tra.transaction_outputs, new_ring)

        for block in blockchain.chain[1:]:
            print('\nBLOCK\n')
            print(block)
            if not self.valid_proof(block, new_ring):
                print('\nVALIDATE_CHAIN_BLOCK_EXIT\n')
                return False

        self.ring = object_dict_deepcopy(new_ring)
        self.ring_bak = object_dict_deepcopy(new_ring)

        print('\nVALID_CHAIN__VALID_EXIT\n')
        return True

    def get_len_from_address(self, url: str):
        '''Request `url` for length of its blockchain.

        Arguments:

        * `url`: `str` ip+port.

        Returns:

        * Blockchain length of node if valid, else 0.'''

        print('\nGET_LEN\n')

        http = urllib3.PoolManager()
        response = http.request('GET', url, headers={'Accept': 'application/json'})

        if response.status != 200:
            return 0

        # response supposed to be a number
        blockchain_len = json.loads(response.data)

        if not isinstance(blockchain_len, int):
            return 0

        return blockchain_len

    def longest_blockchain_info(self):
        '''Get length and index of node with the longest blockchain.'''

        print('\nGET_LENSS\n')

        pool = ThreadPool(self.nodes-1)
        urls = [
            f'{self.ring[receiver_idx].address}/length' \
                for receiver_idx in self.ring if receiver_idx != self.my_id
        ]
        blockchain_lengths = pool.map(self.get_len_from_address, urls)
        pool.close()
        pool.join()

        # NOTE: Consider returning the whole list to be able to loop in case of lying

        node_with_longest_chain = np.argmax(blockchain_lengths)
        max_blockchain_len = blockchain_lengths[node_with_longest_chain]

        if node_with_longest_chain >= self.my_id:
            # renew index because ours is not included in the list returned
            node_with_longest_chain += 1

        return node_with_longest_chain, max_blockchain_len

    @wrapt.synchronized(TRANSACTION_LOCK)
    def receive_transaction(self, transaction: Union[dict, Transaction]):
        '''Validate `transaction`, update `ring` and add to queue. Call
        miner if necessary and possible.

        Arguments:

        `transaction`: `dict` directly from `to_dict()` or `Transaction`.'''

        print('\nRECEIVE_TRANSACTION_ENTRY\n')

        if isinstance(transaction, dict):
            transaction = Transaction.from_dict(transaction)

        # if ring is incomplete and not bootstrap
        # append to unprocessed
        if len(self.ring) < self.nodes and self.my_id != 0:
            print('\n\nUNPROCESSED_RECEIVE_TRA_EXIT\n\n')
            self.unprocessed_transaction_queue.append(transaction)#, 678)
            return

        if not self.validate_transaction(transaction, self.ring):
            print('\nINVALID_TRANSACTION_RECEIVE_EXIT\n')
            return
        self.add_utxos(transaction.transaction_outputs, self.ring)
        self.transaction_queue.append(transaction)#, 685)

        if len(self.transaction_queue) >= self.capacity:
            self.mine_block()

        print('\nRECEIVE_TRANSACTION_SUCCESS\n')

    @wrapt.synchronized(TRANSACTION_LOCK)
    def process_transactions(self):
        '''Process transaction in the `unprocessed_transaction_queue`.'''

        print('\nPROCESS_UNPROCESSED_ENTRY\n')

        for tra in self.unprocessed_transaction_queue:
            if not self.validate_transaction(tra, self.ring):
                print('\nPROCESS_UNPROCESSED_FAILE_EXIT\n')
                return
            self.add_utxos(tra.transaction_outputs, self.ring)
            self.transaction_queue.append(tra)#, 703)

        self.unprocessed_transaction_queue.empty()

        if len(self.transaction_queue) >= self.capacity:
            self.mine_block()

        print('\nPROCESS_UNPROCESSED_EXIT\n')

    def kill_miner(self):
        '''If miner is active, kill it (`SIGKILL`).'''

        if self.miner_pid is not None:
            print('Kill miner!')
            os.kill(self.miner_pid, signal.SIGKILL)
            self.miner_pid = None

    def resolve_conflicts(self):
        '''Try and get longest chain from the network. If
        new blockchain is indeed found, renew rings and keep
        transactions that'''

        print('\nRESOLVE_ENTRY\n')

        node_with_longest_chain, max_blockchain_len = self.longest_blockchain_info()

        if len(self.blockchain) >= max_blockchain_len:
            print('\nRESOLVE_NOT_LARGER_EXIT\n')
            return

        url = f'{self.ring[node_with_longest_chain].address}/blockchain'

        http = urllib3.PoolManager()
        response = http.request('GET', url, headers={'Accept': 'application/json'})

        blockchain = Blockchain.from_dict(json.loads(response.data))

        # renews both rings
        if not self.valid_chain(blockchain):
            print('\nRESOLVE_NOT_VALID_CHAIN_EXIT\n')
            return

        self.kill_miner()

        # keep transactions that have been sent to us
        # but do not exist in the received blockchain

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

        print('\nRESOLVE_SUCCESSFUL_EXIT\n')

    @wrapt.synchronized(BLOCK_LOCK)
    @wrapt.synchronized(TRANSACTION_LOCK)
    def receive_block(self, block_dict: dict):
        '''Check if block is redundant to handle, proper to append
        to the blockchain (and kill miner) or ask for new blockchain.

        Arguments:

        * `block_dict`: `dict` directly from `to_dict()`.'''

        print('\nRECEIVEDBLOCK_ENTRY\n')

        block = Block.from_dict(block_dict)
        # NOTE: check capacity?

        if block.previous_hash in self.blockchain.hashes_set and \
            block.previous_hash != self.blockchain.get_block_hash(-1):
            print('\nRECEIVEDBLOCK_EXISTS_EXIT\n')
            return

        if block.previous_hash != self.blockchain.get_block_hash(-1):
            self.resolve_conflicts()
            print('\nRECEIVEDBLOCK_RESOLVED_EXIT\n')
            return

        if self.valid_proof(block, self.ring_bak): # use bak to validate
            # if valid, ring_bak is updated
            print(f'Trying to kill miner {self.miner_pid}!')
            self.kill_miner()
            self.blockchain.append_block(block)

            # logic: removed transactions of block from queue
            # & update ring wrt transactions never seen before
            # without adding them to the queue, while preserving
            # their order with OrderedSet
            tra_queue_set = OrderedSet(self.transaction_queue.transactions())
            rec_tra_set = OrderedSet(block.list_of_transactions)

            self.transaction_queue.set(list(tra_queue_set - rec_tra_set))
            unknown_tra = list(rec_tra_set - tra_queue_set)
            for tra in unknown_tra:
                # add to ring but do not append to queue
                # they already in blockchain
                self.validate_transaction(tra, self.ring)
                self.add_utxos(tra.transaction_outputs, self.ring)

        print('\nRECEIVEDBLOCKFINALEXIT\n')
