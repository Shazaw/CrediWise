"""Generates a local-dev-only RSA keypair for RS256 JWT signing (PLAN §18.1).

Run once per developer machine and paste the printed lines into your local
`.env` — never into `.env.example` (PLAN §17.5 forbids committing secrets).

Usage: python scripts/generate_dev_jwt_keys.py
"""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    print("SECURITY_JWT_PRIVATE_KEY=" + private_pem.replace("\n", "\\n"))
    print("SECURITY_JWT_PUBLIC_KEY=" + public_pem.replace("\n", "\\n"))


if __name__ == "__main__":
    main()
