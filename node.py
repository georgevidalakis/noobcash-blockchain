from block import Block
from wallet import Wallet
from transaction import Transaction
from blockchain import Blockchain

import json
import urllib3
import jsonpickle

class Node:
	def __init__(self, is_bootstrap : bool, n : int, bootstrap_address : str):
		self.NBC = 0

		if is_bootstrap:
			self.my_id, self.chain = 0, self.init_bootstrap_blockchain(n)
		else:
			while True:
				self.my_id, self.chain = self.first_contact_data(bootstrap_address)
				if self.valid_chain(self.chain):
					break
			
		self.current_id_count = 0
		
		self.wallet = self.generate_wallet()

		self.ring = []  # Here we store information for every node, as its id, its address (ip:port) its public key and its balance 


	def init_bootstrap_blockchain(self, n):
		genesis_transaction = Transaction(self.wallet.public_key, 100 * n, None)
		return Blockchain(None, genesis_transaction)
	
	def first_contact_data(self, bootstrap_address):
		my_public_key = {
			'n': self.wallet.public_key.n,
			'e': self.wallet.public_key.e
		}
		http = urllib3.PoolManager()
		response = json.loads(http.request('POST', 'http://localhost:8080/assets',
							  			   headers={'Content-Type': 'application/json'},
							  			   body=my_public_key))
		blockchain = [Block.from_dict(block) for block in response['blockchain']]
		return response['id'], blockchain

	def create_new_block(self):
		pass

	def generate_wallet(self):
		#create a wallet for this node, with a public key and a private key
		return Wallet()

	def register_node_to_ring(self):
		# add this node to the ring, only the bootstrap node can add a node to the ring after checking his wallet and ip:port address
		# bootstrap node informs all other nodes and gives the request node an id and 100 NBCs
		pass


	def create_transaction(self, sender, receiver, signature):
		#remember to broadcast it
		pass


	def broadcast_transaction(self):
		pass

	def validate_transaction(self):
		#use of signature and NBCs balance
		pass
		

	def add_transaction_to_block(self):
		#if enough transactions  mine
		pass



	def mine_block(self):
		pass



	def broadcast_block(self):
		pass


		

	def valid_proof(self, difficulty=MINING_DIFFICULTY):
		pass
	
	#concencus functions

	def valid_chain(self, chain):
		#check for the longer chain across all nodes
		pass


	def resolve_conflicts(self):
		#resolve correct chain
		pass



