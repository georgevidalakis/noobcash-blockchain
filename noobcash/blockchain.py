from noobcash.block import Block

from ordered_set import OrderedSet

class Blockchain:
    '''List of validated blocks with Proof-of-Work.
    Contains list of `Block` objects `chain`.'''


    def __init__(self, genesis_transaction=None):
        '''Initialize `Blockchain` object.

        Arguments:

        * `genesis_transaction`: Genesis `Transaction`. Is used
        when `received_blockchain` is not set, i.e. bootstrap
        initializes its blockchain. Default: `None`.'''

        self.chain = []
        self.hashes_set = set()

        if genesis_transaction is not None:
            self.append_block(Block(None, genesis_transaction))

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

        * `blockchain`: `dict` directly from `to_dict()` send by another node.
        (NOTE: not validated yet).'''

        inst = cls()
        
        for b in blockchain['chain']:
            inst.append_block(Block.from_dict(b))

        return inst

    def get_block_hash(self, i):
        return self.chain[i].hash

    def append_block(self, block: Block):
        self.chain.append(block)
        self.hashes_set.add(block.hash)

    def __len__(self):
        return len(self.chain)
    
    def set_of_transactions(self):
        ''''''

        transactions_set = OrderedSet()
        
        for b in self.chain:
            transactions_set.update(b.list_of_transactions)
        
        return transactions_set