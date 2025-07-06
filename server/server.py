import socket
import selectors
import sys
import os
import json


def response_header(status, status_code, content_type=None, content_length=0):
    response_headers = [
        f"HTTP/1.1 {status_code} {status}\r\n".encode('utf-8'),
        f"Content-Type: {content_type}; charset=utf-8\r\n".encode('utf-8') if content_type else b'',
        f"Content-Length: {content_length}\r\n".encode('utf-8') if content_type else b'',
        b"Connection: close\r\n",
        b"\r\n"
    ]

    return b''.join(response_headers)


def valid_file_name(name):
    if name.count('.')!=1:
        return False
    elif name.split('.')[0].strip()=='':
        return False
    elif name.split('.')[1].strip()=='':
        return False

    return True


def process_get_request(key):
    request_file = key.data['request_line'].split(' ')[1]
    json_data = None

    try:
        if request_file=='/':
            with open(f'./frontend_files/index.html', 'rb') as file:
                file_data = file.read()
        elif '?' in request_file:
            param_list = request_file.split('?')[1].split('&')
            
            if 'file-list=true' in param_list:
                os.makedirs('./media', exist_ok=True)

                media_file_list = [file for file in os.listdir('./media') if os.path.isfile(os.path.join('./media', file))]
                media_file_list.sort()
                json_data = json.dumps({'media_file_list': media_file_list}).encode('utf-8')
            else:
                with open(f'./frontend_files/index.html', 'rb') as file:
                    file_data = file.read()
        else:
            with open(f'./frontend_files{request_file}', 'rb') as file:
                file_data = file.read()
    except:
        return response_header(status='Not Found', status_code='404', content_type=None, content_length=0)
    
    if json_data:
        response = response_header(status='OK', status_code='200', content_type='application/json', content_length=len(json_data))

        response += json_data
    else:
        response = response_header(status='OK', status_code='200', content_type='text/html', content_length=len(file_data))

        response += file_data
    
    return response

def process_post_request(key):
    # File upload requests without any files will still have some data like boundary, content-disposition
    if key.data['content_length']>188:
        data = key.data['input_buffer']
        data_list = data.split(b'\r\n\r\n')
        content_disposition = data_list[0].split(b'\r\n')[1]
        content_disposition_list = content_disposition.split(b'"')
        data_list = data_list[1].split(('\r\n--'+key.data['boundary']+'--\r\n').encode('utf-8'))

        file_name = content_disposition_list[len(content_disposition_list)-2].decode('utf-8')
        file_data = data_list[0]

        if not file_data:
            return response_header(status='Bad Request', status_code=400)
        
        os.makedirs('./media', exist_ok=True)

        with open(f'./media/{file_name}', 'wb') as f:
            f.write(file_data)

        status_code = 201
        response = response_header(status='Created', status_code=201)
    else:
        response = response_header(status='Bad Request', status_code=400)

    return response


def process_put_request(key):
    if key.data['content_length']>0:
        data = json.loads(key.data['input_buffer'].decode('utf-8'))
        if 'old_name' not in data or 'new_name' not in data:
            return response_header(status='Bad Request', status_code=400)

        if data['old_name'].count('.')!=1 or data['new_name'].count('.')!=1:
            return response_header(status='Bad Request', status_code=400)

        if valid_file_name(data['old_name']) is False or valid_file_name(data['new_name']) is False:
            return response_header(status='Bad Request', status_code=400)

        media_file_list = [file for file in os.listdir('./media') if os.path.isfile(os.path.join('./media', file))]
        
        if data['old_name'] not in media_file_list:
            return response_header(status='Not Found', status_code=404)

        os.rename(f"./media/{data['old_name']}", f"./media/{data['new_name']}")

        response = response_header(status='OK', status_code=200)
    else:
        response = response_header(status='Bad Request', status_code=400)

    return response


