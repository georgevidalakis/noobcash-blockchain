from block import Block
from wallet import Wallet
from transaction import Transaction
from blockchain import Blockchain

import wrapt
import json
import queue
import urllib3
import jsonpickle
import numpy as np
from Crypto.Hash import SHA
from Crypto.Signature import PKCS1_v1_5
from multiprocessing.dummy import Pool as ThreadPool

class Node:
	def __init__(self, is_bootstrap : bool, n : int, bootstrap_address : str, capacity : int, difficulty : int):
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

		# TODO: self.ring should be a list with None in the position of the current node
		#       There should be one dict (public key -> node idx)
		self.ring = dict()  # Here we store information for every node, as its id, its address (ip:port) its public key and its balance

		self.transaction_queue = queue.Queue()

		self.capacity = capacity

		self.difficulty = difficulty

		self.pending_block = None


	def init_bootstrap_blockchain(self, n):
		genesis_transaction = Transaction(self.wallet.public_key, 100 * n, None)
		return Blockchain(None, genesis_transaction)
	
	def first_contact_data(self, bootstrap_address : str):
		my_public_key = {
			'n': self.wallet.public_key.n,
			'e': self.wallet.public_key.e
		}
		http = urllib3.PoolManager()
		response = json.loads(http.request('POST', f'{bootstrap_address}/node',
							  			   headers={'Content-Type': 'application/json'},
							  			   body=my_public_key))
		blockchain = [Block.from_dict(block) for block in response['blockchain']]
		return response['id'], blockchain

	def create_new_block(self):
		self.pending_block = Block(self.chain)
		while not self.transaction_queue.empty():
			self.add_transaction_to_block(self.transaction_queue.get_nowait())
				

	def generate_wallet(self):
		#create a wallet for this node, with a public key and a private key
		return Wallet()

	def register_node_to_ring(self):
		# add this node to the ring, only the bootstrap node can add a node to the ring after checking his wallet and ip:port address
		# bootstrap node informs all other nodes and gives the request node an id and 100 NBCs
		pass

	def create_transaction(self, receiver_idx : int, amount : int) -> bool:
		# remember to broadcast it
		receiver_node_info = self.ring[receiver_idx]
		try:
			transaction = Transaction(receiver_node_info.recipient_address, amount, self.wallet)
		except TypeError:
			# Reject transaction
			return False
		self.broadcast_transaction(transaction)
		self.add_utxos(transaction.transaction_outputs)
		if len(self.pending_block) == self.capacity:
			self.transaction_queue.put(transaction)
		else:
			self.add_transaction_to_block(transaction)
		return True

	def add_utxos(self, transaction_outputs: list):
		for transaction_output in transaction_outputs:
			if transaction_output.receiver_public_key == self.wallet.public_key:
				self.wallet.add_utxo(transaction_output)
			else:
				for receiver_idx in self.ring:
					if transaction_output.receiver_public_key == self.ring[receiver_idx].public_key:
						self.ring[receiver_idx].add_utxo(transaction_output)
						break

	def broadcast_dict_to_address(self, request_params) -> bool:
		dict_to_broadcast, url = request_params
		http = urllib3.PoolManager()
		response = http.request('POST', url,
								headers={'Content-Type': 'application/json'},
								body=dict_to_broadcast)
		return (response.status == 200)

	def broadcast_transaction(self, transaction : Transaction) -> bool:
		broadcast_message = transaction.to_dict()
		pool = ThreadPool(3)
		request_params_list = [(broadcast_message, f'{self.ring[receiver_idx].address}/transaction') for receiver_idx in self.ring]
		results = pool.map(self.broadcast_dict_to_address, request_params_list)
		pool.close()
		pool.join()
		return all(results)

	def validate_transaction(self, transaction : Transaction) -> bool:
		# use of signature and NBCs balance
		transaction_id = SHA.new(data=transaction.message().encode('utf-8'))
		if transaction_id.hexdigest() != transaction.transaction_id.hexdigest():
			return False
		if len(set(transaction.transaction_inputs)) < len(transaction.transaction_inputs):
			return False
		for node_info in self.ring:
			if node_info.public_key == transaction.sender_address:
				break
		amount = sum([utxo.amount for utxo in transaction.transaction_outputs])
		try:
			if node_info.filtered_sum(transaction.transaction_inputs) != amount or transaction.amount != amount:
				return False
		except KeyError:
			return False
		return bool(PKCS1_v1_5.new(transaction.sender_address).verify(transaction.transaction_id, transaction.Signature))
		
	@wrapt.synchronized
	def add_transaction_to_block(self, transaction : Transaction):
		# If enough transactions mine
		if self.pending_block.add_transaction(transaction) == self.capacity:
			self.mine_block()


	def mine_block(self):
		while True:
			self.pending_block.nonce = np.random.randint(2 ** 32)
			if int(self.pending_block.my_hash, 16) < 2 ** (32 - self.difficulty):
				break
		self.chain.append(self.pending_block)
		self.broadcast_block()
		self.create_new_block()

	def broadcast_block(self) -> bool:
		broadcast_message = self.pending_block.to_dict()
		pool = ThreadPool(3)
		request_params_list = [(broadcast_message, f'{self.ring[receiver_idx].address}/block') for receiver_idx in self.ring]
		results = pool.map(self.broadcast_dict_to_address, request_params_list)
		pool.close()
		pool.join()
		return all(results)

	def valid_proof(self, difficulty):
		pass
	
	#concencus functions

	def valid_chain(self, chain):
		#check for the longer chain across all nodes
		pass


	def resolve_conflicts(self):
		#resolve correct chain
		pass
