from lib import handshake, read_msg, serialize_msg, read_varint, read_address, BitcoinProtocolError
from io import BytesIO
import time

class Node:

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    @property
    def address(self):
        return (self.ip, self.port)

class Connection:

    def __init__(self, node):
        self.node = node
        self.sock = None
        self.stream = None
        self.start = None

        # results
        self.peer_version_payload = None
        self.nodes_discovered = []

    def handle_ping(self, payload):
        res = serialize_msg(command=b'pong', payload=payload)
        self.sock.sendall(res)
        print('Sent pong')

    def handle_addr(self, payload):
        payload = read_addr_payload(BytesIO(payload))
        if len(payload['addresses']) > 1:
            self.nodes_discovered.extend([
                    Node(a['ip'], a['port']) for a in payload['addresses']
            ])

    def handle_msg(self):
        msg = read_msg(self.stream)
        command = msg['command'].decode()
        payload_len = len(msg['payload'])
        payload = msg['payload']
        print('Received a {} containing {} bytes'.format(command, payload_len))

        method_name = "handle_{}".format(command)

        if hasattr(self, method_name):
            getattr(self, method_name)(payload)

    def remain_alive(self):
        return not self.nodes_discovered

    def open(self):
        # set start time
        self.start = time.time()

        # open TCP connection
        print("Connecting to {}".format(self.node.ip))
        self.sock = handshake(self.node.address)
        self.stream = self.sock.makefile('rb')

        # Request peer's peers
        self.sock.sendall(serialize_msg(b'getaddr'))

        # Handle messages until program exits
        while self.remain_alive():
            self.handle_msg()

    def close(self):
        # clean up socket's file descriptor
        if self.sock:
            self.sock.close()

class Crawler:

    def __init__(self, nodes):
        self.nodes = nodes

    def crawl(self):
        while True:
            # Get next node and connect
            node = self.nodes.pop()
            try:
                conn = Connection(node)
                conn.open()
            except (OSError, BitcoinProtocolError) as e:
                print("Got error {}".format(str(e)))
                continue
            finally:
                conn.close()

            # Handle the results
            self.nodes.extend(conn.nodes_discovered)
            print("{} reports version {}".format(conn.node.ip, conn.peer_version_payload))

            pass

def read_addr_payload(stream):
    r = {}

    # read varint
    count = read_varint(stream)

    # read_address varint times. Return as list.
    r["addresses"] = [read_address(stream) for _ in range(count)]
    return r

if __name__ == '__main__':
    nodes = [Node('204.236.245.12', '8333')]
    Crawler(nodes).crawl()
