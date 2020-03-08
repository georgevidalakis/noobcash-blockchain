class TransactionOutput:
    def __init__(self, transaction_id, receiver_public_key, amount):
        self.transaction_id = transaction_id
        self.receiver_public_key = receiver_public_key
        self.amount = amount
    
    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'receiver_public_key': self.receiver_public_key,
            'amount': self.amount
        }