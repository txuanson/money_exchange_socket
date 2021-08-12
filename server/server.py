import sys
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog, QApplication, QMessageBox
from PyQt5.uic import loadUi
import socket
import threading
import time
import requests
import json
import datetime
import sqlite3
from uuid import uuid4

# self module
import db
import crypto

# config server

HOST = socket.gethostbyname(socket.gethostname())
PORT = 8080
HEADER = 64
FORMAT = 'utf-8'

# message
SUCCESS = 0
FAILED = -1

# for crawl
API_HOST = 'https://vapi.vnappmob.com'
INTERVAL_UPDATE = 1800

class Client(QThread):
    client_logger = pyqtSignal(str)
    stop_signal = pyqtSignal(str)
    def __init__(self, parent=None):
        super(Client, self).__init__(parent)
        self.live = False
        
    def init(self, client, addr, client_id):
        self.client = client
        self.addr = addr
        self.client_id = client_id

    def get_message_length(self):
        message_header = self.client.recv(HEADER).decode(FORMAT)
        if message_header:
            return int(message_header)
        else:
            return 0

    def receive_message(self, message_length):
        message = self.client.recv(message_length).decode(FORMAT)
        body = json.loads(message)
        return (body['action'], body['body'])

    def send(self, action, code, body):
        if action == 'live-rate': 
            if self.live == False:
                return
            else:
                self.client_logger.emit(f'[LIVE]\t\t{self.addr} push rate')
        message = {
            "action": action,
            "code": code,
            "body": body
        }
        body = json.dumps(message).encode(FORMAT)
        message_length = len(body)
        header = str(message_length).encode(FORMAT)
        header += b' ' * (HEADER - len(header))

        self.client.send(header)
        self.client.send(body)

    def run(self):
        self.client_logger.emit(f'[CONNECTED]\t\t{self.addr} connected')
        self.on_connect = True
        while self.on_connect == True:
            try:
                message_length = self.get_message_length()
                if message_length != 0 and self.on_connect == True:
                    action, body = self.receive_message(message_length)
                    if action == 'login':
                        connection = sqlite3.connect("db.db", detect_types=sqlite3.PARSE_DECLTYPES)
                        if connection:
                            cur = connection.cursor()
                            query = '''SELECT password FROM account WHERE username = :username'''
                            cur.execute(query, body)
                            password = cur.fetchone()
                            cur.close()
                            connection.close()
                            if not password:
                                self.send("login", FAILED, "Wrong username or password!")
                            elif crypto.compare_password(body['password'], password[0]) == False:
                                self.send("login", FAILED, "Wrong username or password!")
                            else:
                                self.send( "login", SUCCESS, "Login success!")
                                self.client_logger.emit(f'\t\t{self.addr} login')
                    elif action == 'register':
                        connection = sqlite3.connect("db.db", detect_types=sqlite3.PARSE_DECLTYPES)
                        if connection:
                            cur = connection.cursor()
                            query = '''SELECT EXISTS(SELECT * FROM account WHERE username = :username)'''
                            cur.execute(query, body)
                            check = cur.fetchone()
                            if check[0] == 1:
                                self.send("register", FAILED, "Username existed")
                            else:
                                body['password'] = crypto.hash_password(body['password'])
                                db.register(body)
                                self.send("register", SUCCESS, "Register success")
                                self.client_logger.emit(f'\t\t{self.addr} register')
                            cur.close()
                            connection.close()
                    elif action == 'search':
                        self.live = False
                        connection = sqlite3.connect("db.db", detect_types=sqlite3.PARSE_DECLTYPES)
                        connection.row_factory = db.dict_factory
                        if connection:
                            cur = connection.cursor()
                            query = '''SELECT * FROM currency'''
                            subquery = ""
                            if 'date' in body and body['currency'] != 'All currencies':
                                subquery = ' WHERE update_at = :date AND currency = :currency'
                            elif 'date' in body:
                                subquery = ' WHERE update_at = :date'
                            elif body['currency'] != 'All currencies':
                                subquery = ' WHERE currency = :currency'
                            query += subquery + ' ORDER BY update_at ASC, currency ASC'
                            cur.execute(query, body)
                            res = cur.fetchall()
                            if len(res) == 0:
                                self.send("search", FAILED, "Data not found")
                            else:
                                self.send("search", SUCCESS, res)
                                self.client_logger.emit(f'\t\t{self.addr} search')
                            cur.close()
                            connection.close()
                    elif action == 'live':
                        self.live = True
                        connection = sqlite3.connect("db.db", detect_types=sqlite3.PARSE_DECLTYPES)
                        connection.row_factory = db.dict_factory
                        if connection:
                            cur = connection.cursor()
                            query = '''SELECT * FROM currency WHERE update_at = date('now', 'localtime') ORDER BY update_at ASC, currency ASC'''
                            cur.execute(query)
                            res = cur.fetchall()
                            if len(res) == 0:
                                self.send("live", FAILED, "Data not found")
                            else:
                                self.send("live", SUCCESS, res)
                                self.client_logger.emit(f'\t\t{self.addr} live')
                            cur.close()
                            connection.close()
                    elif action == 'disconnect':
                        # no need to send response here cuz the client disconnect already
                        self.on_connect = False
                    time.sleep(0.001) # reduce CPU usage
                else:
                    self.on_connect = False
            except Exception as e:
                self.on_connect = False
        self.client.shutdown(socket.SHUT_RDWR)
        self.client.close()
        self.stop_signal.emit(self.client_id)

    def client_stop(self):
        if self.isRunning():
            self.client.shutdown(socket.SHUT_RDWR)
            self.client.close()
            self.client_logger.emit(f'[DISCONNECTED]\t{self.addr} disconnected')
            self.terminate()

