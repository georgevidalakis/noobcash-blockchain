import binascii

import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

from requests import get



class wallet:

	def __init__(self):
		self.private_key = RSA.generate(2048)
		self.public_key = self.private_key.publickey()
		self.address = get('https://api.ipify.org').text
		self.transactions = []

	def balance(self):
		pass


my_wallet = wallet()
