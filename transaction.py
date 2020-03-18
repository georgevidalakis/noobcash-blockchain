import binascii

import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

import requests
from flask import Flask, jsonify, request, render_template

import json

from transaction_output import TransactionOutput
from helpers import pubk_from_dict, sign_from_dict, pubk_to_dict, sign_to_dict


class Transaction:
    '''Cryptocurrency transaction. Contains "unique" `transaction_id`
    (SHA object, needed in this format to sign transaction), sender 
    RSA public key `sender_pubk`, receiver RSA public key `receiver_pubk`,
    transaction IDs `transaction_inputs` where the money from `sender_pubk`
    supposedly come from, `signature` with private key of node for
    verification (in bytes)'''

    def __init__(self, recipient_pubk, value: int, my_wallet):
        '''Initialize `Transaction`object.

        Arguments:

        * `recipient_pubk`: RSA public key of recipient of NBCs.

        * `value`: amount of NBCs to be transfered.

        * `my_wallet`: `Wallet` of sender (MUST be this node's =>
        must contain its RSA private key). If `None`, then GENESIS
        transaction.'''

        self.receiver_pubk = recipient_pubk

        self.amount = value

        if my_wallet is None:
            # GENESIS
            self.sender_pubk = 0
            self.transaction_inputs, change = [], 0
            self.signature = b'No need'
        else:
            self.sender_pubk = my_wallet.public_key
            # list of hex_digests
            self.transaction_inputs, change = my_wallet.get_sufficient_utxos(value)
            self.signature = self.sign_transaction(my_wallet.private_key)

        self.transaction_id = SHA.new(data=self.message().encode('utf-8'))

        self.transaction_outputs = [
            TransactionOutput(self.transaction_id.hexdigest(),
                              self.receiver_address, value)
        ]
        if change > 0:
            self.transaction_outputs.append(
                TransactionOutput(self.transaction_id.hexdigest(),
                                  self.sender_address, change)
            )

    @classmethod
    def from_dict(cls, transaction: dict):
        '''Constructor to be used when receiving a transaction.

        Arguments:

        * `transaction`: `dict` directly from `to_dict()` send by other node.
        (NOTE: not validated yet).'''

        receiver_pubk = pubk_from_dict(transaction['receiver_pubk'])
        sender_pubk = pubk_from_dict(transaction['sender_pubk'])
        amount = int(transaction['amount'])
        transaction_inputs = transaction['transaction_inputs']
        transaction_outputs = [
            TransactionOutput.from_dict(to_dict) \
                for to_dict in transaction['transaction_outputs']
        ]
        signature = sign_from_dict(transaction['signature'])

        # use constructor if genesis transaction
        inst = cls(receiver_pubk, amount, my_wallet=None)
        inst.sender_pubk = sender_pubk
        inst.transaction_inputs = transaction_inputs
        # update id after new attributes
        inst.transaction_id = SHA.new(data=inst.message().encode('utf-8'))
        # assign correct transaction outputs
        inst.transaction_outputs = transaction_outputs
        inst.signature = signature

        return inst

    def message(self):
        '''"Arbitrary" choice of form of data to pass to hash function
        to produce `hash` of transaction, used for signatures.

        Returns:

        * `str` that somehow contains transaction's keys,
        value and input unspend transactions.'''

        return json.dumps(dict(
            sender_pubk=pubk_to_dict(self.sender_pubk),
            receiver_pubk=pubk_to_dict(self.receiver_pubk),
            amount=self.amount,
            transaction_inputs=self.transaction_inputs
        ))

    def to_dict(self):
        '''Transform attributes to `dict` for
        nodes to broadcast or send within block
        or with blockchain.

        Returns:

        * `dict` of ALL attributes but `transaction_id`
        (which is not useful since we would have to transmit its
        `hexdigest()`, which in turn cannot reconstruct the original
        attribute, while `message()` can).'''

        return dict(
            sender_pubk=pubk_to_dict(self.sender_pubk),
            receiver_pubk=pubk_to_dict(self.receiver_address),
            amount=self.amount,
            transaction_inputs=self.transaction_inputs,
            transaction_outputs=[
                to.to_dict() for to in self.transaction_outputs
            ],
            signature=sign_to_dict(self.signature)
        )

    def sign_transaction(self, private_key):
        '''Sign transaction with private key.

        Arguments:

        * `private_key`: RSA private key to sign transaction with.

        Returns:

        * `bytes` signature.'''

        return PKCS1_v1_5.new(private_key).sign(self.transaction_id)


'''
Signature manipulation for reference:

>>> pr = RSA.generate(2048)
>>> pu = pr.publickey()
>>> h = SHA.new(b'gc10')
>>> PKCS1_v1_5.new(pr).sign(h)
b'\x1a-\x1f\xfdv?#\x1e\x87!Y/\xee+\x18l\xbe\xd8E\x01\xc2\xc3W\xa8\xad\xa6...'
>>> signa = PKCS1_v1_5.new(pr).sign(h)
>>> PKCS1_v1_5.new(pu).verify(h, signa)
True
>>> PKCS1_v1_5.new(pu).verify(h, bytes.fromhex(signa.hex()))
True
>>> signa.hex()
'1a2d1ffd763f231e8721592fee2...'
'''