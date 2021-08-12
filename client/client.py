import sys
import os
from PyQt5.QtWidgets import QDialog, QApplication, QMessageBox, QStackedWidget, QTableWidgetItem
from PyQt5.uic import loadUi
from PyQt5.QtCore import QDate, QThread, pyqtSignal
import socket
import json

HEADER = 64
FORMAT = "utf-8"

# code
SUCCESS = 0
FAILED = -1

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def send(message):
    body = json.dumps(message).encode(FORMAT)
    message_length = len(body)
    header = str(message_length).encode(FORMAT)
    header += b' ' * (HEADER - len(header))

    client.send(header)
    client.send(body)

def get_message_length():
        message_header = client.recv(HEADER).decode(FORMAT)
        if message_header:
            return int(message_header)
        else:
            return 0

def receive_message(body_length):
    message = client.recv(body_length).decode(FORMAT)
    body = json.loads(message)
    return body

class Receiver(QThread):
    received = pyqtSignal(object)

    def __init__(self, parent=None):
        super(Receiver, self).__init__(parent)

    def run(self):
        listening = True
        while listening:
            try:
                message_length = get_message_length()
                if message_length != 0 and listening == True:
                    response = receive_message(message_length)
                    self.received.emit(response)
            except Exception as e:
                listening = False
class MainWindow(QDialog):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('main.ui', self)
        self.dateInput.setDate(QDate.currentDate())
        self.checkBox.stateChanged.connect(self.handleCheckbox)
        self.liveBtn.clicked.connect(self.subscribeLive)
        self.searchBtn.clicked.connect(self.handleSearch)
        self.disconnectBtn.clicked.connect(self.handleDisconnect)
        self.bgProcess = Receiver(self)
        self.bgProcess.received.connect(self.handleResponse)

    def start_receive(self):
        if not self.bgProcess.isRunning():
            self.bgProcess.start()

    def add_row(self, row):
        rowPos = self.tableWidget.rowCount()
        self.tableWidget.insertRow(rowPos)
        self.tableWidget.setItem(rowPos, 0, QTableWidgetItem(row['currency']))
        self.tableWidget.setItem(rowPos, 1, QTableWidgetItem(str(int(row['buy']))))
        self.tableWidget.setItem(rowPos, 2, QTableWidgetItem(str(int(row['sell']))))
        self.tableWidget.setItem(rowPos, 3, QTableWidgetItem(row['update_at']))

    def handleSearch(self):
        try:
            self.liveBtn.setEnabled(True)
            currency = str(self.currencyInput.currentText())
            payload = {
                "action": "search",
                "body": {
                    "currency": currency
                }
            }
            if self.checkBox.isChecked():
                payload["body"]["date"] = str(self.dateInput.date().toPyDate())
            send(payload)
        except WindowsError as e:
            QMessageBox.critical(self, "Error!", "Connection error",
                                QMessageBox.Ok | QMessageBox.Ok)
            widget.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "Error!", repr(e),
                                QMessageBox.Ok | QMessageBox.Ok)
        
    def handleCheckbox(self, int):
        if self.checkBox.isChecked():
            self.dateInput.setEnabled(True)
        else:
            self.dateInput.setEnabled(False)

    def subscribeLive(self):
        try:
            send({
                "action": "live",
                "body": ""
            })
            self.liveBtn.setEnabled(False)
        except WindowsError as e:
            QMessageBox.critical(self, "Error!", "Connection error",
                                QMessageBox.Ok | QMessageBox.Ok)
            widget.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "Error!", repr(e),
                                QMessageBox.Ok | QMessageBox.Ok)

    def handleDisconnect(self):
        reply = QMessageBox.question(self, 'Disconnect', 'Are you sure?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            send({
                "action": "disconnect",
                "body": ""
            })
            global client
            client.close()
            widget.setCurrentIndex(0)

    def handleResponse(self, data):
        if data['code'] == FAILED:
            QMessageBox.critical(self, "Error!", data['body'],
                                QMessageBox.Ok | QMessageBox.Ok)
        else:
            if data['action'] == 'disconnect':
                QMessageBox.information(self, "Disconnect!", "The connection being shutdown by the server",
                                QMessageBox.Ok | QMessageBox.Ok)
                global client
                client.close()
                widget.setCurrentIndex(0)
            elif data['action'] == 'live' or data['action'] == 'search' or data['action'] == 'live-rate':
                self.tableWidget.setRowCount(0)
                for row in data['body']:
                    self.add_row(row)


