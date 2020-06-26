import json
import random
import time
from hashlib import md5
from cryptography.fernet import Fernet

cur_time = int(time.time())
rnd_num = random.randint(100000, 999999)
token = str(cur_time) + ':' + str(rnd_num)
token = md5(token.encode(encoding='utf-8')).hexdigest()

data = {
  'username': 'flash_7',
  'email': 'tarangokhan77@gmail.com',
  'token': token
}

print(data)


def generate_key():
    """
    Generates a key and save it into a file
    """
    key = Fernet.generate_key()
    with open("secret.key", "wb") as key_file:
        key_file.write(key)


def load_key():
    """
    Load the previously generated key
    """
    return open("secret.key", "rb").read()


def encrypt_message(message):
    """
    Encrypts a message
    """
    key = load_key()
    encoded_message = message.encode()
    f = Fernet(key)
    encrypted_message = f.encrypt(encoded_message)

    print(encrypted_message)
    return encrypted_message


def decrypt_message(encrypted_message):
    """
    Decrypts an encrypted message
    """
    key = load_key()
    f = Fernet(key)
    decrypted_message = f.decrypt(encrypted_message)

    print(decrypted_message.decode())
    return decrypted_message.decode()


if __name__ == "__main__":
    generate_key()
    encrypted_message = encrypt_message(str(data))
    decrypted_message = decrypt_message(encrypted_message)
    decrypted_message = decrypted_message.replace("\'", "\"")
    print(type(decrypted_message))
    decrypted_message = json.loads(str(decrypted_message))
    print(type(decrypted_message))
    print('FINAL decrypted_message: ', decrypted_message)
    print(decrypted_message['username'])
