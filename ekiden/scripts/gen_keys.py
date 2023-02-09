from ekiden.keys import PrivateKey

private_key = PrivateKey()
print(f"private key {private_key.hex()}")
print(f"public key {private_key.public_key().hex()}")
