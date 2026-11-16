import paramiko
import stat

class SftpConnection:
    def __init__(self, hostname, port, username, password):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.ssh_client = None
        self.sftp = None

    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def open(self):
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh_client.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
            self.sftp = self.ssh_client.open_sftp()
        except Exception:
            self.ssh_client.close()
            raise ("SSH client connection error")

    def close(self):
        if self.sftp is not None:
            self.sftp.close()
            self.sftp = None
        if self.ssh_client is not None:
            self.ssh_client.close()
            self.ssh_client = None

    def read_file(self, img_path):
        with self.sftp.open(img_path, "rb") as f:
            f.prefetch()
            return f.read()

    def list_files(self, remote_path, files=None):
        if files is None:
            files = []
        dirs = []
        for entry in self.sftp.listdir_attr(remote_path):
            path = f"{remote_path}/{entry.filename}"
            if stat.S_ISDIR(entry.st_mode):
                dirs.append(path)
            else:
                files.append(path)
        for dirname in dirs:
            self.list_files(dirname, files)
        return files