'''Queue to hold received or created transactions.
Has a single attribute, a list of `Trsansaction`s,
`queue`. Mainly used to make commands on `queue`
atomic with `syncronized`.'''

import wrapt

from noobcash.transaction import Transaction

@wrapt.synchronized
class TransactionQueue:
    '''Queue to hold received or created transactions.
    Has a single attribute, a list of `Trsansaction`s,
    `queue`. Mainly used to make commands on `queue`
    atomic with `syncronized`.'''

    def __init__(self, queue=list()):
        '''Initialize `TransactionQueue` object.

        Arguments:

        * `queue`: Initial `Transaction`s. Default: `[]`.'''

        assert hasattr(queue, '__len__')
        if not isinstance(queue, list):
            queue = list(queue)

        self.queue = queue

    def __str__(self):
        ''''''
        return str(self.queue)

    def __len__(self):
        '''Return number of transactions in queue.'''
        return len(self.queue)

    def append(self, transaction: Transaction, line: int):
        '''Append `transaction` to `queue`.

        Arguments:

        * `transaction`: `Trsansaction` to be appended.'''
        self.queue.append(transaction)
        print(f'\nAppend to queue in line #{line}\n')

        for other_tra in self.queue[:-1]:
            if other_tra.transaction_id == transaction.transaction_id:
                print(f'\nDuplicate transaction created in line #{line}.\n')
                print('\n'.join([str(tra) for tra in self.queue]))
                break

    def extend(self, transactions):
        '''Extend `queue` with `transactions`.

        Arguments:

        * `transactions`: `Trsansactions` to be appended.'''

        assert hasattr(transactions, '__len__')
        if not isinstance(transactions, list):
            transactions = list(transactions)

        self.queue.extend(transactions)

    def __getitem__(self, index):
        '''Method to access `queue` by indexing class.'''
        return self.queue[index]

    def split(self, index, assign=None):
        '''Split queue at `index`. Assign one of the splits
        to the queue is `assign` is set.

        Arguments:

        * `index`: index where `queue` should be split.

        * `assign`: If set, assigns the `assign`-th split to
        `queue`. Default: `None` (No assignment).

        Returns:

        * `tuple` of splits (`list`s).'''

        # chech if split possible ?
        ret = (self.queue[:index], self.queue[index:])

        if assign is not None:
            assert assign in (0, 1)
            self.queue = ret[assign]

        return ret


    def empty(self):
        '''Empty `queue`.'''
        self.queue = []

    def set(self, queue):
        '''Set `queue` to another queue without
        initializing a new object.'''

        assert hasattr(queue, '__len__')
        if not isinstance(queue, list):
            queue = list(queue)

        self.queue = queue

    def transactions(self):
        '''Get `Transaction`s in `list`, i.e. `queue`.'''
        return self.queue