def process_delete_request(key):
    status_code = 200
    
    if key.data['content_length']>0:
        data = json.loads(key.data['input_buffer'].decode('utf-8'))
        if 'file_name' not in data:
            return response_header(status='Bad Request', status_code=400)

        if data['file_name'].count('.')!=1:
            return response_header(status='Bad Request', status_code=400)

        if valid_file_name(data['file_name']) is False:
            return response_header(status='Bad Request', status_code=400)

        media_file_list = [file for file in os.listdir('./media') if os.path.isfile(os.path.join('./media', file))]
        
        if data['file_name'] not in media_file_list:
            return response_header(status='Not Found', status_code=404)

        os.remove(f"./media/{data['file_name']}")

        response = response_header(status='OK', status_code=status_code)
    else:
        response = response_header(status='Bad Request', status_code=400)

    return response


def get_request_type(request_line):
    if 'GET' in request_line:
        return 'GET'
    elif 'POST' in request_line:
        return 'POST'
    elif 'PUT' in request_line:
        return 'PUT'
    elif 'DELETE' in request_line:
        return 'DELETE'
    else:
        return None

def process_request(key, mask, s):
    sock = key.fileobj

    if mask & selectors.EVENT_READ:
        try:
            request_data = sock.recv(102400)
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

            request_type = get_request_type(request_line)
            key.data['request_type'] = request_type
            if request_type in ['POST', 'PUT', 'DELETE']:
                for header in headers_list:
                    if b'Content-Length' in header:
                        key.data['content_length'] = int(header.split(b' ')[1].decode('utf-8'))
                    if request_type=='POST' and b'Content-Type' in header:
                        key.data['boundary'] = header.split(b'boundary=')[1].decode('utf-8')
                
                if key.data['content_length']==0:
                    s.unregister(sock)
                    sock.close()
        
        if key.data['headers_parsed'] is True and key.data['request_type']=='GET':
            key.data['output_buffer'] = process_get_request(key)
            s.modify(sock, selectors.EVENT_WRITE, data=key.data)

        if key.data['headers_parsed'] is True and key.data['request_type']=='POST':
            if len(key.data['input_buffer'])==key.data['content_length']:
                key.data['output_buffer'] = process_post_request(key)
                s.modify(sock, selectors.EVENT_WRITE, data=key.data)

        if key.data['headers_parsed'] is True and key.data['request_type']=='PUT':
            if len(key.data['input_buffer'])==key.data['content_length']:
                key.data['output_buffer'] = process_put_request(key)
                s.modify(sock, selectors.EVENT_WRITE, data=key.data)

        if key.data['headers_parsed'] is True and key.data['request_type']=='DELETE':
            if len(key.data['input_buffer'])==key.data['content_length']:
                key.data['output_buffer'] = process_delete_request(key)
                s.modify(sock, selectors.EVENT_WRITE, data=key.data)

    elif mask & selectors.EVENT_WRITE:
        if key.data['request_type'] in ['GET', 'POST', 'PUT', 'DELETE']:
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
        'request_type': '',
        'boundary': ''
    }

    # Do not put (selectors.EVENT_READ | selectors.EVENT_WRITE) here as the socket will be always 
    # ready to write. So a write event may be triggered even when input buffer is empty.
    # We will modify the socket to selectors.EVENT_READ when we are sure that there is something to write.
    events_mask = selectors.EVENT_READ

    s.register(conn, events_mask, data=data)


def event_loop(s, HOST, PORT):
    print(f'Started server. Address: {HOST}:{PORT}')
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
    PORT = 8000

    s = selectors.DefaultSelector()

    listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listening_socket.bind((HOST, PORT))
    listening_socket.listen()
    listening_socket.setblocking(False)

    s.register(listening_socket, selectors.EVENT_READ, data=None) 

    try:
        event_loop(s, HOST, PORT)
        s.unregister(listening_socket)
        listening_socket.close()
    except:
        s.unregister(listening_socket)
        listening_socket.close()


if __name__ == '__main__':
    main()


