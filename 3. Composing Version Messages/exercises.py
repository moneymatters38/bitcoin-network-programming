import time
import socket
from random import randint
from hashlib import sha256

ZERO = b'\x00'
IPV4_PREFIX = b"\x00" * 10 + b"\x00" * 2
dummy_address = {
    "services": 0,
    "ip": '0.0.0.0',
    "port": 8333
}

def ip_to_bytes(ip):
    if ":" in ip:
        return socket.inet_pton(socket.AF_INET6, ip)
    else:
        return IPV4_PREFIX + socket.inet_pton(socket.AF_INET, ip)

def serialize_address(address, has_timestamp):
    result = b""
    if has_timestamp:
        result += int_to_little_endian(address['timestamp'], 4)
    result += int_to_little_endian(address['services'], 8)
    result += ip_to_bytes(address['ip'])
    result += int_to_big_endian(address['port'], 2)
    return result

def int_to_little_endian(integer, length):
    return integer.to_bytes(length, byteorder='little')

def int_to_big_endian(integer, length):
    return integer.to_bytes(length, byteorder='big')
    
def services_dict_to_int(services_dict):
    result = 0
    key_to_multiplier = {
        'NODE_NETWORK': 2**0,
        'NODE_GETUTXO': 2**1,
        'NODE_BLOOM': 2**2,
        'NODE_WITNESS': 2**3,
	'NODE_CASH': 2**4, 
        'NODE_NETWORK_LIMITED': 2**10,
    }
    for key, value in services_dict.items():
        result += key_to_multiplier[key] if value else 0
    return result


def bool_to_bytes(bool):
    return bytes([int(bool)])
    
def serialize_varint(i):
    if i < 253:
        return i.to_bytes(1, 'little')
    elif i < 256**2:
        return b'\xfd' + i.to_bytes(2, 'little')
    elif i < 256**4:
        return b'\xfe' + i.to_bytes(4, 'little')
    elif i < 256**8:
        return b'\xff' + i.to_bytes(8, 'little')
    else:
        raise RuntimeError('integer too large: {}'.format(i))
        
    
def serialize_varstr(bytes):
    return serialize_varint(len(bytes)) + bytes
    
def compute_checksum(bytes):
    return sha256(sha256(bytes).digest()).digest()[:4]
    
def serialize_version_payload(
        version=70015, services_dict={}, timestamp=None,
        receiver_address=dummy_address,
        sender_address=dummy_address,
        nonce=None, user_agent=b'/buidl-army/',
        start_height=0, relay=True):
    if timestamp is None:
        timestamp = int(time.time())
    if nonce is None:
        nonce = randint(0, 2**64)
    # message starts empty, we add to it for every field
    msg = b''
    # version
    msg += int_to_little_endian(version, 4)
    # services
    msg += int_to_little_endian(services_dict_to_int(services_dict), 8)
    # timestamp
    msg += int_to_little_endian(timestamp, 8)
    # receiver address
    msg += serialize_address(receiver_address, False)
    # sender address
    msg += serialize_address(sender_address, False)
    # nonce
    msg += int_to_little_endian(nonce, 8)
    # user agent
    msg += serialize_varstr(user_agent)
    # start height
    msg += int_to_little_endian(start_height, 4)
    # relay
    msg += bool_to_bytes(relay)
    return msg 

def serialize_message(command, payload):
    result = bytes.fromhex('F9 BE B4 D9')
    result += command + (12-len(command))*b'\x00'
    result += int_to_little_endian(len(payload), 4)
    result += compute_checksum(payload)
    result += payload
    return result

def handshake(address):
    sock = socket.create_connection(address, timeout=1)
    stream = sock.makefile("rb")

    # Step 1: our version message
    sock.sendall(serialize_message(command=b"version", payload=serialize_version_payload()))
    print("Sent version")

    # Step 2: their version message
    peer_version = read_message(stream) 
    print("Version: ")
    pprint(peer_version)

    # Step 3: their version message
    peer_verack = read_message(stream) 
    print("Verack: ", peer_verack)

    # Step 4: our verack
    sock.sendall(serialize_message(command=b"verack", payload=serialize_version_payload()))
    print("Sent verack")

    return sock, stream