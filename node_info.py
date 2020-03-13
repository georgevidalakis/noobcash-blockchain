import transaction_output

class NodeInfo:

    def __init__(self, id, address, public_key):
        self.id = id
        self.address = address
        self.public_key = public_key
        self.utxo_dict = dict()
    
    def add_utxo(self, utxo):
        self.utxo_dict[utxo.transaction_id] = utxo
    
    def remove_utxo(self, utxo_id):
        del self.utxo_dict[utxo_id]
    
    def filtered_sum(self, utxo_ids):
        # return sum([self.utxo_dict[utxo_id].amount for utxo_id in utxo_ids])
        s = 0
        for utxo_id in utxo_ids:
            s += self.utxo_dict[utxo_id].amount
        return s