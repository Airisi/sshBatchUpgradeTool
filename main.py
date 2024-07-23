import os
import sys
import time
import json
import pandas as pd
import asyncio
from PyQt5 import uic
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QPushButton, QLineEdit, \
    QVBoxLayout, QDialog, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal, QFileInfo, QByteArray
from ssh_manager import SSHManager
from upgrade_manager import UpgradeManager


class SSHConfigEditor(QDialog):
    def __init__(self, ip, username, password, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit SSH Config")
        self.layout = QVBoxLayout(self)

        self.ip_entry = QLineEdit(self)
        self.ip_entry.setText(ip)
        self.layout.addWidget(self.ip_entry)

        self.username_entry = QLineEdit(self)
        self.username_entry.setText(username)
        self.layout.addWidget(self.username_entry)

        self.password_entry = QLineEdit(self)
        self.password_entry.setText(password)
        self.password_entry.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.password_entry)

        self.save_button = QPushButton("Save", self)
        self.save_button.clicked.connect(self.accept)
        self.layout.addWidget(self.save_button)

    def get_data(self):
        return self.ip_entry.text(), self.username_entry.text(), self.password_entry.text()


class AsyncWorker(QThread):
    finished = pyqtSignal(int, str, str)  # 行号，状态，消息

    def __init__(self, coro, row):
        super().__init__()
        self.coro = coro
        self.row = row

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.coro)
            self.finished.emit(self.row, "Success", str(result))
        except Exception as e:
            self.finished.emit(self.row, "Fail", str(e))
        finally:
            loop.close()


