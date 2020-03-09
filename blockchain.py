from block import Block

class Blockchain:

    def __init__(self, received_blockchain=None, genesis_transaction=None):
        if received_blockchain is None:
            assert(genesis_transaction is not None)
            self.chain = [Block(None, genesis_transaction)]
        else:
            assert(genesis_transaction is None)
            self.chain = received_blockchain
