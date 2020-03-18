from helpers import pubk_from_dict, pubk_to_dict

class TransactionOutput:
    '''Transaction Output (utxo). Contains "unique" transaction ID
    (`hexdigest()`) `transaction_id`, RSA public key of the receiver
    `receiver_public_key` and amount `amount` she receives.'''

    def __init__(self, transaction_id, receiver_public_key, amount: int):
        '''Initialize `TransactionOutput` object.

        Arguments:

        * `transaction_id`: `hexdigest()` of transaction ID of transaction
        that created this object.

        * `receiver_public_key`: RSA public key of the node that will
        receiver this utxo.

        * `amount`: amount that this utxo contains.'''

        self.transaction_id = transaction_id
        self.receiver_public_key = receiver_public_key
        self.amount = amount

    @classmethod
    def from_dict(cls, transaction_output : TransactionOutput):
        '''Constructor to be used when receiving a transaction.
        
        Arguments:
        
        `transaction_output`: `dict` directly from `to_dict()` send
        by other node.'''

        transaction_output['receiver_pubk'] = pubk_from_dict(transaction_output['receiver_pubk'])
        return cls(transaction_output['transaction_id'], transaction_output['receiver_pubk'],
                   int(transaction_output['amount']))

    def to_dict(self):
        '''Transform attributes to `dict` for
        nodes to broadcast or send within block
        or with blockchain.

        Returns:

        * `dict` of ALL attributes.'''

        return dict(
            transaction_id=self.transaction_id,
            receiver_pubk=pubk_to_dict(self.receiver_public_key),
            amount=self.amount
        )
