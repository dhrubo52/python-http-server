import socket
import selectors
import sys


def create_get_response(key):
    request_file = key.data['request_line'].split(' ')[1]
    
    try:
        if request_file=='/':
            with open(f'./frontend_files/index.html', 'rb') as file:
                file_data = file.read()
        else:
            with open(f'./frontend_files{request_file}', 'rb') as file:
                file_data = file.read()
    except:
        response_headers = [
            b"HTTP/1.1 404 Not Found\r\n",
            b"Content-Type: text/plain; charset=utf-8\r\n",
            b"Content-Length: 0\r\n",
            b"Connection: close\r\n",
            b"\r\n"
        ]

        return b''.join(response_headers)


    response_headers = [
        b"HTTP/1.1 200 OK\r\n",
        b"Content-Type: text/html; charset=utf-8\r\n",
        f"Content-Length: {len(file_data)}\r\n".encode('utf-8'),
        b"Connection: close\r\n",
        b"\r\n"
    ]

    response = b''.join(response_headers)

    response += file_data

    return response

def create_post_response(key):
    data = b"You just made a POST request."

    response_headers = [
        b"HTTP/1.1 200 OK\r\n",
        b"Content-Type: text/plain; charset=utf-8\r\n",
        f"Content-Length: {len(data)}\r\n".encode('utf-8'),
        b"Connection: close\r\n",
        b"\r\n"
    ]

    response = b''.join(response_headers)

    response += data

    return response




def get_request_type(data):
    if 'GET' in data:
        return 'GET'
    elif 'POST' in data:
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
        
        # If we see atleast one b'\r\n\r\n' in the input buffer 
        # then it means we have atleast received the request line and headers
        if b'\r\n\r\n' in key.data['input_buffer'] and key.data['headers_parsed'] is False:
            input_buffer_list = key.data['input_buffer'].split(b'\r\n\r\n')
            request_line = input_buffer_list[0].split(b'\r\n')[0].decode('utf-8')
            headers_list = input_buffer_list[0].split(b'\r\n')[1:]

            # length of request line and headers
            request_and_headers_length = len(input_buffer_list[0]) + 4
            
            # Removed the bytes we processed from the input buffer
            key.data['input_buffer'] = key.data['input_buffer'][request_and_headers_length:]
            key.data['headers_parsed'] = True
            key.data['request_line'] = request_line
            print(request_line)

            request_type = get_request_type(request_line)
            key.data['request_type'] = request_type
            if request_type=='POST':
                for header in headers_list:
                    if b'Content-Length' in header:
                        key.data['content_length'] = int(header.split(b' ')[1].decode('utf-8'))

                if key.data['content_length']==0:
                    s.unregister(sock)
                    sock.close()
            

        
        if key.data['headers_parsed'] is True and key.data['request_type']=='GET':
            key.data['output_buffer'] = create_get_response(key)
            s.modify(sock, selectors.EVENT_WRITE, data=key.data)

        if key.data['headers_parsed'] is True and key.data['request_type']=='POST':
            if len(key.data['input_buffer'])==key.data['content_length']:
                key.data['output_buffer'] = create_post_response(key)
                s.modify(sock, selectors.EVENT_WRITE, data=key.data)

    elif mask & selectors.EVENT_WRITE:
        if key.data['request_type'] in ['GET', 'POST']:
            bytes_sent = sock.send(key.data['output_buffer'])
            if len(key.data['output_buffer'])==bytes_sent:
                key.data['output_buffer'] = b''
                s.unregister(sock)
                sock.close()
            else:
                key.data['output_buffer'] = key.data['output_buffer'][bytes_sent:]


def accept_connection(sock, s):
    conn, addr = sock.accept()

    conn.setblocking(False)
    data = {
        'addr': addr, 
        'input_buffer': b'', 
        'output_buffer': b'',
        'headers_parsed': False,
        'content_length': 0,
        'request_line': '',
        'request_type': ''
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
        s.unregister(listening_socket)
        listening_socket.close()
    except:
        s.unregister(listening_socket)
        listening_socket.close()


if __name__ == '__main__':
    main()


