import secp256k1


class PublicKey:
    def __init__(self, key_hex: str):
        self._public_key = secp256k1.PublicKey()
        self._public_key.deserialize(bytes.fromhex(key_hex))

    def verify(self, msg: bytes, signature: str) -> bool:
        return self._public_key.schnorr_verify(msg, bytes.fromhex(signature), None, raw=True)


class PrivateKey:
    def __init__(self):
        self._private_key = secp256k1.PrivateKey()

    def digest(self):
        """
        Returns the byte format of the private key
        """
        return self._private_key.private_key

    def hexdigest(self):
        """
        Returns the hex string format of the private key
        """
        return self._private_key.serialize()

    def sign(self, msg: bytes) -> str:
        return self._private_key.schnorr_sign(msg, None, raw=True).hex()

    def public_key_hexdigest(self) -> str:
        return self._private_key.pubkey.serialize().hex()

    def public_key(self) -> PublicKey:
        return PublicKey(key_hex=self.public_key_hexdigest())

    @classmethod
    def load(cls, hex_str: str):
        """
        Load the private key from a hex string of the private key
        """
        p = PrivateKey()
        p._private_key.deserialize(hex_str)
        return p


if __name__ == "__main__":
    key = PrivateKey()
    signature = key.sign(b"hello, world")

    pubkey = key.public_key()
    v = pubkey.verify(b"hello, world", signature)
    print(v)
