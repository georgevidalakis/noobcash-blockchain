from Crypto.PublicKey import RSA

class TransactionOutput:
    def __init__(self, transaction_id, receiver_public_key, amount):
        self.transaction_id = transaction_id
        self.receiver_public_key = receiver_public_key
        self.amount = amount
    
    @classmethod
    def from_dict(cls, transaction_output : TransactionOutput):
        transaction_output['receiver_public_key'] = RSA.construct((transaction_output['receiver_public_key']['n'],
                                                                   transaction_output['receiver_public_key']['e']))
        return cls(transaction_output['transaction_id'], transaction_output['receiver_public_key'],
                   transaction_output['amount'])

    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'receiver_public_key': self.receiver_public_key,
            'amount': self.amount
        }