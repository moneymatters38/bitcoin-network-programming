from lib import handshake, read_msg

def listener(address):
    # Establish connection
    sock = handshake(address)
    stream = sock.makefile('rb')

    # Print every possible gossip message we receive
    while True:
        msg = read_msg(stream)
        command = msg['command']
        payload_len = len(msg['payload'])
        print('Received a "{command}" containing {payload_len} bytes')

if __name__ == 'main':
    listener(('204.236.245.12', '8333'))
