'''Auxiliary functions used throughout `noobcash`.'''

from Crypto.PublicKey import RSA

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
    except AttributeError:
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

