# Please create conda kernel: conda create -n <name> python=3.9.0 first
import RDT
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send a message to server')
    # parser.add_argument('message', type=str, help='message to send')
    parser.add_argument('--port', type=int, default=2345, help='port to send message to')
    args = parser.parse_args()
    client = RDT.RDTSocket()
    client.bind(('127.0.0.1', args.port))
    client.listen(5)
    client.connect(('127.0.0.1', 2345))
