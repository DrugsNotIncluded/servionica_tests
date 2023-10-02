#!/bin/python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import threading


class Server1Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"message": "OK"}')


class Server2Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(300)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"message": "Redirect"}')


class Server3Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(400)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"message": "Bad Request"}')


def run_servers():
    server1 = HTTPServer(('localhost', 5000), Server1Handler)
    server2 = HTTPServer(('localhost', 5001), Server2Handler)
    server3 = HTTPServer(('localhost', 5002), Server3Handler)
    print('Web servers are running!')
    server1_thread = threading.Thread(target=server1.serve_forever)
    server2_thread = threading.Thread(target=server2.serve_forever)
    server3_thread = threading.Thread(target=server3.serve_forever)
    server1_thread.start()
    server2_thread.start()
    server3_thread.start()


run_servers()
