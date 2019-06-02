from lib import handshake, read_msg, serialize_msg, read_varint, read_address
from io import BytesIO

def read_addr_payload(stream):
    r = {}

    # read varint
    count = read_varint(stream)

    # read_address varint times. Return as list.
    r["addresses"] = [read_address(stream) for _ in range(count)]
    return r


def listener(addresses):
    while True:
        address = addresses.pop()
        # Establish connection
        print("Connecting to {}".format(address))
        sock = handshake(address)
        stream = sock.makefile('rb')

        # Request peer's peers
        sock.sendall(serialize_msg(b'getaddr'))

        # Print every possible gossip message we receive
        while True:
            msg = read_msg(stream)
            command = msg['command']
            payload_len = len(msg['payload'])
            print('Received a {} containing {} bytes'.format(command, payload_len))

            # respond to pong
            if command == b'ping':
                res = serialize_msg(command=b'pong', payload=msg['payload'])
                sock.sendall(res)
                print('Sent pong')

            # handle peer lists
            if command == b'addr':
                payload = read_addr_payload(BytesIO(msg['payload']))
                if len(payload) > 0:
                    addresses.extend([
                        (a['ip'], a['port']) for a in payload['addresses']
                        ])
                    break

if __name__ == '__main__':
    listener([('204.236.245.12', '8333')])
