import queue
from ML.OCR_Pipeline.SftpConnection import SftpConnection

class SftpPool:
    def __init__(self, hostname, port, username, password, size=8):
        self.hostname = hostname 
        self.port = port 
        self.username = username
        self.password = password
        self.size = size
        self.queue = queue.Queue()
        self.is_open = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def open(self):
        if self.is_open:
            return
        try:
            for i in range(0, self.size):
                connection = SftpConnection(self.hostname, self.port, self.username, self.password)
                connection.open()
                self.queue.put(connection)
            self.is_open = True
        except Exception as e:
            self.close()
            raise RuntimeError("One or multiple connections failed to open") from e

    def close(self):
        while True:
            try:
                connection = self.queue.get_nowait()
            except queue.Empty:
                break
            connection.close()
        self.is_open = False

    def read_file(self, img_path):
        connection = self.queue.get()
        try:
            return connection.read_file(img_path)
        finally:
            self.queue.put(connection)