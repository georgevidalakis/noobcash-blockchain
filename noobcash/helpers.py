'''Auxiliary functions used throughout `noobcash`.'''

import json
import urllib3
from Crypto.PublicKey import RSA

from noobcash.blockchain import Blockchain
from noobcash.wallet import Wallet

def pubk_to_dict(pubk):
    '''Transform RSA public key to a dictionary
    so it can be recovered afterwards.

    Arguments:

    * `pubk`: RSA public key.

    Returns:

    * `dict` with keys ['n', 'e'].'''
    try:
        return dict(n=pubk.n, e=pubk.e)
    except AttributeError:
        # genesis wallet
        return pubk

def pubk_from_dict(pubk_dict):
    '''Retrieve RSA public key from `dict`
    containing `n` and `e`

    Arguments:

    * `pubk_dict`: `dict` containing keys ['n', 'e'].

    Returns:

    * RSA public key.'''

    try:
        return RSA.construct((pubk_dict['n'], pubk_dict['e']))
    except TypeError:
        return pubk_dict

def pubk_to_key(pubk):
    '''Get hashable info from RSA public key

    Arguments:

    * `pubk`: RSA public key.

    Returns:

    * `tuple` of (`n`, `e`).'''

    return (pubk.n, pubk.e)

def sign_to_dict(signature):
    '''Transform signature to recoverable form. Name is
    chosen for consistency with other objects.

    Arguments:

    * `signature`: signature as returned from `PKCS1_v5_1.new(*).sign()`.

    Returns:

    * Hexadecimal string.'''

    return signature.hex()

def sign_from_dict(signature_dict):
    '''Retrieve original form of signature.

    Arguments:

    * `signature_dict`: Hexadecimal string,
    name for consistency.

    Returns:

    * `bytes` signature.'''

    return bytes.fromhex(signature_dict)

def object_dict_deepcopy(dct):
    '''Deepcopy of whole `dict` with `Wallet`s,
    `TransactionOutput`s, etc.

    Returns:

    * Deepcopied `dict`.'''

    new_dct = {}
    for k in dct:
        new_dct[k] = dct[k].deepcopy()
    return new_dct


def get_len_from_address(url: str):
    '''Request `url` for length of its blockchain.

    Arguments:

    * `url`: `str` ip+port.

    Returns:

    * Blockchain length of node if valid, else 0.'''

    http = urllib3.PoolManager()
    response = http.request('GET', url, headers={'Accept': 'application/json'})

    if response.status != 200:
        return 0

    # response supposed to be a number
    blockchain_len = json.loads(response.data)

    if not isinstance(blockchain_len, int):
        return 0

    return blockchain_len

def first_contact_data(bootstrap_address: str, wallet: Wallet):
    '''Contact bootstrap to register into the network
    and handle the data in the response. MUST send wallet
    information and get index and current blockchain.

    Arguments:

    * `bootstrap_address`: ip+port of bootstrap (assumed
    to be known from the start).

    * `wallet`: the node's `Wallet` (not set yet into `ring`),

    Returns:

    * ([ascending] ID of node in the network, [not validated] bootstrap's blockchain).'''

    myinfo = wallet.to_dict()

    http = urllib3.PoolManager()

    # we are contacting the bootstrap
    # loop until we get proper chain
    response = json.loads(http.request('POST', f'{bootstrap_address}/node',
                                       headers={'Content-Type': 'application/json'},
                                       body=json.dumps(myinfo)).data)

    # blockchain in response is (ordered) list of blocks
    return response['id'], Blockchain.from_dict(response['blockchain'])

def send_dict_to_address(request_params):
    '''Send specified dict to an address.

    Arguments:

    * `request_params`: `tuple` of `dict` and `str` URL.

    Returns:

    * `True` is response status code is 200, else `False`.'''


    dict_to_broadcast, url = request_params
    http = urllib3.PoolManager()
    response = http.request('POST', url,
                            headers={'Content-Type': 'application/json'},
                            body=json.dumps(dict_to_broadcast))

    return response.status == 200

def generate_wallet(port: int):
    '''Generate node's wallet.

    Arguments:

    * `port`: integer port where node is listening.

    Returns:

    * `Wallet`.'''

    return Wallet(port=port, this_node=True)
