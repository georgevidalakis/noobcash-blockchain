from block import Block

class Blockchain:
    '''List of validated blocks with Proof-of-Work.
    Contains list of `Block` objects `chain`.'''


    def __init__(self, received_blockchain=None, genesis_transaction=None):
        '''Initialize `Blockchain` object.

        Arguments:

        * `received_blockchain`: `Blockchain` object received
        from another node (e.g. bootstrap). Default: `None` ->
        GENESIS block to be added.

        * `genesis_transaction`: Genesis `Transaction`. Is used
        when `received_blockchain` is not set, i.e. bootstrap
        initializes its blockchain. Default: `None`.'''

        if received_blockchain is None:
            assert(genesis_transaction is not None)
            self.chain = [Block(None, genesis_transaction)]
        else:
            self.chain = received_blockchain

    def to_dict(self):
        '''Transform attribute to `dict`
        as list of proper `Blocks`

        Returns:

        * `dict` of list of `dict` of `Blocks`.'''

        return dict(
            chain=[
                b.to_dict() for b in self.chain
            ]
        )

    @classmethod
    def from_dict(cls, blockchain: dict):
        '''Constructor to be used when receiving a blockchain
        from another node.
        
        Arguments:
        
        * `transaction`: `dict` directly from `to_dict()` send by another node.
        (NOTE: not validated yet).'''

        blockchain = [
            Block.from_dict(b) for b in blockchain['chain']
        ]
        return cls(received_blockchain=blockchain)
