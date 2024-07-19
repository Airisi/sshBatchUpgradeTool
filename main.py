import sys
import time
import json
import pandas as pd
import asyncio
from PyQt5 import uic
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QPushButton, QLineEdit, \
    QVBoxLayout, QDialog, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal
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

    CONFIG_FILE = 'config.json'

    def __init__(self):
        """
        初始化主窗口。
        加载UI界面并设置升级按钮的点击事件。
        """
        super().__init__()
        uic.loadUi('ui/main_window.ui', self)
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
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Upgrade File", "", "All Files (*)")
        if file_path:
            self.upgradeFileEntry.setText(file_path)
            self.save_config()  # 保存配置

    def select_upgrade_script(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Upgrade Script", "", "Shell Scripts (*.sh);;All Files (*)")
        if file_path:
            self.upgradeScriptEntry.setText(file_path)
            self.save_config()  # 保存配置

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

            self.save_config()  # 保存配置

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

        self.save_config()  # 保存配置

    def clear_ssh_configs(self):
        """
        清空SSH配置。
        """
        self.sshConfigTable.clearContents()
        self.sshConfigTable.setRowCount(0)
        self.save_config()  # 保存配置

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
        #     print(f"Worker {w} is running: {w.isRunning()}")

        # 检查是否所有的worker都完成了工作
        if all(not w.isRunning() for w in self.workers):
            self.connectAllButton.setEnabled(True)  # 启用“连接全部”按钮

    def save_config(self):
        config = {
            'upgrade_file': self.upgradeFileEntry.text(),
            'upgrade_script': self.upgradeScriptEntry.text(),
        }
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(config, f)

    def load_config(self):
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.upgradeFileEntry.setText(config.get('upgrade_file', ''))
                self.upgradeScriptEntry.setText(config.get('upgrade_script', ''))
        except FileNotFoundError:
            pass

    def save_ssh_configs(self):
        """
        保存SSH配置到文件。
        """
        file_path, _ = QFileDialog.getSaveFileName(self, "Save SSH Configs", "", "CSV Files (*.csv)")
        if file_path:
            data = []
            for row in range(self.sshConfigTable.rowCount()):
                row_data = []
                for column in range(self.sshConfigTable.columnCount()):
                    item = self.sshConfigTable.item(row, column)
                    if item:
                        row_data.append(item.text())
                    else:
                        widget = self.sshConfigTable.cellWidget(row, column)
                        if widget and isinstance(widget, QPushButton):
                            row_data.append(widget.text())
                        else:
                            row_data.append('')
                data.append(row_data)
            df = pd.DataFrame(data, columns=['IP', 'Username', 'Password', 'Upgrade', 'Delete', 'State', 'Logs'])
            df.to_csv(file_path, index=False)

    def load_ssh_configs(self):
        """
        从文件加载SSH配置。
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Load SSH Configs", "", "CSV Files (*.csv)")
        if file_path:
            df = pd.read_csv(file_path)
            self.sshConfigTable.setRowCount(len(df))
            for row in range(len(df)):
                for column in range(len(df.columns)):
                    item = QTableWidgetItem(str(df.iat[row, column]))
                    self.sshConfigTable.setItem(row, column, item)

                upgrade_button = QPushButton('Upgrade')
                upgrade_button.clicked.connect(lambda _, r=row: self.connect_selected(r))
                self.sshConfigTable.setCellWidget(row, 3, upgrade_button)

                delete_button = QPushButton('Delete')
                delete_button.clicked.connect(lambda _, r=row: self.delete_ssh_config(r))
                self.sshConfigTable.setCellWidget(row, 4, delete_button)


def main():
    """
    主函数，启动应用程序。
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
