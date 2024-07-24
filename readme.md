### 项目名称

SSH 配置管理和升级工具

### 项目简介

本项目是一个基于 PyQt5 的图形用户界面 (GUI) 应用程序，用于管理多个 SSH 配置，并通过异步方式执行远程主机的文件升级操作。它支持添加、删除和导入导出 SSH 配置信息，以及一键执行所有配置的远程升级操作。

### 文件结构

- `main.py`：应用程序的主文件，包含主窗口类 `MainWindow` 及其相关逻辑。
- `requirements.txt`：列出项目依赖的 Python 包。
- `ssh_manager.py`：定义 `SSHManager` 类，用于处理 SSH 连接和命令执行。
- `upgrade_manager.py`：定义 `UpgradeManager` 类，用于处理远程主机的升级操作。

### 依赖安装

在运行此项目之前，请确保已安装所需的 Python 包。您可以使用以下命令安装它们：

```sh
pip install -r requirements.txt
```

### 主要功能

#### 主窗口

`main.py` 文件包含 `MainWindow` 类，提供以下功能：

- **添加 SSH 配置**：通过输入 IP 地址、用户名和密码来添加新的 SSH 配置。
- **删除 SSH 配置**：从配置列表中删除指定的 SSH 配置。
- **导入和导出 SSH 配置**：从 CSV 文件中加载或保存 SSH 配置信息。
- **选择升级文件和脚本**：选择要上传和执行的升级文件和脚本。
- **连接所有配置**：一键执行所有 SSH 配置的远程升级操作，并显示每个配置的执行状态和日志。

#### SSH 管理

`ssh_manager.py` 文件包含 `SSHManager` 类，提供以下功能：

- **异步建立 SSH 连接**：通过异步方式连接到远程主机。
- **异步执行命令**：在远程主机上异步执行命令并返回结果。
- **异步上传文件**：将本地文件异步上传到远程主机。
- **关闭连接**：关闭 SSH 连接。

#### 升级管理

`upgrade_manager.py` 文件包含 `UpgradeManager` 类，提供以下功能：

- **执行升级操作**：在远程主机上执行文件上传和脚本执行，完成升级操作。
- **清理临时文件**：升级完成后清理远程主机上的临时文件。

### 运行程序

运行程序的步骤如下：

1. 启动应用程序：

```sh
python main.py
```

2. 添加 SSH 配置信息：在应用程序中输入 IP 地址、用户名和密码，点击“添加”按钮。
3. 选择升级文件和脚本：点击“选择文件”和“选择脚本”按钮，选择相应的文件。
4. 执行升级操作：点击“连接所有”按钮，执行所有配置的远程升级操作。

### 导入和导出文件功能

#### 导出 SSH 配置

用户可以将当前的 SSH 配置信息导出到 CSV 文件中，方便保存和共享。导出步骤如下：

1. 在应用程序中点击“导出”按钮。
2. 选择要保存的文件路径和文件名。
3. 应用程序会将所有 SSH 配置信息保存到指定的 CSV 文件中。

#### 导入 SSH 配置

用户可以从 CSV 文件中导入 SSH 配置信息，快速加载大量配置。导入步骤如下：

1. 在应用程序中点击“导入”按钮。
2. 选择包含 SSH 配置信息的 CSV 文件。
3. 应用程序会从选定的 CSV 文件中读取并加载所有 SSH 配置信息。

#### CSV 文件模板

导入的 CSV 文件需要满足以下格式：

```csv
Host,Username,Password
192.168.0.1,user1,password1
192.168.0.2,user2,password2
192.168.0.3,user3,password3
```

每行表示一个 SSH 配置信息，包含三个字段：IP 地址、用户名和密码。确保文件没有额外的空行或格式错误。

### 使用PyInstaller打包

#### 安装PyInstaller

首先，确保在虚拟环境中安装PyInstaller：

```sh
pip install pyinstaller
```

#### 打包应用程序

在项目根目录中运行以下命令以使用PyInstaller打包应用程序：

```sh
pyinstaller SSHTool.spec
```

这将生成`dist/UpgradeTool`目录，其中包含打包后的可执行文件。

#### 运行打包后的应用程序

进入`dist/UpgradeTool`目录，并运行生成的可执行文件：

```sh
cd dist/UpgradeTool
./UpgradeTool.exe  # 对于Windows系统使用 `UpgradeTool.exe`
```
这样，你就可以成功地打包并运行你的应用程序了。

### 总结

此项目旨在简化多台远程主机的 SSH 配置管理和升级操作，通过图形界面和异步处理提高效率。希望此工具能为您的远程管理工作带来便利。

