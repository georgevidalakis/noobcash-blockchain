from transaction import Transaction

import time
import json
from Crypto.Hash import SHA

class Block:
	def __init__(self, blockchain, genesis_transaction=None):
		if blockchain is None:
			assert(genesis_transaction is not None)
			self.index = 0
			self.previous_hash = 1
			self.nonce = 0
			self.list_of_transactions = [genesis_transaction]
			self.hash = '0'
		else:
			assert(genesis_transaction is None)
			self.index = len(blockchain.chain)
			self.previous_hash = blockchain.chain[-1].hash
			self.list_of_transactions = []

		self.timestamp = time.time()
	
	'''@classmethod
	def from_dict(self, block : dict):
		self.__dict__.update(block)'''
	
	def message(self):
		return json.dumps({
			'index': self.index,
			'previous_hash': self.previous_hash,
			'nonce': self.nonce,
			'list_of_transactions': [transaction.to_dict() for transaction in self.list_of_transactions]
		})
	
	def to_dict(self) -> dict:
		return {
			'index': self.index,
			'previous_hash': self.previous_hash,
			'nonce': self.nonce,
			'list_of_transactions': [transaction.to_dict() for transaction in self.list_of_transactions],
			'hash': self.hash
		}

	def my_hash(self) -> str:
		self.hash = SHA.new(data=self.message().encode('utf-8')).hexdigest()
		return self.hash

	def __len__(self):
		return len(self.list_of_transactions)

	def add_transaction(self, transaction : Transaction):
		# add a transaction to the block
		self.list_of_transactions.append(transaction)
		
		return len(self.list_of_transactions)