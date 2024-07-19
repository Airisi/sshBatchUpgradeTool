# class UpgradeManager:
#     def __init__(self, ssh_manager):
#         self.ssh_manager = ssh_manager
#
#     async def perform_upgrade_async(self):
#         if not await self.ssh_manager.ping_host():
#             raise Exception(f'Host {self.ssh_manager.host} is not reachable.')
#
#         try:
#             await self.ssh_manager.connect_async()
#             stdout, stderr = await self.ssh_manager.execute_command_async('echo 1 >> /home/yyz/ssh_test')
#             await self.ssh_manager.close_async()
#             if stderr:
#                 raise Exception(stderr)
#             return stdout or "Successfully upgrade."
#         except Exception as e:
#             raise Exception(str(e))
import asyncio
import os


import os
import asyncssh


class UpgradeManager:
    def __init__(self, ssh_manager):
        self.ssh_manager = ssh_manager

    async def perform_upgrade_async(self, upgrade_file_path, upgrade_script_path):
        if not await self.ssh_manager.ping_host():
            raise Exception(f'Host {self.ssh_manager.host} is not reachable.')

        try:
            await self.ssh_manager.connect_async()

            # 构建远程临时文件路径
            remote_file_path = f'/tmp/{os.path.basename(upgrade_file_path)}'
            remote_script_path = f'/tmp/{os.path.basename(upgrade_script_path)}'

            # 使用upload_files_async上传文件和脚本
            await self.ssh_manager.upload_file_async(upgrade_file_path, '/tmp')
            # 问题：这里不关闭重新打开，SSH连接会断开
            await self.ssh_manager.close_async()
            await self.ssh_manager.connect_async()
            await self.ssh_manager.upload_file_async(upgrade_script_path, '/tmp')
            # 问题：这里不关闭重新打开，SSH连接会断开
            await self.ssh_manager.close_async()
            await self.ssh_manager.connect_async()
            # 给脚本执行权限
            await self.ssh_manager.execute_command_async(f'chmod +x {remote_script_path}')

            # 执行升级脚本，将上传的文件路径作为参数传递
            stdout, stderr = await self.ssh_manager.execute_command_async(f'{remote_script_path} {remote_file_path}')

            # 清理临时文件
            await self.ssh_manager.execute_command_async(f'rm {remote_file_path} {remote_script_path}')

            await self.ssh_manager.close_async()
            if stderr:
                raise Exception(stderr)
            return stdout or "Successfully upgraded."
        except Exception as e:
            raise Exception(str(e))
