import socket
import selectors
import sys


def get_request_type(data):
    if b'GET' in data:
        return 'GET'
    elif b'POST' in data:
        return 'POST'
    else:
        return None

def process_request(key, mask, s):
    sock = key.fileobj
    
    if mask & selectors.EVENT_READ:
        try:
            request_data = sock.recv(1024)
        except:
            request_data = b''

        if request_data:
            key.data['input_buffer'] += request_data    
        
        if b'\r\n\r\n' in key.data['input_buffer'] and key.data['headers_parsed'] is False:
            input_buffer_list = key.data['input_buffer'].split(b'\r\n\r\n')
            request_line = input_buffer_list[0].split(b'\r\n')[0]
            headers_list = input_buffer_list[0].split(b'\r\n')[1:]
            request_and_headers_length = len(input_buffer_list[0]) + 4

            key.data['input_buffer'] = key.data['input_buffer'][request_and_headers_length:]
            key.data['headers_parsed'] = True
            key.data['request_line'] = request_line

            request_type = get_request_type(key.data['request_line'])

            if request_type == 'GET':
                response = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: text/plain\r\n"
                    b"Content-Length: 15\r\n"
                    b"Connection: close\r\n"
                    b"\r\n"
                    b"Hi from server!"
                )
                sock.send(response)
            
            s.unregister(sock)
            sock.close()
        # elif key.data['headers_parsed'] is True:
        #     # print('test')
        #     request_type = get_request_type(key.data['request_line'])
        #     if request_type == 'GET':
        #         key.data['output_buffer'] = b'Hi from server!'
        #         s.register(sock, selectors.EVENT_WRITE, data=key.data)
    else:
        sock.send(key.data['output_buffer'])
        s.unregister(sock)
        sock.close()



        
    
    # headers = request.split('\r\n\r\n')
    # headers = headers[0].split('\r\n')
    
    # if 'GET' in headers[0]:
    #     data['output_buffer']
    


def accept_connection(sock, s):
    conn, addr = sock.accept()

    conn.setblocking(False)
    data = {
        'addr': addr, 
        'input_buffer': b'', 
        'output_buffer': b'',
        'headers_parsed': False,
        'content_length': 0,
        'request_line': b''
    }
    events_mask = selectors.EVENT_READ | selectors.EVENT_WRITE

    s.register(conn, events_mask, data=data)


def event_loop(s):
    try:
        while True:
            events = s.select(timeout=None)
                
            for key, mask in events:
                if key.data is None:
                    accept_connection(key.fileobj, s)
                else:
                    process_request(key, mask, s)
    except Exception as e:
        print(str(e))


def main():
    HOST = '127.0.0.1'
    PORT = 7000

    s = selectors.DefaultSelector()

    try:
        if len(sys.argv) > 2:
            HOST = sys.argv[1]
            PORT = int(sys.argv[2])
    except:
        return 0

    listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listening_socket.bind((HOST, PORT))
    listening_socket.listen()
    listening_socket.setblocking(False)

    s.register(listening_socket, selectors.EVENT_READ, data=None) 

    try:
        event_loop(s)
    except:
        s.unregister(listening_socket)
        listening_socket.close()


if __name__ == '__main__':
    main()


