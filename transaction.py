from collections import OrderedDict

import binascii

import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

import requests
from flask import Flask, jsonify, request, render_template


class Transaction:

    def __init__(self, sender_address, sender_private_key, recipient_address, value):
        #self.sender_address: To public key του wallet από το οποίο προέρχονται τα χρήματα
        self.sender_address = sender_address

        #self.receiver_address: To public key του wallet στο οποίο θα καταλήξουν τα χρήματα
        self.receiver_address = recipient_address

        #self.amount: το ποσό που θα μεταφερθεί
        self.amount = value

        #self.transaction_id: το hash του transaction

        #self.transaction_inputs: λίστα από Transaction Input

        #self.transaction_outputs: λίστα από Transaction Output
        #selfSignature

    def to_dict(self):
        

    def sign_transaction(self):
        """
        Sign transaction with private key
        """
       