class TransactionOutput:
    def __init__(self, transaction_id, receiver_public_key, amount):
        self.transaction_id = transaction_id
        self.receiver_public_key = receiver_public_key
        self.amount = amount
    
    @classmethod
    def from_dict(self, transaction_output):
        transaction_output['receiver_public_key'] = RSA.construct((transaction['receiver_public_key']['n'],
                                                                   transaction['receiver_public_key']['e']))
        self.__dict__.update(transaction_output)

    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'receiver_public_key': self.receiver_public_key,
            'amount': self.amount
        }