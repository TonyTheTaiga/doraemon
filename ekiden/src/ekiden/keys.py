import secrets

import secp256k1


class PublicKey:
    def __init__(self, key_hex: str):
        self._public_key = secp256k1.PublicKey(b"\x02" + bytes.fromhex(key_hex), True)

    def hex(self):
        """
        Returns the hex string format of the key
        """
        return self._public_key.serialize().hex()

    def verify(self, msg: bytes, signature: str) -> bool:
        return self._public_key.schnorr_verify(msg, bytes.fromhex(signature), None, raw=True)


class PrivateKey:
    def __init__(self):
        # Use the secrets module instead of the os.urandom which the secp256k1 library uses
        # secrets.token_bytes uses the systems random number generator which is less predicable than using os.urandom
        self._private_key = secp256k1.PrivateKey(secrets.token_bytes(32))

    def hex(self):
        """
        Returns the hex string format of the key
        """
        return self._private_key.serialize()

    def sign(self, msg: bytes) -> str:
        return self._private_key.schnorr_sign(msg, None, raw=True).hex()

    def public_key_hex(self) -> str:
        # Prefix with x02 for schnorr specs
        return self._private_key.pubkey.serialize()[1:].hex()

    def public_key(self) -> PublicKey:
        return PublicKey(key_hex=self.public_key_hex())

    @classmethod
    def load(cls, hex_str: str):
        """
        Load the key from hex digest
        """
        p = PrivateKey()
        p._private_key.deserialize(hex_str)
        return p


if __name__ == "__main__":
    key = PrivateKey()
    print(key.public_key_hex())
    signature = key.sign(b"hello, world")

    pubkey = key.public_key()
    v = pubkey.verify(b"hello, world", signature)
    print(v)
