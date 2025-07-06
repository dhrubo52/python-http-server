# Python Http Server

A simple http server created using python for educational purposes. I created this server learn how http servers work. 

Created in the Ubuntu OS, this program utilizes the socket and selectors library to handle and process requests. I have not tried running this program on any other OS.

It can handle GET, POST, PUT and DELETE requests.

In this project:  
GET request is used to fetch html files and some JSON data.

POST request is used to upload files to the http server. Uploaded files will be stored in the "media" directory inside the "server" directory. If the "media" directory does not exist the program will automatically create one when a POST request is recieved.

PUT request is used to edit the uploaded files' name.

DELETE request is used to delete uploaded files.


The prgram can be run using the following python command,

python3 -m server.py

The above command will start the server on "127.0.0.1:8000" address.
