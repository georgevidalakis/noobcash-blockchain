'''Block of a blockchain. Contains integer `index`,
`previous_hash` of previous in the blockchain block and `hash` as strings,
integer `nonce` when it is mined, list `list_of_transactions` of "valid"
Transaction objects and `timestamp` of creation.'''

import time
import json
import numpy as np
from Crypto.Hash import SHA

from noobcash.transaction import Transaction

class Block:
    '''Block of a blockchain. Contains integer `index`,
    `previous_hash` of previous in the blockchain block and `hash` as strings,
    integer `nonce` when it is mined, list `list_of_transactions` of "valid"
    Transaction objects and `timestamp` of creation.'''

    def __init__(self, blockchain, genesis_transaction=None):
        '''Initialize `Block` object.

        Arguments:

        * `blockchain`: The blockchain we expect to extend with
        this block. Should be set to `None` if this is the
        genesis block.

        * `genesis_transaction`: the first, virtual transaction
        to construct the genesis block. Default: `None`.'''

        # NOTE: hashes are kept as (hex) strings since
        # their only purposes are comparison and mining

        self._hash_bits = SHA.digest_size * 8 # bytes -> bits
        if blockchain is None:
            # if blockchain is None => GENESIS block
            assert genesis_transaction is not None
            self.index = 0
            self.previous_hash = '1'
            self.nonce = 0
            self.list_of_transactions = [genesis_transaction]
            self.hash = '0'
        else:
            self.index = len(blockchain)
            self.previous_hash = blockchain.get_block_hash(-1)
            self.list_of_transactions = []

        self.timestamp = time.time()

    @classmethod
    def from_dict(cls, block: dict):
        '''Constructor to be used when a block is
        broadcasted of a blockchain is requested.

        Arguments:

        * `block`: `dict` directly from `to_dict()` send by other node
        (NOTE: assumes `nonce`, 'hash` are set, i.e. block has been mined).'''

        # use constructor of genesis block
        # with dummy genesis transaction
        inst = cls(None, 0)
        inst.index = block['index']
        inst.previous_hash = block['previous_hash']
        inst.hash = block['hash']
        inst.nonce = block['nonce']
        inst.list_of_transactions = [
            Transaction.from_dict(t) for t in block['list_of_transactions']
        ]
        inst.timestamp = block['timestamp']

        return inst

    def message(self):
        '''"Arbitrary" choice of form of data to pass to hash function
        to produce `hash` of block, used for mining and validating.

        Returns:

        * `str` that somehow contains block's transactions,
        previous_hash, nonce [and index].'''

        return json.dumps(dict(
            index=self.index,
            previous_hash=self.previous_hash,
            nonce=self.nonce,
            list_of_transactions=[
                t.to_dict() for t in self.list_of_transactions
            ]
        ))

    def to_dict(self):
        '''Transform attributes to `dict` for
        nodes to send as mined of as part of blockchain.

        Returns:

        * `dict` of ALL attributes.'''

        return dict(
            index=self.index,
            previous_hash=self.previous_hash,
            nonce=self.nonce,
            list_of_transactions=[
                t.to_dict() for t in self.list_of_transactions
            ],
            hash=self.hash,
            timestamp=self.timestamp
        )

    def my_hash(self):
        '''Produces `hash` of block. This functions does NOT secure
        a proper hash, it just produces it and stores it in the object.

        Returns:

        * Hexadecimal number in the form of a `str`
        of hashed `message()` of block.'''

        self.hash = SHA.new(data=self.message().encode('utf-8')).hexdigest()
        return self.hash

    def __len__(self):
        '''Length of block used for comparison
        with a capacity for transactions.

        Returns:

        * `int` number of transactions.'''

        return len(self.list_of_transactions)

    def add_transactions(self, transactions: list):
        '''Add VALIDATED transaction to block.

        Arguments:

        * `transaction`: validated `Transaction`.

        Returns:

        * `int` number of transactions after insertion to
        compare online with capacity.'''

        self.list_of_transactions.extend(transactions)

        return len(self.list_of_transactions)

    def mine(self, difficulty: int):
        '''Set `nonce` for Proof-of-work.

        Arguments:

        * `difficulty`: the difficulty of mining.'''

        while True:
            self.nonce = np.random.randint(2 ** 32)
            if self.validate_hash(difficulty):
                break

    def validate_hash(self, difficulty: int):
        '''Return whether nonce constitutes Proof-of-work.'''

        return int(self.my_hash(), 16) < 2 ** (self._hash_bits - difficulty)

    def __str__(self):
        '''Used for debugging, returns a `json.dumps`'d `dict`.'''

        result = dict(
            index=self.index,
            list_of_transactions=[
                json.loads(str(t)) for t in self.list_of_transactions
            ],
            timestamp=self.timestamp,
            hash=self.hash,
            prev=self.previous_hash
        )
        return json.dumps(result, indent=4)
