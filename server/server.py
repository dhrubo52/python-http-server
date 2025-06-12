import socket
import selectors
import sys

def main():
    HOST = '127.0.0.1'
    PORT = 7000

    try:
        if len(sys.argv) > 2:
            HOST = sys.argv[1]
            PORT = int(sys.argv[2])
    except:
        return 0

    listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening_socket.bind((HOST, PORT))
    listening_socket.listen()
    

