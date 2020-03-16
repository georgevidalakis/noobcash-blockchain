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


class Transaction:

    def __init__(self, recipient_address, value : int, my_wallet):
        if my_wallet is None:
            self.sender_address = 0
            #self.transaction_inputs: λίστα από Transaction Input
            self.transaction_inputs, change = [], 0
        else:
            #self.sender_address: To public key του wallet από το οποίο προέρχονται τα χρήματα
            self.sender_address = my_wallet.public_key
            #self.transaction_inputs: λίστα από Transaction Input
            self.transaction_inputs, change = my_wallet.get_sufficient_utxos(value)

        #self.receiver_address: To public key του wallet στο οποίο θα καταλήξουν τα χρήματα
        self.receiver_address = recipient_address

        #self.amount: το ποσό που θα μεταφερθεί
        self.amount = value

        #self.transaction_id: το hash του transaction
        self.transaction_id = SHA.new(data=self.message().encode('utf-8'))

        #self.transaction_outputs: λίστα από Transaction Output
        self.transaction_outputs = [TransactionOutput(self.transaction_id, self.receiver_address, value)]
        if change > 0:
            self.transaction_outputs.append(TransactionOutput(self.transaction_id, self.sender_address, change))

        #self.Signature
        self.Signature = self.sign_transaction(my_wallet.private_key)
    
    '''@classmethod
    def from_dict(cls, transaction : dict):
        transaction['sender_address'] = RSA.construct((transaction['sender_address']['n'],
                                                       transaction['sender_address']['e']))

        transaction['receiver_address'] = RSA.construct((transaction['receiver_address']['n'],
                                                         transaction['receiver_address']['e']))

        transaction['transaction_outputs'] = [
            TransactionOutput.from_dict(transaction_output) \
                for transaction_output in transaction['transaction_outputs']
        ]

        self.__dict__.update(transaction)'''
    
    def message(self):
        return json.dumps({
            'sender_address': self.sender_address,
            'receiver_address': self.receiver_address,
            'amount': self.amount,
            'transaction_inputs': self.transaction_inputs
        })

    def to_dict(self):
        return {
            'sender_address': self.sender_address,
            'receiver_address': self.receiver_address,
            'amount': self.amount,
            'transaction_inputs': self.transaction_inputs,
            'transaction_outputs': [transaction_output.to_dict() for transaction_output in self.transaction_outputs],
            'transaction_id': self.transaction_id.hexdigest(),
            'Signature': self.Signature.hex()
        }
    
    def sign_transaction(self, private_key):
        """
        Sign transaction with private key
        """
        return PKCS1_v1_5.new(private_key).sign(self.transaction_id)