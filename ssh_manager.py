import asyncio
import asyncssh


class SSHManager:
    """
    该类用于建立SSH连接，并执行远程命令。

    参数:
    - host: 远程主机的地址。
    - username: 远程主机的登录用户名。
    - password: 远程主机的登录密码。
    """

    def __init__(self, host, username, password):
        """
        初始化SSHManager实例。

        设置远程主机地址、用户名和密码。
        """
        self.host = host
        self.username = username
        self.password = password
        self.client = None

    async def ping_host(self):
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(self.host, 22), timeout=1)
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, OSError):
            print(f'Ping failed: {self.host}')
            return False

    async def connect_async(self):
        """
        异步建立SSH连接。

        创建SSHClient实例，并使用提供的凭证连接到远程主机。
        """
        max_retries = 1
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                self.client = await asyncssh.connect(
                    self.host,
                    username=self.username,
                    password=self.password,
                    known_hosts=None
                )
                return
            except (asyncssh.Error, OSError) as exc:
                print(f'SSH connection failed (attempt {attempt + 1}): {exc}')
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise Exception(f'Failed to connect after {max_retries} attempts: {exc}')

    async def execute_command_async(self, command):
        """
        异步执行远程命令并返回结果。

        参数:
        - command: 待执行的远程命令。

        返回:
        - stdout: 命令的标准输出。
        - stderr: 命令的标准错误输出。
        """
        if self.client is None:
            return '', 'SSH client is not connected. Please call connect_async first.'

        try:
            result = await self.client.run(command)
            return result.stdout, result.stderr
        except (asyncssh.Error, OSError) as exc:
            error_msg = f'Failed to execute command: {exc}'
            print(error_msg)
            return '', error_msg

    async def upload_file_async(self, local_path, remote_path):
        """
        异步上传文件到远程主机。

        参数:
        - local_path: 本地文件路径。
        - remote_path: 远程文件路径。
        """
        if self.client is None:
            raise Exception('SSH client is not connected. Please call connect_async first.')

        try:
            await asyncssh.scp(local_path, (self.client, remote_path))
            print(f'File {local_path} uploaded to {remote_path} successfully.')
        except (asyncssh.Error, OSError) as exc:
            print(f'Failed to upload file: {exc}')
            raise

    async def close_async(self):
        """
        关闭SSH连接。
        """
        if self.client:
            self.client.close()
            await self.client.wait_closed()
