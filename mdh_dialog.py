#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QLabel,
    QSplitter,
    QWidget,
    QGroupBox,
    QFileDialog,
    QMessageBox,
    QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter

from codegen import forward_kinematics, dynamic_base_regressor, jacobian
from translations import tr

import re


class CppSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for C/C++ code"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Define highlighting rules
        self.highlighting_rules = []
        
        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(86, 156, 214))  # Blue
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            'auto', 'break', 'case', 'char', 'const', 'continue', 'default',
            'do', 'double', 'else', 'enum', 'extern', 'float', 'for', 'goto',
            'if', 'inline', 'int', 'long', 'register', 'restrict', 'return',
            'short', 'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef',
            'union', 'unsigned', 'void', 'volatile', 'while', 'class', 'namespace',
            'template', 'public', 'private', 'protected', 'using', 'virtual',
            'override', 'final', 'nullptr', 'new', 'delete', 'try', 'catch',
            'throw', 'bool', 'true', 'false', 'std'
        ]
        for keyword in keywords:
            pattern = r'\b' + keyword + r'\b'
            self.highlighting_rules.append((pattern, keyword_format))
        
        # Class names
        class_format = QTextCharFormat()
        class_format.setForeground(QColor(78, 201, 176))  # Cyan
        class_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r'\bclass\s+\w+', class_format))
        
        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor(220, 220, 170))  # Yellow
        self.highlighting_rules.append((r'\b[A-Za-z0-9_]+(?=\()', function_format))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(181, 206, 168))  # Light green
        self.highlighting_rules.append((r'\b[0-9]+\.?[0-9]*[fFlL]?\b', number_format))
        
        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(214, 157, 133))  # Orange
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))
        
        # Single line comments
        single_comment_format = QTextCharFormat()
        single_comment_format.setForeground(QColor(106, 153, 85))  # Green
        self.highlighting_rules.append((r'//[^\n]*', single_comment_format))
        
        # Multi-line comments
        self.multi_line_comment_format = QTextCharFormat()
        self.multi_line_comment_format.setForeground(QColor(106, 153, 85))  # Green
        
        # Preprocessor
        preprocessor_format = QTextCharFormat()
        preprocessor_format.setForeground(QColor(155, 155, 155))  # Gray
        self.highlighting_rules.append((r'#[^\n]*', preprocessor_format))
        
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text"""
        # Apply single-line rules
        for pattern, format in self.highlighting_rules:
            expression = re.compile(pattern)
            for match in expression.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)
        
        # Handle multi-line comments
        self.setCurrentBlockState(0)
        
        start_expression = re.compile(r'/\*')
        end_expression = re.compile(r'\*/')
        
        start_index = 0
        if self.previousBlockState() != 1:
            match = start_expression.search(text, start_index)
            if match:
                start_index = match.start()
            else:
                start_index = -1
        
        while start_index >= 0:
            match = end_expression.search(text, start_index)
            if match:
                end_index = match.end()
                comment_length = end_index - start_index
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            
            self.setFormat(start_index, comment_length, self.multi_line_comment_format)
            match = start_expression.search(text, start_index + comment_length)
            if match:
                start_index = match.start()
            else:
                start_index = -1


class MDHDialog(QDialog):
    """Dialog for displaying MDH parameters and generating code"""
    
    def __init__(self, parent=None, chain_name="", mdh_parameters=None):
        super().__init__(parent)
        self.chain_name = chain_name
        self.mdh_parameters = mdh_parameters if mdh_parameters else []
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(tr("mdh_title") + f" - {self.chain_name}")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)

        # Main layout
        main_layout = QHBoxLayout(self)

        # Create left panel for MDH parameters
        left_panel = self.create_left_panel()

        # Create right panel for code display
        right_panel = self.create_right_panel()

        # Add panels to main layout with splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])  # Set initial sizes

        main_layout.addWidget(splitter)
        
    def create_left_panel(self):
        """Create the left panel with MDH parameters table and buttons"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Add title
        title_label = QLabel(tr("mdh_parameters"))
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(title_label)

        # Create table for MDH parameters
        self.mdh_table = QTableWidget()
        self.mdh_table.setColumnCount(5)  # Joint, theta, d, a, alpha
        self.mdh_table.setHorizontalHeaderLabels([tr("joint"), tr("theta_rad"), "d", "a", tr("alpha_rad")])
        
        # Set row count
        self.mdh_table.setRowCount(len(self.mdh_parameters))
        
        # Fill table with MDH parameters
        for i, params in enumerate(self.mdh_parameters):
            # Joint name
            joint_item = QTableWidgetItem(f"Joint {i+1}")
            self.mdh_table.setItem(i, 0, joint_item)
            
            # MDH parameters: theta, d, a, alpha
            for j, param in enumerate(params):
                param_item = QTableWidgetItem(f"{param:.4f}")
                self.mdh_table.setItem(i, j+1, param_item)
        
        # Resize columns to content
        self.mdh_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        left_layout.addWidget(self.mdh_table)
        
        # Create buttons
        buttons_layout = QHBoxLayout()

        self.btn_forward_kinematics = QPushButton(tr("forward_kinematics"))
        self.btn_forward_kinematics.clicked.connect(self.on_forward_kinematics)

        self.btn_jacobian = QPushButton(tr("jacobian"))
        self.btn_jacobian.clicked.connect(self.on_jacobian)

        self.btn_dynamic_base_regressor = QPushButton(tr("dynamic_base_regressor"))
        self.btn_dynamic_base_regressor.clicked.connect(self.on_dynamic_base_regressor)

        self.btn_save_mdh = QPushButton(tr("save_mdh"))
        self.btn_save_mdh.clicked.connect(self.on_save_mdh)
        
        buttons_layout.addWidget(self.btn_forward_kinematics)
        buttons_layout.addWidget(self.btn_jacobian)
        buttons_layout.addWidget(self.btn_dynamic_base_regressor)

        buttons_layout.addWidget(self.btn_save_mdh)
        
        left_layout.addLayout(buttons_layout)
        
        return left_widget
    
    def create_right_panel(self):
        """Create the right panel with header and cpp file display areas"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Create splitter for top and bottom sections
        vertical_splitter = QSplitter(Qt.Vertical)

        # Top section for .h header file
        header_group = QGroupBox(tr("header_file_or_python_usage"))

        header_layout = QVBoxLayout(header_group)

        # Add copy button for header
        header_button_layout = QHBoxLayout()
        self.btn_copy_header = QPushButton(tr("copy"))
        self.btn_copy_header.clicked.connect(self.on_copy_header)
        header_button_layout.addWidget(self.btn_copy_header)
        header_button_layout.addStretch()
        header_layout.addLayout(header_button_layout)

        self.header_text_edit = QTextEdit()
        self.header_text_edit.setReadOnly(True)
        self.header_text_edit.setPlaceholderText(tr("header_placeholder"))
        # Set monospace font for code
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.Monospace)
        self.header_text_edit.setFont(font)
        # Add syntax highlighter
        self.header_highlighter = CppSyntaxHighlighter(self.header_text_edit.document())
        header_layout.addWidget(self.header_text_edit)

        # Bottom section for .cpp file
        cpp_group = QGroupBox(tr("cpp_source_file"))
        cpp_layout = QVBoxLayout(cpp_group)

        # Add copy button for cpp
        cpp_button_layout = QHBoxLayout()
        self.btn_copy_cpp = QPushButton(tr("copy"))
        self.btn_copy_cpp.clicked.connect(self.on_copy_cpp)
        cpp_button_layout.addWidget(self.btn_copy_cpp)
        cpp_button_layout.addStretch()
        cpp_layout.addLayout(cpp_button_layout)

        self.cpp_text_edit = QTextEdit()
        self.cpp_text_edit.setReadOnly(True)
        self.cpp_text_edit.setPlaceholderText(tr("cpp_placeholder"))
        # Set monospace font for code
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.Monospace)
        self.cpp_text_edit.setFont(font)
        # Add syntax highlighter
        self.cpp_highlighter = CppSyntaxHighlighter(self.cpp_text_edit.document())
        cpp_layout.addWidget(self.cpp_text_edit)
        
        # Add both sections to vertical splitter
        vertical_splitter.addWidget(header_group)
        vertical_splitter.addWidget(cpp_group)
        vertical_splitter.setSizes([300, 300])  # Equal split
        
        right_layout.addWidget(vertical_splitter)
        
        return right_widget
    
    def on_forward_kinematics(self):
        """Handle Forward Kinematics button click"""
        # TODO: Implement forward kinematics calculation and code generation
        print("Forward Kinematics button clicked")
        # For now, just show placeholder text
        
        fk = forward_kinematics.FK_SYM(self.mdh_parameters)
        fk_code, fk_header = fk.gencpp()
        
        
        self.header_text_edit.setText(fk_header)
        self.cpp_text_edit.setText(fk_code)
    
    def on_jacobian(self):
        """Handle Jacobian button click"""
        # TODO: Implement Jacobian calculation and code generation
        print("Jacobian button clicked")
        # For now, just show placeholder text
        
        jac = jacobian.JAC_SYM(self.mdh_parameters)
        jac_code, jac_header = jac.gencpp()
        self.header_text_edit.setText(jac_header)
        self.cpp_text_edit.setText(jac_code)
        
    def on_dynamic_base_regressor(self):
        """Handle Dynamic Base Regressor button click"""
        # TODO: Implement Dynamic Base Regressor calculation and code generation
        print("Dynamic Base Regressor button clicked")
        
        code, base_idxs = dynamic_base_regressor.create_gx7(self.mdh_parameters)
        # For now, just show placeholder text
        self.header_text_edit.setText(f'{base_idxs}')
        self.cpp_text_edit.setText(code)

    
    def update_mdh_parameters(self, mdh_parameters):
        """Update the MDH parameters in the table"""
        self.mdh_parameters = mdh_parameters

        # Update table row count
        self.mdh_table.setRowCount(len(self.mdh_parameters))

        # Fill table with new MDH parameters
        for i, params in enumerate(self.mdh_parameters):
            # Joint name
            joint_item = QTableWidgetItem(tr("joint") + f" {i+1}")
            self.mdh_table.setItem(i, 0, joint_item)

            # MDH parameters: theta, d, a, alpha
            for j, param in enumerate(params):
                param_item = QTableWidgetItem(f"{param:.4f}")
                self.mdh_table.setItem(i, j+1, param_item)

    def on_save_mdh(self):
        """Save MDH parameters to a text file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("dialog_save_mdh"),
            f"{self.chain_name}_mdh_parameters.txt",
            tr("dialog_text_files")
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    # Write header
                    f.write(tr("mdh_file_header", self.chain_name) + "\n")
                    f.write("=" * 50 + "\n\n")

                    # Write column headers
                    f.write(f"{tr('joint'):<10} {tr('theta_rad'):<12} {'d':<12} {'a':<12} {tr('alpha_rad'):<12}\n")
                    f.write("-" * 60 + "\n")

                    # Write MDH parameters
                    for i, params in enumerate(self.mdh_parameters):
                        joint_name = f"Joint {i+1}"
                        theta, d, a, alpha = params
                        f.write(f"{joint_name:<10} {theta:<4.8f} {d:<4.8f} {a:<4.8f} {alpha:<4.8f}\n")

                    f.write("\n" + "=" * 50 + "\n")
                    f.write(tr("mdh_total_joints", len(self.mdh_parameters)) + "\n")

                QMessageBox.information(self, tr("success"), tr("mdh_saved", file_path))
            except Exception as e:
                QMessageBox.critical(self, tr("error"), tr("failed_to_save_mdh", str(e)))

    def on_copy_header(self):
        """Copy header code to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.header_text_edit.toPlainText())
        QMessageBox.information(self, tr("copied"), tr("header_copied"))

    def on_copy_cpp(self):
        """Copy source code to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.cpp_text_edit.toPlainText())
        QMessageBox.information(self, tr("copied"), tr("source_copied"))
