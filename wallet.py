import binascii

import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

import hashlib
import json
from time import time
from urllib2.parse import urlparse
from uuid import uuid4

from requests import get

class Wallet:

	def __init__(self):
		self.private_key = RSA.generate(2048)
		self.public_key = self.private_key.publickey()
		self.address = get('https://api.ipify.org').text
		self.transactions = []
		self.balance = 0  # Transactions and balance may be inconsistent (lock)

	def get_sufficient_utxos(self, amount):
		if amount > self.balance:
			return None
		utxo_ids = []
		s = 0
		while amount > s:
			utxo = self.transactions.pop()
			utxo_ids.append(utxo.transaction_id)
			s += utxo.amount
		self.balance -= s
		return utxo_ids, s - amount
