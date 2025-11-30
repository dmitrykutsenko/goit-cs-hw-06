import socket
import multiprocessing
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import pathlib
import mimetypes
from datetime import datetime
from pymongo import MongoClient


# ------------------ Socket Server ------------------
def socket_server():
    HOST = "0.0.0.0"
    PORT = 5000

    client = MongoClient("mongodb://mongo:27017/")
    db = client["messages_db"]
    collection = db["messages"]

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Socket server running on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(1024)
                if not data:
                    continue
                # decode and parse key=value&key=value
                decoded = urllib.parse.unquote_plus(data.decode())
                data_dict = {k: v for k, v in [el.split("=") for el in decoded.split("&")]}
                # add timestamp
                doc = {
                    "date": str(datetime.now()),
                    "username": data_dict.get("username", ""),
                    "message": data_dict.get("message", "")
                }
                collection.insert_one(doc)
                print("Saved:", doc)


# ------------------ HTTP Server ------------------
class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)

        if pr_url.path == "/":
            self.send_html_file("front-init/index.html")
        elif pr_url.path.startswith("/message"):
            self.send_html_file("front-init/message.html")
        else:
            if pathlib.Path("front-init").joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file("front-init/error.html", 404)

    def do_POST(self):
        data = self.rfile.read(int(self.headers["Content-Length"]))
        # forward to socket server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("localhost", 5000))
            sock.sendall(data)

        # redirect back to home
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", "text/plain")
        self.end_headers()
        with open(f"front-init{self.path}", "rb") as file:
            self.wfile.write(file.read())


def run_http():
    server_address = ("", 3000)
    http = HTTPServer(server_address, HttpHandler)
    print("HTTP server running on port 3000")
    http.serve_forever()


# ------------------ Main ------------------
if __name__ == "__main__":
    p1 = multiprocessing.Process(target=run_http)
    p2 = multiprocessing.Process(target=socket_server)

    p1.start()
    p2.start()

    p1.join()
    p2.join()
