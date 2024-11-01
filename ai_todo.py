import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLineEdit, QTextEdit, 
                            QListWidget, QMessageBox, QCheckBox, QListWidgetItem,
                            QMenu, QStyle)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction
import requests
from datetime import datetime
from functools import partial


class ClickableLineEdit(QLineEdit):
    clicked = pyqtSignal()  # 自定义点击信号
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if not self.isReadOnly():  # 如果是编辑状态，使用默认行为
            return
        self.clicked.emit()  # 发送点击信号

class TaskItem(QWidget):
    deleted = pyqtSignal(object)
    edited = pyqtSignal(object, str)
    statusChanged = pyqtSignal(object, bool)
    focusOut = pyqtSignal()
    clicked = pyqtSignal(object)
    
    def __init__(self, text, task_id, is_checked=False, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(is_checked)
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
        self.checkbox.setStyleSheet("""
            QCheckBox {
                padding: 0px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        
        self.text_label = ClickableLineEdit(text)
        self.text_label.setReadOnly(True)
        self.text_label.editingFinished.connect(self.finish_edit)
        self.text_label.focusOutEvent = self.on_focus_out
        self.text_label.setMinimumWidth(350)
        self.text_label.setFixedHeight(24)
        self.text_label.clicked.connect(self.on_text_clicked)
        self.update_style(is_checked)
        
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(4)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        button_style = """
            QPushButton {
                padding: 0px;
                margin: 0px;
                border: none;
                background: transparent;
                width: 24px;
                height: 24px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-radius: 3px;
            }
        """
        
        self.edit_button = QPushButton()
        self.edit_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.edit_button.setIconSize(QSize(14, 14))
        self.edit_button.setToolTip("编辑")
        self.edit_button.clicked.connect(self.toggle_edit)
        self.edit_button.setFixedSize(24, 24)
        self.edit_button.setStyleSheet(button_style)
        
        delete_button_style = button_style + """
            QPushButton {
                color: #ff4d4d;
            }
            QPushButton:hover {
                background-color: #ffe6e6;
            }
        """
        self.delete_button = QPushButton()
        self.delete_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.delete_button.setIconSize(QSize(14, 14))
        self.delete_button.setToolTip("删除")
        self.delete_button.clicked.connect(self.delete_task)
        self.delete_button.setFixedSize(24, 24)
        self.delete_button.setStyleSheet(delete_button_style)
        
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.text_label, 1)
        layout.addWidget(button_container, 0)
        
        self.setFixedHeight(32)
    
    def toggle_edit(self):
        if self.text_label.isReadOnly():
            self.text_label.setReadOnly(False)
            self.text_label.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #4a90e2;
                    background: white;
                    padding: 0px 2px;
                    font-size: 12px;
                    height: 20px;
                }
            """)
            self.text_label.setFocus()
        else:
            self.text_label.setReadOnly(True)
            self.update_style(self.checkbox.isChecked())
            self.edited.emit(self.listWidgetItem, self.text_label.text())
    
    def update_style(self, is_checked):
        # 基础文本样式
        base_style = """
            QLineEdit {
                border: none;
                background: transparent;
                padding: 2px 4px;
                margin: 0px;
                font-size: 13px;
                height: 24px;
                line-height: 24px;
            }
        """
        
        if is_checked:
            # 任务完成时的样式
            self.setStyleSheet("""
                QWidget {
                    background-color: #e8f5e9;
                }
            """)
            self.text_label.setStyleSheet(base_style + """
                QLineEdit {
                    text-decoration: line-through;
                    color: #2ecc71;
                }
            """)
        else:
            # 任务未完成时的样式
            self.setStyleSheet("")
            self.text_label.setStyleSheet(base_style + """
                QLineEdit {
                    color: black;
                }
            """)
    
    def delete_task(self):
        self.deleted.emit(self.listWidgetItem)
        
    def on_checkbox_changed(self, state):
        """复选框状态改变时触发"""
        is_checked = bool(state)  # 直接转换为布尔值，因为我们只关心是否选中
        self.update_style(is_checked)  # 立即更新样式
        self.statusChanged.emit(self.listWidgetItem, is_checked)
        # 触发选中事件
        self.clicked.emit(self.listWidgetItem)
    
    def on_text_clicked(self):
        """文本框被点击时触发"""
        if self.text_label.isReadOnly():
            self.clicked.emit(self.listWidgetItem)
    
    def on_focus_out(self, event):
        if not self.text_label.isReadOnly():
            self.finish_edit()
        self.focusOut.emit()
        super(QLineEdit, self.text_label).focusOutEvent(event)
    
    def finish_edit(self):
        if not self.text_label.isReadOnly():
            self.toggle_edit()
    
    def edit_task(self, item, new_text):
        widget = self.task_list.itemWidget(item)
        if widget:
            # 更新任务文本和修改时间
            for task in self.tasks_data["tasks"]:
                if task["id"] == widget.task_id:
                    task["text"] = new_text
                    task["updated_at"] = self.get_current_time()
                    break
            widget.text_label.setText(new_text)
            self.save_tasks()

class AITodoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Todo List")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QPushButton {
                padding: 8px;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                padding: 8px;
            }
        """)
        
        # 加载配置
        with open('config.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.tasks_file = 'tasks.json'
        self.tasks_data = self.load_tasks()
        
        self.current_task = None
        self.next_task_id = 1
        
        self.init_ui()
        self.load_tasks_to_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # 左侧布局：任务列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("输入新任务...")
        self.add_button = QPushButton("添加")
        self.add_button.clicked.connect(self.add_task)
        
        self.task_list = QListWidget()
        self.task_list.setSpacing(1)
        self.task_list.setAlternatingRowColors(True)
        self.task_list.itemClicked.connect(self.show_subtasks)
        self.task_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_list.customContextMenuRequested.connect(self.show_context_menu)
        self.task_list.setMinimumWidth(500)
        self.task_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                padding: 1px;
            }
            QListWidget::item {
                padding: 1px;
                margin: 1px;
                min-height: 32px;
            }
            QListWidget::item:alternate {
                background-color: #f8f9fa;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                border-radius: 4px;
                border: 1px solid #90caf9;  /* 添加边框 */
                color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
                border-radius: 4px;
            }
        """)
        
        # Adjust the layout to display task_input and add_button horizontally
        task_input_layout = QHBoxLayout()
        task_input_layout.addWidget(self.task_input)
        task_input_layout.addWidget(self.add_button)
        left_layout.addLayout(task_input_layout)
        
        left_layout.addWidget(self.task_list)
        
        # 右侧布局：子任务详情
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 任务信息区域
        self.task_info_area = QTextEdit()
        self.task_info_area.setReadOnly(True)
        self.task_info_area.setMaximumHeight(56)
        self.task_info_area.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                padding: 8px;
            }
        """)
        
        # 子任务列表
        self.subtasks_list = QListWidget()
        self.subtasks_list.setAlternatingRowColors(True)
        self.subtasks_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                padding: 1px;
            }
            QListWidget::item {
                padding: 1px;
                margin: 1px;
                min-height: 32px;
            }
            QListWidget::item:alternate {
                background-color: #f8f9fa;
            }
        """)
        
        # 子任务输入区域
        subtask_input_widget = QWidget()
        subtask_input_layout = QHBoxLayout(subtask_input_widget)
        subtask_input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.subtask_input = QLineEdit()
        self.subtask_input.setPlaceholderText("输入新子任务...")
        self.subtask_input.returnPressed.connect(self.add_subtask)
        
        self.add_subtask_button = QPushButton("添加")
        self.add_subtask_button.clicked.connect(self.add_subtask)
        
        subtask_input_layout.addWidget(self.subtask_input)
        subtask_input_layout.addWidget(self.add_subtask_button)
        
        self.generate_button = QPushButton("AI生成子任务")
        self.generate_button.clicked.connect(self.generate_subtasks)
        
        right_layout.addWidget(self.task_info_area)
        right_layout.addWidget(self.subtasks_list)
        right_layout.addWidget(subtask_input_widget)
        right_layout.addWidget(self.generate_button)
        
        # 添加左右布局
        layout.addWidget(left_widget)
        layout.addWidget(right_widget)
    
    def load_tasks(self):
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"tasks": []}
    
    def save_tasks(self):
        """保任务到文件"""
        self.tasks_data["tasks"] = self.clean_data_for_save()
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks_data, f, ensure_ascii=False, indent=2)
    
    def add_task(self):
        task_text = self.task_input.text().strip()
        if task_text:
            current_time = self.get_current_time()
            item = QListWidgetItem(self.task_list)
            task_id = self.get_next_task_id()
            task_widget = TaskItem(task_text, task_id)
            item.setSizeHint(task_widget.sizeHint())
            task_widget.listWidgetItem = item
            
            # 连接所有信号
            task_widget.deleted.connect(self.delete_task)
            task_widget.edited.connect(self.edit_task)
            task_widget.statusChanged.connect(self.update_task_status)
            task_widget.focusOut.connect(self.save_tasks)
            task_widget.clicked.connect(self.show_subtasks)
            
            # 新的任务数据结构
            task_data = {
                "id": task_id,
                "text": task_text,
                "completed": False,
                "hidden": False,
                "created_at": current_time,
                "updated_at": current_time,
                "subtasks": []  # 子任务列表，每个子任务都是完整的任务数据结构
            }
            self.tasks_data["tasks"].append(task_data)
            
            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, task_widget)
            self.task_input.clear()
            self.save_tasks()
    
    def delete_task(self, item):
        row = self.task_list.row(item)
        widget = self.task_list.itemWidget(item)
        task_id = widget.task_id
        
        # 更新任务状态为隐藏
        for task in self.tasks_data["tasks"]:
            if task["id"] == task_id:
                task["hidden"] = True
                task["updated_at"] = self.get_current_time()
                break
        
        # 从列表中移除显示
        self.task_list.takeItem(row)
        
        # 清除当前选中状态
        if self.current_task == item:
            self.current_task = None
            self.subtasks_area.clear()
        
        # 保存更改
        self.save_tasks()
    
    def edit_task(self, item, new_text):
        widget = self.task_list.itemWidget(item)
        if widget:
            # 更新任务文本和修改时间
            for task in self.tasks_data["tasks"]:
                if task["id"] == widget.task_id:
                    task["text"] = new_text
                    task["updated_at"] = self.get_current_time()
                    break
            widget.text_label.setText(new_text)
            self.save_tasks()
    
    def update_task_status(self, item, is_checked):
        widget = self.task_list.itemWidget(item)
        if widget:
            # 更新UI样式
            widget.update_style(is_checked)

            # 更新任务状态
            task_id = widget.task_id
            for task in self.tasks_data["tasks"]:
                if task["id"] == task_id:
                    task["completed"] = is_checked
                    task["updated_at"] = self.get_current_time()
                    break
            
            # 强制刷新列表项
            self.task_list.update(self.task_list.indexFromItem(item))
            
            # 更新子任务显示
            if self.current_task == item:
                self.show_subtasks(item)
            
            # 保存更改
            self.save_tasks()
    
    def show_context_menu(self, position):
        item = self.task_list.itemAt(position)
        if item:
            menu = QMenu()
            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self.delete_task(item))
            menu.addAction(delete_action)
            menu.exec(self.task_list.viewport().mapToGlobal(position))

    def show_subtasks(self, item):
        """当点击任务时触发"""
        # 检查是否是主任务列表中的项目
        if item.listWidget() != self.task_list:
            return
            
        self.current_task = item
        self.task_list.setCurrentItem(item)
        widget = self.task_list.itemWidget(item)
        
        # 获取当前任务数据
        task_id = widget.task_id
        task_data = next((t for t in self.tasks_data["tasks"] if t["id"] == task_id), None)
        
        if task_data:
            # 显示任务信息
            info_text = (f"任务名称：{task_data['text']}\n"
                        f"创建时间：{task_data['created_at']}\t"
                        f"修改时间：{task_data['updated_at']}")
            self.task_info_area.setText(info_text)
            
            # 清空并重新显示子任务
            self.subtasks_list.clear()
            for subtask in task_data.get("subtasks", []):
                if subtask and not subtask.get("hidden", False):
                    item = QListWidgetItem(self.subtasks_list)
                    subtask_widget = TaskItem(subtask["text"], subtask["id"], 
                                            subtask.get("completed", False))
                    item.setSizeHint(subtask_widget.sizeHint())
                    subtask_widget.listWidgetItem = item
                    
                    # 直接连接信号，不使用 lambda 或 partial
                    subtask_widget.deleted.connect(self.delete_subtask)
                    subtask_widget.edited.connect(self.edit_subtask)
                    subtask_widget.statusChanged.connect(self.update_subtask_status)
                    subtask_widget.focusOut.connect(self.save_tasks)
                    
                    self.subtasks_list.addItem(item)
                    self.subtasks_list.setItemWidget(item, subtask_widget)
    
    def generate_subtasks(self):
        if not self.current_task:
            QMessageBox.warning(self, "警告", "请先选择一个任务！")
            return
            
        task_widget = self.task_list.itemWidget(self.current_task)
        task_text = task_widget.text_label.text()
        
        # 获取当前任务的现有子任务
        task_id = task_widget.task_id
        task_data = next((t for t in self.tasks_data["tasks"] if t["id"] == task_id), None)
        existing_subtasks = task_data.get("subtasks", []) if task_data else []
        
        try:
            # 调用DeepSeek API
            headers = {
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": f"请将这个任务拆分成具体的子任务步骤（用数字编号）：{task_text}"
                    }
                ],
                "temperature": 0.7
            }
            
            response = requests.post(
                self.config['api_endpoint'],
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            subtasks = result['choices'][0]['message']['content']
            
            # 解析新生成的子任务，并转换为正确的数据结构
            current_time = self.get_current_time()
            new_subtasks = []
            for subtask_text in [s.strip() for s in subtasks.split('\n') if s.strip()]:
                subtask_data = {
                    "id": self.get_next_task_id(),
                    "text": subtask_text,
                    "completed": False,
                    "hidden": False,
                    "created_at": current_time,
                    "updated_at": current_time
                }
                new_subtasks.append(subtask_data)
            
            # 合并现有子任务和新子任务
            updated_subtasks = existing_subtasks + new_subtasks if existing_subtasks else new_subtasks
            
            # 更新数据和显示
            for task in self.tasks_data["tasks"]:
                if task["id"] == task_id:
                    task["subtasks"] = updated_subtasks
                    task["updated_at"] = current_time
                    break
            
            # 保存并更新显示
            self.save_tasks()
            self.show_subtasks(self.current_task)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成子任务失败：{str(e)}")
    
    def load_tasks_to_ui(self):
        """从tasks.json加载任务到界面"""
        for task_data in self.tasks_data.get("tasks", []):
            # 只加载未隐藏的任务
            if not task_data.get("hidden", False):
                item = QListWidgetItem(self.task_list)
                task_id = task_data.get("id", self.get_next_task_id())
                task_widget = TaskItem(task_data["text"], task_id, task_data.get("completed", False))
                item.setSizeHint(task_widget.sizeHint())
                task_widget.listWidgetItem = item
                task_widget.deleted.connect(self.delete_task)
                task_widget.edited.connect(self.edit_task)
                task_widget.statusChanged.connect(self.update_task_status)
                task_widget.focusOut.connect(self.save_tasks)
                task_widget.clicked.connect(self.show_subtasks)
                self.task_list.addItem(item)
                self.task_list.setItemWidget(item, task_widget)
                
                # 更新next_task_id
                self.next_task_id = max(self.next_task_id, task_id + 1)
    
    def get_next_task_id(self):
        """获取下一个可用的任务ID"""
        current_id = self.next_task_id
        self.next_task_id += 1
        return current_id
    
    def get_current_time(self):
        """获取当前时间的格式化字符串"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def add_subtask(self):
        """手动添加子任务"""
        if not self.current_task:
            QMessageBox.warning(self, "警告", "请先选择一个任务！")
            return
            
        subtask_text = self.subtask_input.text().strip()
        if not subtask_text:
            return
            
        current_time = self.get_current_time()
        subtask_id = self.get_next_task_id()
        
        # 创建新的子任务数据
        subtask_data = {
            "id": subtask_id,
            "text": subtask_text,
            "completed": False,
            "hidden": False,
            "created_at": current_time,
            "updated_at": current_time
        }
        
        # 添加到主任务的子任务列表中
        task_widget = self.task_list.itemWidget(self.current_task)
        task_id = task_widget.task_id
        for task in self.tasks_data["tasks"]:
            if task["id"] == task_id:
                task["subtasks"].append(subtask_data)
                task["updated_at"] = current_time
                break
        
        # 更新显示
        self.save_tasks()
        self.show_subtasks(self.current_task)
        self.subtask_input.clear()

    def update_subtask_status(self, item, is_checked):
        """更新子任务状态"""
        if not self.current_task:
            return
            
        # 获取 TaskItem 部件
        subtask_widget = self.subtasks_list.itemWidget(item)
        if subtask_widget:
            task_widget = self.task_list.itemWidget(self.current_task)
            task_id = task_widget.task_id
            subtask_id = subtask_widget.task_id
            
            # 更新数据结构中的状态
            for task in self.tasks_data["tasks"]:
                if task["id"] == task_id:
                    for subtask in task["subtasks"]:
                        if subtask["id"] == subtask_id:
                            subtask["completed"] = is_checked
                            subtask["updated_at"] = self.get_current_time()
                            break
                    task["updated_at"] = self.get_current_time()
                    break
            
            # 更新UI显示
            subtask_widget.update_style(is_checked)
            self.save_tasks()
            self.update_task_info()

    def delete_subtask(self, item):
        """删除（隐藏）子任务"""
        if not self.current_task:
            return
            
        # 获取 TaskItem 部件
        subtask_widget = self.subtasks_list.itemWidget(item)
        if subtask_widget:
            task_widget = self.task_list.itemWidget(self.current_task)
            task_id = task_widget.task_id
            subtask_id = subtask_widget.task_id
            
            # 更新数据
            for task in self.tasks_data["tasks"]:
                if task["id"] == task_id:
                    for subtask in task["subtasks"]:
                        if subtask["id"] == subtask_id:
                            subtask["hidden"] = True
                            subtask["updated_at"] = self.get_current_time()
                            break
                    task["updated_at"] = self.get_current_time()
                    break
            
            # 更新UI
            self.save_tasks()
            self.show_subtasks(self.current_task)

    def edit_subtask(self, item, new_text):
        """编辑子任务"""
        if not self.current_task:
            return
            
        # 获取 TaskItem 部件
        subtask_widget = self.subtasks_list.itemWidget(item)
        if subtask_widget:
            task_widget = self.task_list.itemWidget(self.current_task)
            task_id = task_widget.task_id
            subtask_id = subtask_widget.task_id
            
            # 更新数据
            for task in self.tasks_data["tasks"]:
                if task["id"] == task_id:
                    for subtask in task["subtasks"]:
                        if subtask["id"] == subtask_id:
                            subtask["text"] = new_text
                            subtask["updated_at"] = self.get_current_time()
                            break
                    task["updated_at"] = self.get_current_time()
                    break
            
            # 更新UI
            subtask_widget.text_label.setText(new_text)
            subtask_widget.update_style(subtask_widget.checkbox.isChecked())
            self.save_tasks()

    def clean_data_for_save(self):
        """清理数据，确保只保存基本数据类型"""
        clean_tasks = []
        for task in self.tasks_data["tasks"]:
            clean_task = {
                "id": task["id"],
                "text": task["text"],
                "completed": task.get("completed", False),
                "hidden": task.get("hidden", False),
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
                "subtasks": []
            }
            
            for subtask in task.get("subtasks", []):
                if isinstance(subtask, dict):
                    clean_subtask = {
                        "id": subtask["id"],
                        "text": subtask["text"],
                        "completed": subtask.get("completed", False),
                        "hidden": subtask.get("hidden", False),
                        "created_at": subtask.get("created_at", self.get_current_time()),
                        "updated_at": subtask.get("updated_at", self.get_current_time())
                    }
                    clean_task["subtasks"].append(clean_subtask)
            
            clean_tasks.append(clean_task)
        return clean_tasks

    def update_task_info(self):
        """更新右侧的主任务信息"""
        if self.current_task:
            task_widget = self.task_list.itemWidget(self.current_task)
            task_id = task_widget.task_id
            task_data = next((t for t in self.tasks_data["tasks"] if t["id"] == task_id), None)
            
            if task_data:
                info_text = (f"任务名称：{task_data['text']}\n"
                            f"创建时间：{task_data['created_at']}\t"
                            f"修改时间：{task_data['updated_at']}")
                self.task_info_area.setText(info_text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AITodoApp()
    window.show()
    # PyQt6 中使用 exec 而不是 exec_
    sys.exit(app.exec()) 