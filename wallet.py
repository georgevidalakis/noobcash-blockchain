import binascii

import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

import hashlib
import json
from time import time
from uuid import uuid4

from requests import get
from transaction_output import TransactionOutput

class Wallet:
    '''Wallet of cryptocurrency of a node in a network.
    Contains `private_key` (RSA object) if wallet belongs to the node,
    `public_key` (RSA object) of the node, `address` (ip+port as string)
    of the node, `utxos` as a dict of its unspent transactions and `balance`
    the sum of its available money.'''

    def __init__(self, port, this_node=True):
        '''Initialize `Wallet` object.

        Arguments:

        * `port`: the port where the node is listening to.

        * `this_node`: flag, whether this objects refers to the
        information of this node.'''

        if this_node:
            self.private_key = RSA.generate(2048)
            self.public_key = self.private_key.publickey() # n, e
            # NOTE: added port into address
            self.address = f'{get("https://api.ipify.org").text}:{port}'
        self.utxos = dict() # key: transaction_id, value: utxo
        self.balance = 0 # Utxos and balance may be inconsistent (lock)

    @classmethod
    def from_dict(cls, wallet: dict): # NOTE: added extra constructor
        '''Constructor to be used when bootstrap node sends
        information about other nodes.

        Arguments:

        * `wallet`: `dict` directly from `to_dict()` send by bootstrap.'''

        inst = cls(port=0, this_node=False) # dummy port, wont be used
        inst.public_key = RSA.construct(wallet['public_key']['n'],
                                        wallet['public_key']['e'])
        inst.address = wallet['address']
        # NOTE: private key is not set
        return inst

    def to_dict(self): # NOTE: added to_dict for pubk and address
        '''Transform proper attributes to `dict` for
        bootstrap and node during first contact to send.

        Returns:

        * `dict` of proper attributes.'''

        return dict(
            public_key=dict(n=self.public_key.n,
                            e=self.public_key.e),
            address=self.address
        )

    def get_sufficient_utxos(self, amount: int):
        return self._get_necessary_utxos(amount)


    def add_utxo(self, utxo: TransactionOutput): # NOTE: transfered from NodeInfo
        '''Add an unspent transaction to be added to wallet.
        Balance is also updated.

        Arguments:

        * `utxo`: (hopefully) legit TransactionOutput.'''

        self.utxos[utxo.transaction_id] = utxo
        self.balance += utxo.amount

    def remove_utxo(self, utxo_id): # NOTE: transfered from NodeInfo
        '''Remove unspent transaction with transaction ID `utxo_id`
        from wallet. Balance is also updated.

        Arguments:

        * `utxo_id`: Transaction ID (SHA object) of
        unspent transaction to be removed.'''

        self.balance -= self.utxos[utxo_id]
        del self.utxo[utxo_id]

    def filtered_sum(self, utxo_ids): # NOTE: transfered from NodeInfo
        '''Compute sum of designated unspent transactions.

        Arguments:

        * `utxo_ids`: list of transaction IDs (SHA objects).

        Returns:

        * Sum of amounts in these unspent transactions.'''

        s = 0
        for tid in utxo_ids:
            s += self.utxos[tid].amount
        return s

    ##########################################################
    ############## different ways to pick utxos ##############
    ##########################################################

    def _get_necessary_utxos(self, amount: int):
        '''Get JUST ENOUGH unspent transactions from wallet to
        generate transaction. Balance is also updated.

        Arguments:

        * `amount`: amount transfered by the transaction.

        Returns:

        * (Transaction IDs (SHA objects) in a `list`, value of leftover NBCs [change]) if
        amount can be satisfied, else `None`.'''

        if amount > self.balance: # if not enough NBCs
            return None

        utxo_ids, s = [], 0
        for tid in self.utxos:
            # this way of iterating ensures that we get the lru utxos
            # even though we cannot pop
            # popitem() in while loop would get mru
            # pop() in for loop needs deepcopy
            utxo_ids.append(tid)
            s += self.utxos[tid].amount
            if s >= amount:
                break

        for tid in utxo_ids:
            # remove used utxos
            self.utxos.pop(tid)
        self.balance -= s

        return utxo_ids, s - amount

    def _get_all_utxos(self, amount: int):
        '''Get ALL unspent transactions from wallet to
        generate transaction. Balance is also updated.

        Arguments:

        * `amount`: amount transfered by the transaction.

        Returns:

        * (Transaction IDs (SHA object) in a `list`, value of leftover NBCs [change]) if
        amount can be satisfied, else `None`.'''

        change = self.balance - amount
        if change < 0: # if not enough NBCs
            return None

        utxo_ids = list(self.utxos) # get all keys

        self.balance = 0
        self.utxos = dict()

        return utxo_ids, change

    def _get_all_lru_utxos(self, amount: int):
        '''Get ALL BUT LAST (if possible) unspent transactions from wallet to
        generate transaction. Balance is also updated.

        Arguments:

        * `amount`: amount transfered by the transaction.

        Returns:

        * (Transaction IDs (SHA object) in a `list`, value of leftover NBCs [change]) if
        amount can be satisfied, else `None`.'''

        if amount > self.balance: # if not enough NBCs
            return None

        last_tid, last_utxo = self.utxos.popitem() # mru

        if amount > self.balance - last_utxo.amount:
            # if not enough NBCs without last utxo
            self.utxos[last_tid] = last_utxo # restore last entry
            return self._get_all_utxos(amount)

        utxo_ids, s = [], 0
        for tid in self.utxos:
            utxo_ids.append(tid)
            s += self.utxos[tid].amount

        self.balance -= s
        self.utxos = {last_tid: last_utxo} # keep only last entry

        return utxo_ids, s - amount


"""
RSA outputs for reference:

>>> pr = RSA.generate(2048)
>>> pu = pr.publickey()
>>> pu.n
536290887991748995089561472211460467762611...
>>> pu.e
65537
"""