class Server(QThread):
    server_logger = pyqtSignal(str)
    clients = {}

    def __init__(self, parent=None):
        super(Server, self).__init__(parent)
    
    def run(self):
        self.SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.SERVER.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.SERVER.bind((HOST, PORT))
        self.SERVER.listen()
        self.online = True
        while self.online == True:
            try:
                client, address = self.SERVER.accept()
                client_thread = Client() # cant insert the parent thread here cuz of thread scheduler T_T
                client_id = str(uuid4())
                self.clients[client_id] = client_thread
                self.clients[client_id].init(client, address, client_id)
                self.clients[client_id].client_logger.connect(self.send_log)
                self.clients[client_id].stop_signal.connect(self.client_disconnect)
                self.clients[client_id].start()
                time.sleep(0.001)   # reduce CPU usage
            except:
                self.online = False
        self.SERVER.shutdown(socket.SHUT_RDWR)
        self.SERVER.close()

    def stop(self):
        if self.isRunning():
            self.online = False
            self.boardcast(action="disconnect", message="")
            if self.clients:
                for key in self.clients:
                    self.clients[key].client_stop()
                self.clients.clear()
            self.SERVER.close()
            self.terminate()
        
    def boardcast(self, action, message):
        if self.clients:
            for key in self.clients:
                self.clients[key].send(action, SUCCESS, message)

    def send_log(self, text: str):
        self.server_logger.emit(text)
    
    def client_disconnect(self, client_id: str):
        self.server_logger.emit(f'[DISCONNECTED]\t{self.clients[client_id].addr} disconnected')
        self.clients.pop(client_id)

class Crawler(QThread):
    boardcast_signal = pyqtSignal(list)

    def __init__(self, parent=None):
        super(Crawler, self).__init__(parent)
    
    def get_token(self):
        res = requests.get(
            API_HOST + '/api/request_api_key?scope=exchange_rate'
        )
        data = json.loads(res.text)
        return data["results"]

    def run(self):
        while True:
            token = self.get_token()
            response = requests.get(
                API_HOST + '/api/v2/exchange_rate/sbv',
                headers={
                    'Authorization': 'Bearer {}'.format(token)
                }
            )
            data = json.loads(response.text)
            # update rate to db
            db.update_rate(data["results"])
            # push rate -> clients
            connection = sqlite3.connect("db.db", detect_types=sqlite3.PARSE_DECLTYPES)
            connection.row_factory = db.dict_factory
            if connection:
                cur = connection.cursor()
                query = '''SELECT * FROM currency WHERE update_at = date('now', 'localtime') ORDER BY update_at ASC, currency ASC'''
                cur.execute(query)
                res = cur.fetchall()
                cur.close()
                connection.close()
            self.boardcast_signal.emit(res)
            # wait for 30 mins
            time.sleep(INTERVAL_UPDATE)

class MainWindow(QDialog):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('server.ui', self)
        self.startBtn.clicked.connect(self.start_server)
        self.shutdownBtn.clicked.connect(self.shutdown_server)
        self.server = Server(self)
        self.server.server_logger.connect(self.receive_log)
        self.server.started.connect(lambda: self.receive_log(f'[STARTED]\t\tServer started at {HOST}'))
        self.server.finished.connect(lambda: self.receive_log('[STOPPED]\t\tServer stopped...'))
        self.crawler = Crawler(self)
        self.crawler.boardcast_signal.connect(self.boardcast)
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Window Close', 'Are you sure you want to close the window?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # stop crawler
            if self.crawler.isRunning():
                self.crawler.terminate()
            # shutdown server
            if self.server.isRunning():
                self.server.stop()
            event.accept()
        else:
            event.ignore()

    def start_server(self):
        self.startBtn.setEnabled(False)
        self.shutdownBtn.setEnabled(True)
        if not self.crawler.isRunning():
            self.crawler.start()
        if not self.server.isRunning():
            self.server.start()

    def shutdown_server(self):
        reply = QMessageBox.question(self, 'Shutdown the server?', 'This action will disconnect all the connected client! Proceed?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.startBtn.setEnabled(True)
            self.shutdownBtn.setEnabled(False)
            # stop crawler
            if self.crawler.isRunning():
                self.crawler.terminate()
            # shutdown server
            if self.server.isRunning():
                self.server.stop()
    
    def receive_log(self, text):
        self.logger.append(text)

    def boardcast(self, rate: list):
        self.server.boardcast('live-rate', rate)

if __name__ == "__main__":
    # ui start
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()