class MainWindow(QMainWindow):
    """
    主窗口类，继承自QMainWindow。
    提供UI界面和升级内核的功能。
    """
    CONFIG_FILE = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), 'config.json')

    def __init__(self):
        """
        初始化主窗口。
        加载UI界面并设置升级按钮的点击事件。
        """
        super().__init__()
        self._last_opened_dir = ''
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        ui_path = os.path.join(base_path, 'ui/main_window.ui')
        uic.loadUi(ui_path, self)
        self.addSSHConfigButton.clicked.connect(self.add_ssh_config)
        self.connectAllButton.clicked.connect(self.connect_all)
        self.upgradeFileButton.clicked.connect(self.select_upgrade_file)
        self.upgradeScriptButton.clicked.connect(self.select_upgrade_script)
        self.sshConfigTable.setColumnCount(7)
        self.sshConfigTable.setHorizontalHeaderLabels(
            ['IP', 'Username', 'Password', 'Upgrade', 'Delete', 'State', 'Logs'])
        header = self.sshConfigTable.horizontalHeader()
        header.setStretchLastSection(True)
        self.importButton.clicked.connect(self.load_ssh_configs)
        self.exportButton.clicked.connect(self.save_ssh_configs)
        self.clearConfigTableButton.clicked.connect(self.clear_ssh_configs)
        self.workers = []

        # 加载配置
        self.load_config()

    def select_upgrade_file(self):
        initial_dir = self.get_last_opened_dir()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Upgrade File", initial_dir, "All Files (*)")
        if file_path:
            self.upgradeFileEntry.setText(file_path)
            self.save_last_opened_dir(file_path)

    def select_upgrade_script(self):
        initial_dir = self.get_last_opened_dir()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Upgrade Script", initial_dir,
                                                   "Shell Scripts (*.sh);;All Files (*)")
        if file_path:
            self.upgradeScriptEntry.setText(file_path)
            self.save_last_opened_dir(file_path)

    def add_ssh_config(self):
        """
        添加新的SSH配置。
        """
        ip = self.ipEntry.text()
        username = self.usernameEntry.text()
        password = self.passwordEntry.text()
        if ip and username and password:
            row_position = self.sshConfigTable.rowCount()
            self.sshConfigTable.insertRow(row_position)

            self.sshConfigTable.setItem(row_position, 0, QTableWidgetItem(ip))
            self.sshConfigTable.setItem(row_position, 1, QTableWidgetItem(username))
            self.sshConfigTable.setItem(row_position, 2, QTableWidgetItem(password))

            upgrade_button = QPushButton('Upgrade')
            upgrade_button.clicked.connect(lambda _, r=row_position: self.connect_selected(r))
            self.sshConfigTable.setCellWidget(row_position, 3, upgrade_button)

            delete_button = QPushButton('Delete')
            delete_button.clicked.connect(lambda _, r=row_position: self.delete_ssh_config(r))
            self.sshConfigTable.setCellWidget(row_position, 4, delete_button)

    def delete_ssh_config(self, row):
        self.sshConfigTable.removeRow(row)
        # 更新所有删除按钮的lambda函数
        for i in range(self.sshConfigTable.rowCount()):
            upgrade_button = self.sshConfigTable.cellWidget(i, 3)
            upgrade_button.clicked.disconnect()
            upgrade_button.clicked.connect(lambda _, r=i: self.connect_selected(r))

            delete_button = self.sshConfigTable.cellWidget(i, 4)
            delete_button.clicked.disconnect()
            delete_button.clicked.connect(lambda _, r=i: self.delete_ssh_config(r))

    def clear_ssh_configs(self):
        """
        清空SSH配置。
        """
        self.sshConfigTable.clearContents()
        self.sshConfigTable.setRowCount(0)

    async def connect_ssh(self, row):
        """
        连接SSH并执行升级操作。
        """
        ip = self.sshConfigTable.item(row, 0).text()
        username = self.sshConfigTable.item(row, 1).text()
        password = self.sshConfigTable.item(row, 2).text()
        ssh_manager = SSHManager(ip, username, password)
        upgrade_manager = UpgradeManager(ssh_manager)
        try:
            result = await upgrade_manager.perform_upgrade_async()
            if isinstance(result, str):  # 如果是错误消息
                raise Exception(result)
            stdout, stderr = result
            if stderr:
                raise Exception(stderr)
            self.sshConfigTable.setItem(row, 5, QTableWidgetItem("Success"))
            self.sshConfigTable.setItem(row, 6, QTableWidgetItem(stdout))
        except Exception as e:
            self.sshConfigTable.setItem(row, 5, QTableWidgetItem("Fail"))
            self.sshConfigTable.setItem(row, 6, QTableWidgetItem(str(e)))

    def connect_all(self):
        """
        为所有SSH配置创建并启动异步工作线程。
        """
        self.connectAllButton.setEnabled(False)  # 禁用“连接全部”按钮
        for row in range(self.sshConfigTable.rowCount()):
            self.connect_selected(row)

    def connect_selected(self, row):
        ip = self.sshConfigTable.item(row, 0).text()
        username = self.sshConfigTable.item(row, 1).text()
        password = self.sshConfigTable.item(row, 2).text()
        upgrade_file = self.upgradeFileEntry.text()
        upgrade_script = self.upgradeScriptEntry.text()

        if not upgrade_file or not upgrade_script:
            QMessageBox.warning(self, "Warning", "Please select both upgrade file and script.")
            return

        ssh_manager = SSHManager(ip, username, password)
        upgrade_manager = UpgradeManager(ssh_manager)

        worker = AsyncWorker(upgrade_manager.perform_upgrade_async(upgrade_file, upgrade_script), row)
        worker.finished.connect(self.on_worker_finished)
        self.workers.append(worker)
        worker.start()

        upgrade_button = self.sshConfigTable.cellWidget(row, 3)
        upgrade_button.setEnabled(False)

    def on_worker_finished(self, row, status, message):
        status_item = QTableWidgetItem(status)
        message_item = QTableWidgetItem(message)

        if status == "Success":
            status_item.setForeground(QColor("green"))
            message_item.setForeground(QColor("green"))
        else:  # status == "Fail"
            status_item.setForeground(QColor("red"))
            message_item.setForeground(QColor("red"))

        self.sshConfigTable.setItem(row, 5, status_item)
        self.sshConfigTable.setItem(row, 6, message_item)

        # 启用升级按钮
        upgrade_button = self.sshConfigTable.cellWidget(row, 3)  # 注意：升级按钮在第4列（索引3）
        upgrade_button.setEnabled(True)

        # 延时0.1秒 确保当前worker为停止状态
        time.sleep(0.1)

        # 可选：清理完成的worker
        self.workers = [w for w in self.workers if w.isRunning()]

        # 打印每个worker的状态
        # for w in self.workers:
        #     print(f"Worker {w.row} is running: {w.isRunning()}")

        # 检查是否所有worker均已完成
        if not self.workers:
            self.connectAllButton.setEnabled(True)

    def load_ssh_configs(self):
        initial_dir = self.get_last_opened_dir()
        file_path, _ = QFileDialog.getOpenFileName(self, "Load SSH Configs", initial_dir,
                                                   "CSV Files (*.csv);;All Files (*)")
        if file_path:
            df = pd.read_csv(file_path)
            self.sshConfigTable.setRowCount(0)
            for index, row in df.iterrows():
                row_position = self.sshConfigTable.rowCount()
                self.sshConfigTable.insertRow(row_position)

                self.sshConfigTable.setItem(row_position, 0, QTableWidgetItem(row['IP']))
                self.sshConfigTable.setItem(row_position, 1, QTableWidgetItem(row['Username']))
                self.sshConfigTable.setItem(row_position, 2, QTableWidgetItem(row['Password']))

                upgrade_button = QPushButton('Upgrade')
                upgrade_button.clicked.connect(lambda _, r=row_position: self.connect_selected(r))
                self.sshConfigTable.setCellWidget(row_position, 3, upgrade_button)

                delete_button = QPushButton('Delete')
                delete_button.clicked.connect(lambda _, r=row_position: self.delete_ssh_config(r))
                self.sshConfigTable.setCellWidget(row_position, 4, delete_button)

            self.save_last_opened_dir(file_path)

    def save_ssh_configs(self):
        initial_dir = self.get_last_opened_dir()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save SSH Configs", initial_dir,
                                                   "CSV Files (*.csv);;All Files (*)")
        if file_path:
            data = []
            for row in range(self.sshConfigTable.rowCount()):
                data.append({
                    'IP': self.sshConfigTable.item(row, 0).text(),
                    'Username': self.sshConfigTable.item(row, 1).text(),
                    'Password': self.sshConfigTable.item(row, 2).text()
                })
            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False)
            self.save_last_opened_dir(file_path)

    def save_config(self):
        """
        保存配置到 config.json 文件。
        """
        config = {
            'geometry': self.saveGeometry().toHex().data().decode(),
            'state': self.saveState().toHex().data().decode(),
            'upgrade_file': self.upgradeFileEntry.text(),
            'upgrade_script': self.upgradeScriptEntry.text(),
            'last_opened_dir': self.get_last_opened_dir() + '/',
            'ssh_configs': [
                {
                    'IP': self.sshConfigTable.item(row, 0).text(),
                    'Username': self.sshConfigTable.item(row, 1).text(),
                    'Password': self.sshConfigTable.item(row, 2).text()
                }
                for row in range(self.sshConfigTable.rowCount())
            ],
            'entries': {
                'ip': self.ipEntry.text(),
                'username': self.usernameEntry.text(),
                'password': self.passwordEntry.text()
            }
        }
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(config, f)

    def load_config(self):
        """
        从 config.json 文件加载配置。
        """
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                config = json.load(f)
                geometry = config.get('geometry')
                state = config.get('state')
                upgrade_file = config.get('upgrade_file', '')
                upgrade_script = config.get('upgrade_script', '')
                last_opened_dir = config.get('last_opened_dir', '')
                ssh_configs = config.get('ssh_configs', [])
                entries = config.get('entries', {})

                if geometry:
                    self.restoreGeometry(QByteArray.fromHex(geometry.encode()))

                if state:
                    self.restoreState(QByteArray.fromHex(state.encode()))

                self.upgradeFileEntry.setText(upgrade_file)
                self.upgradeScriptEntry.setText(upgrade_script)

                # 设置 last_opened_dir 而不引发错误
                self.set_last_opened_dir(last_opened_dir)

                # 加载 SSH 配置
                for ssh_config in ssh_configs:
                    row_position = self.sshConfigTable.rowCount()
                    self.sshConfigTable.insertRow(row_position)
                    self.sshConfigTable.setItem(row_position, 0, QTableWidgetItem(ssh_config.get('IP', '')))
                    self.sshConfigTable.setItem(row_position, 1, QTableWidgetItem(ssh_config.get('Username', '')))
                    self.sshConfigTable.setItem(row_position, 2, QTableWidgetItem(ssh_config.get('Password', '')))

                    upgrade_button = QPushButton('Upgrade')
                    upgrade_button.clicked.connect(lambda _, r=row_position: self.connect_selected(r))
                    self.sshConfigTable.setCellWidget(row_position, 3, upgrade_button)

                    delete_button = QPushButton('Delete')
                    delete_button.clicked.connect(lambda _, r=row_position: self.delete_ssh_config(r))
                    self.sshConfigTable.setCellWidget(row_position, 4, delete_button)

                ip = entries.get('ip', '')
                username = entries.get('username', '')
                password = entries.get('password', '')

                self.ipEntry.setText(ip)
                self.usernameEntry.setText(username)
                self.passwordEntry.setText(password)

        except FileNotFoundError:
            # 如果配置文件不存在，不执行任何操作
            pass
        except Exception as e:
            # 捕获并记录其他可能的异常
            print(f"Error loading configuration: {e}")

    def get_last_opened_dir(self):
        return getattr(self, '_last_opened_dir', '')

    def set_last_opened_dir(self, path):
        self._last_opened_dir = QFileInfo(path).absolutePath() if path else ''

    def save_last_opened_dir(self, path):
        self.set_last_opened_dir(path)
        self.save_config()

    def closeEvent(self, event):
        """
        处理窗口关闭事件，确保在关闭前保存配置。
        """
        self.save_config()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