class ConnectWindow(QDialog):
    def __init__(self):
        super(ConnectWindow, self).__init__()
        loadUi('connect.ui', self)
        self.connectBtn.clicked.connect(self.connect)
    def connect(self):
        try:
            ip = self.ipInput.text()
            port = self.portInput.text()
            global client
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((ip, int(port)))
            QMessageBox.information(self, "Success!", "Connected to server successfully",
                                QMessageBox.Ok | QMessageBox.Ok)
            widget.setCurrentIndex(widget.currentIndex() + 1)
        except WindowsError as e:
            QMessageBox.critical(self, "Error!", "Connection error",
                                QMessageBox.Ok | QMessageBox.Ok)
            widget.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "Error!", repr(e),
                                QMessageBox.Ok | QMessageBox.Ok)

class LoginWindow(QDialog):
    def __init__(self):
        super(LoginWindow, self).__init__()
        loadUi('login.ui', self)
        self.loginBtn.clicked.connect(self.login)
        self.toRegBtn.clicked.connect(self.to_register)
    def login(self):
        try:
            username = self.username.text()
            password = self.password.text()
            send({
                "action": "login", 
                "body": {
                    "username": username,
                    "password": password
                }
            })
            message_length = get_message_length()
            if message_length != 0:
                response = receive_message(message_length)
                if response["code"] == FAILED:
                    QMessageBox.critical(self, "Login failed!", response['body'],
                                QMessageBox.Ok | QMessageBox.Ok)
                else:
                    QMessageBox.information(self, "Login success!", response['body'],
                                QMessageBox.Ok | QMessageBox.Ok)
                    main.start_receive()
                    widget.setCurrentIndex(widget.currentIndex() + 2)
        except WindowsError as e:
            QMessageBox.critical(self, "Error!", "Connection Error",
                                QMessageBox.Ok | QMessageBox.Ok)
            widget.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "Error!", str(e),
                                QMessageBox.Ok | QMessageBox.Ok)

    def to_register(self):
        widget.setCurrentIndex(widget.currentIndex() + 1)

class RegisterWindow(QDialog):
    def __init__(self):
        super(RegisterWindow, self).__init__()
        loadUi('register.ui', self)
        self.toLoginBtn.clicked.connect(self.to_login)
        self.registerBtn.clicked.connect(self.register)
    
    def register(self):
        try:
            username = self.username.text()
            password = self.password.text()
            send({
                "action": "register", 
                "body": {
                    "username": username,
                    "password": password
                }
            })
            message_length = get_message_length()
            if message_length != 0:
                response = receive_message(message_length)
                if response["code"] == FAILED:
                    QMessageBox.critical(self, "Register failed!", response['body'],
                                QMessageBox.Ok | QMessageBox.Ok)
                else:
                    QMessageBox.information(self, "Register success!", response['body'],
                                QMessageBox.Ok | QMessageBox.Ok)
                    self.to_login()
        except WindowsError as e:
            QMessageBox.critical(self, "Error!", "Connection error",
                                QMessageBox.Ok | QMessageBox.Ok)
            widget.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "Error!", repr(e),
                                QMessageBox.Ok | QMessageBox.Ok)
                                
    def to_login(self):
        widget.setCurrentIndex(widget.currentIndex() - 1)

if __name__ == "__main__":
    # ui start
    app = QApplication(sys.argv)
    widget = QStackedWidget()
    main = MainWindow()
    connect = ConnectWindow()
    login = LoginWindow()
    register = RegisterWindow()
    widget.addWidget(connect)
    widget.addWidget(login)
    widget.addWidget(register)
    widget.addWidget(main)
    widget.setFixedSize(420, 480)
    widget.setWindowTitle("Money Exchange Rate")
    widget.show()
    app.exec_()
    client.close()


