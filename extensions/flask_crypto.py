import json
import random
import time
from hashlib import md5
from cryptography.fernet import Fernet


def generate_key():
    try:
        key = Fernet.generate_key()
        with open("secret.key", "wb") as key_file:
            key_file.write(key)
    except Exception as e:
        raise e


def load_key():
    try:
        return open("secret.key", "rb").read()
    except Exception as e:
        raise e


def encrypt_message(message):
    try:
        key = load_key()
        encoded_message = message.encode()
        f = Fernet(key)
        encrypted_message = f.encrypt(encoded_message)
        return encrypted_message.decode()
    except Exception as e:
        raise e


def decrypt_message(encrypted_message):
    try:
        key = load_key()
        f = Fernet(key)
        decrypted_message = f.decrypt(encrypted_message)
        return decrypted_message.decode()
    except Exception as e:
        raise e


def encrypt_json(json_body):
    try:
        return encrypt_message(str(json_body))
    except Exception as e:
        raise e


def decrypt_json(encrypted_message):
    try:
        decrypted_message = decrypt_message(encrypted_message)
        decrypted_message = decrypted_message.replace("\'", "\"")
        decrypted_message = json.loads(str(decrypted_message))
        return decrypted_message
    except Exception as e:
        raise e
