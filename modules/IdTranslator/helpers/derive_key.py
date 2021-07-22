from hmac import HMAC
from base64 import b64decode, b64encode
from hashlib import sha256
from sys import argv


def compute_derived_symmetric_key(secret, reg_id):
    secret = b64decode(secret)
    return b64encode(
        HMAC(
            secret, msg=reg_id.encode("utf8"), digestmod=sha256
        ).digest()
    ).decode("utf-8")


print(compute_derived_symmetric_key(argv[1],argv[2]))