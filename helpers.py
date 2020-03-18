from Crypto.PublicKey import RSA

def pubk_to_dict(pubk):
    return dict(n=pubk.n, e=pubk.e)

def pubk_from_dict(pubk_dict):
    return RSA.construct(pubk_dict['n'], pubk_dict['e'])

def sign_to_dict(signature):
    return signature.hex()

def sign_from_dict(signature_dict):
    return bytes.fromhex(signature_dict)