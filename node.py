from block import Block
from wallet import Wallet
from transaction import Transaction
from blockchain import Blockchain

class Node:
	def __init__(self, is_bootstrap, n):
		self.NBC = 0

		if is_bootstrap:
			my_id, self.chain = 0, self.init_bootstrap_blockchain(n)
		else:
			while True:
				my_id, self.chain = self.first_contact_data()
				if self.valid_chain(blockchain):
					break
			
		#self.current_id_count
		#self.NBCs
		#self.wallet

		#slef.ring[]   #here we store information for every node, as its id, its address (ip:port) its public key and its balance 


	def init_bootstrap_blockchain(self, n):
		genesis_transaction = Transaction(self.wallet.public_key, 100 * n, None)
		return Blockchain(None, genesis_transaction)
	
	def first_contact_data(self):
		pass

	def create_new_block():

	def create_wallet():
		#create a wallet for this node, with a public key and a private key

	def register_node_to_ring():
		#add this node to the ring, only the bootstrap node can add a node to the ring after checking his wallet and ip:port address
		#bottstrap node informs all other nodes and gives the request node an id and 100 NBCs


	def create_transaction(sender, receiver, signature):
		#remember to broadcast it


	def broadcast_transaction():

	def validate_transaction():
		#use of signature and NBCs balance
		

	def add_transaction_to_block():
		#if enough transactions  mine



	def mine_block():



	def broadcast_block():


		

	def valid_proof(.., difficulty=MINING_DIFFICULTY):




	#concencus functions

	def valid_chain(self, chain):
		#check for the longer chain across all nodes


	def resolve_conflicts(self):
		#resolve correct chain



