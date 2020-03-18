from Crypto.PublicKey import RSA

def pubk_to_dict(pubk):
    '''Transform RSA public key to a dictionary
    so it can be recovered afterwards.

    Arguments:

    * `pubk`: RSA public key.

    Returns:

    * `dict` with keys ['n', 'e'].'''

    return dict(n=pubk.n, e=pubk.e)

def pubk_from_dict(pubk_dict):
    '''Retrieve RSA public key from `dict`
    containing `n` and `e`

    Arguments:

    * `pubk_dict`: `dict` containing keys ['n', 'e'].

    Returns:

    * RSA public key.'''

    return RSA.construct(pubk_dict['n'], pubk_dict['e'])

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