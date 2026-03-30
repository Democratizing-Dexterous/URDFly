#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import tempfile
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QLabel,
    QSplitter,
    QShortcut,
    QDesktopWidget,
    QLineEdit,
    QSpinBox
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QRegExp
import math
from PyQt5.QtGui import QFont, QKeySequence, QTextCharFormat, QColor, QSyntaxHighlighter, QTextCursor, QTextDocument
from translations import tr


class XMLHighlighter(QSyntaxHighlighter):
    """XML syntax highlighter for the editor"""
    
    # Define states for multi-line constructs
    NORMAL_STATE = 0
    IN_COMMENT = 1
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.highlighting_rules = []
        
        # XML tags
        tag_format = QTextCharFormat()
        tag_format.setForeground(QColor("#0000FF"))  # Blue
        tag_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r'<[/]?[a-zA-Z0-9_]+[^>]*>', tag_format))
        
        # XML attributes
        attribute_format = QTextCharFormat()
        attribute_format.setForeground(QColor("#FF0000"))  # Red
        self.highlighting_rules.append((r'[a-zA-Z0-9_]+(?=\s*=)', attribute_format))
        
        # XML attribute values
        value_format = QTextCharFormat()
        value_format.setForeground(QColor("#008000"))  # Green
        self.highlighting_rules.append((r'"[^"]*"', value_format))
        self.highlighting_rules.append((r"'[^']*'", value_format))
        
        # XML comment format
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#808080"))  # Gray
        self.comment_format.setFontItalic(True)
    
    def highlightBlock(self, text):
        import re
        
        # First apply single-line rules (tags, attributes, values)
        for pattern, format in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                start = match.start()
                length = match.end() - match.start()
                self.setFormat(start, length, format)
        
        # Handle multi-line comments
        self.setCurrentBlockState(self.NORMAL_STATE)
        
        # Check if we're continuing a comment from the previous block
        start_index = 0
        if self.previousBlockState() == self.IN_COMMENT:
            start_index = 0
        else:
            # Look for comment start
            start_match = re.search(r'<!--', text)
            if start_match:
                start_index = start_match.start()
            else:
                start_index = -1
        
        # Process comments
        while start_index >= 0:
            # Look for comment end
            end_match = re.search(r'-->', text[start_index:])
            
            if end_match:
                # Found end of comment
                end_index = start_index + end_match.end()
                comment_length = end_index - start_index
                self.setFormat(start_index, comment_length, self.comment_format)
                
                # Look for next comment start
                next_start = re.search(r'<!--', text[end_index:])
                if next_start:
                    start_index = end_index + next_start.start()
                else:
                    start_index = -1
            else:
                # Comment continues to next block
                self.setCurrentBlockState(self.IN_COMMENT)
                comment_length = len(text) - start_index
                self.setFormat(start_index, comment_length, self.comment_format)
                break



class XMLEditor(QMainWindow):
    """XML Editor window for editing URDF files"""
    
    def __init__(self, file_path=None, update_callback=None):
        super().__init__()
        self.file_path = file_path
        self.update_callback = update_callback
        # Initialize search variables
        self.last_search_text = ""
        self.last_search_position = 0
        self.init_ui()
        
        if file_path:
            self.load_file(file_path)
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(tr("urdf_editor"))
        # Set window size
        window_width = 1200
        window_height = 800
        
        # Get screen size and calculate center position
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - window_width) // 2 - window_width // 2
        y = (screen.height() - window_height) // 2
        
        # Set window geometry to be centered on screen
        self.setGeometry(x, y, window_width, window_height)
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()

        # Create save as button
        self.btn_save_as = QPushButton(tr("save_as"))
        self.btn_save_as.clicked.connect(self.save_file_as)
        toolbar_layout.addWidget(self.btn_save_as)

        # Create update button
        self.btn_update = QPushButton(tr("update"))
        self.btn_update.clicked.connect(self.update_model)
        self.btn_update.setToolTip(tr("update_tooltip"))
        toolbar_layout.addWidget(self.btn_update)
        
        # Add spacer to push the file path label to the right
        toolbar_layout.addStretch()
        
        # Create file path label
        self.file_path_label = QLabel()
        toolbar_layout.addWidget(self.file_path_label)
        
        # Add toolbar to main layout
        main_layout.addLayout(toolbar_layout)
        
        # Create search bar layout
        search_layout = QHBoxLayout()

        # Create search label
        search_label = QLabel(tr("search"))
        search_layout.addWidget(search_label)

        # Create search input field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("search_placeholder"))
        self.search_input.returnPressed.connect(self.find_next)
        search_layout.addWidget(self.search_input)

        # Create previous button
        self.btn_prev = QPushButton(tr("previous"))
        self.btn_prev.clicked.connect(self.find_previous)
        self.btn_prev.setToolTip(tr("previous_tooltip"))
        search_layout.addWidget(self.btn_prev)

        # Create next button
        self.btn_next = QPushButton(tr("next"))
        self.btn_next.clicked.connect(self.find_next)
        self.btn_next.setToolTip(tr("next_tooltip"))
        search_layout.addWidget(self.btn_next)
        
        # Add search layout to main layout
        main_layout.addLayout(search_layout)
        
        # Create auto-fill layout
        autofill_layout = QHBoxLayout()
        
        # Create pi buttons
        self.btn_pi = QPushButton("π")
        self.btn_pi.clicked.connect(lambda: self.insert_pi_value(math.pi))
        self.btn_pi.setToolTip(tr("pi_tooltip"))
        autofill_layout.addWidget(self.btn_pi)

        self.btn_pi_half = QPushButton("π/2")
        self.btn_pi_half.clicked.connect(lambda: self.insert_pi_value(math.pi/2))
        self.btn_pi_half.setToolTip(tr("pi_half_tooltip"))
        autofill_layout.addWidget(self.btn_pi_half)

        self.btn_pi_quarter = QPushButton("π/4")
        self.btn_pi_quarter.clicked.connect(lambda: self.insert_pi_value(math.pi/4))
        self.btn_pi_quarter.setToolTip(tr("pi_quarter_tooltip"))
        autofill_layout.addWidget(self.btn_pi_quarter)
        
        # Add precision label and spinbox
        precision_label = QLabel(tr("precision"))
        autofill_layout.addWidget(precision_label)
        
        self.precision_spinbox = QSpinBox()
        self.precision_spinbox.setMinimum(1)
        self.precision_spinbox.setMaximum(15)
        self.precision_spinbox.setValue(6)  # Default precision is 6
        self.precision_spinbox.setToolTip(tr("precision_tooltip"))
        autofill_layout.addWidget(self.precision_spinbox)
        
        # Add spacer to push everything to the left
        autofill_layout.addStretch()
        
        # Add auto-fill layout to main layout
        main_layout.addLayout(autofill_layout)
        
        # Create text editor
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Courier New", 10))
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)
        
        # Apply syntax highlighting
        self.highlighter = XMLHighlighter(self.text_edit.document())
        
        # Add text editor to main layout
        main_layout.addWidget(self.text_edit)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Create keyboard shortcuts
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_file_as)
        
        # Create search shortcuts
        self.shortcut_find_next = QShortcut(QKeySequence("F3"), self)
        self.shortcut_find_next.activated.connect(self.find_next)
        
        self.shortcut_find_prev = QShortcut(QKeySequence("Shift+F3"), self)
        self.shortcut_find_prev.activated.connect(self.find_previous)
        
        # Update file path label
        self.update_file_path_label()
    
    def load_file(self, file_path):
        """Load a file into the editor"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                self.text_edit.setText(content)
                self.file_path = file_path
                self.update_file_path_label()
        except Exception as e:
            QMessageBox.critical(self, tr("error"), tr("failed_to_load_file", str(e)))

    def save_file(self):
        """Save the current file"""
        if not self.file_path:
            self.save_file_as()
            return

        try:
            with open(self.file_path, 'w', encoding='utf-8') as file:
                content = self.text_edit.toPlainText()
                file.write(content)
            QMessageBox.information(self, tr("success"), tr("file_saved_successfully"))
        except Exception as e:
            QMessageBox.critical(self, tr("error"), tr("failed_to_save_file", str(e)))

    def save_file_as(self):
        """Save the current file with a new name"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("dialog_save_file_as"), "", tr("dialog_urdf_filter")
        )

        if file_path:
            self.file_path = file_path
            self.save_file()
            self.update_file_path_label()

    def update_file_path_label(self):
        """Update the file path label"""
        if self.file_path:
            self.file_path_label.setText(self.file_path)
            self.setWindowTitle(tr("urdf_editor") + f" - {os.path.basename(self.file_path)}")
        else:
            self.file_path_label.setText(tr("no_file_loaded"))
            self.setWindowTitle(tr("urdf_editor"))

    def update_model(self):
        """Update the model in the viewer with the current text content"""
        if self.update_callback:
            content = self.text_edit.toPlainText()
            self.update_callback(content)
        else:
            QMessageBox.warning(self, tr("warning"), tr("update_callback_not_set"))
    
    def find_text(self, text, forward=True, start_position=None):
        """Find text in the editor
        
        Args:
            text (str): Text to find
            forward (bool): Search direction, True for forward, False for backward
            start_position (int, optional): Starting position for the search. 
                                           If None, uses the current cursor position.
        
        Returns:
            bool: True if text was found, False otherwise
        """
        if not text:
            return False
        
        # Save the search text for next/previous operations
        self.last_search_text = text
        
        # Get the current cursor
        cursor = self.text_edit.textCursor()
        
        # Set the starting position
        if start_position is not None:
            cursor.setPosition(start_position)
        elif not forward:
            # For backward search, move cursor to the beginning of the current selection
            cursor.setPosition(cursor.selectionStart())
        
        # Create a new cursor for searching
        document = self.text_edit.document()
        find_cursor = QTextCursor(document)
        
        # Set search flags
        flags = QTextDocument.FindFlags()
        if not forward:
            flags |= QTextDocument.FindBackward
        
        # Find the text
        if start_position is not None:
            find_cursor.setPosition(start_position)
            find_cursor = document.find(text, find_cursor, flags)
        else:
            find_cursor = document.find(text, cursor, flags)
        
        # If text was found
        if not find_cursor.isNull():
            # Select the found text
            self.text_edit.setTextCursor(find_cursor)
            # Save the position for next search
            self.last_search_position = find_cursor.position()
            return True
        else:
            # If not found from the current position, try from the beginning/end
            if forward:
                cursor.movePosition(QTextCursor.Start)
            else:
                cursor.movePosition(QTextCursor.End)
            
            find_cursor = document.find(text, cursor, flags)
            
            if not find_cursor.isNull():
                # Select the found text
                self.text_edit.setTextCursor(find_cursor)
                # Save the position for next search
                self.last_search_position = find_cursor.position()
                return True
            else:
                # Text not found
                return False
    
    def find_next(self):
        """Find the next occurrence of the search text"""
        text = self.search_input.text()
        if text:
            # If the search text has changed, start from the beginning
            if text != self.last_search_text:
                self.last_search_position = 0

            # Start from the end of the current selection
            cursor = self.text_edit.textCursor()
            start_pos = cursor.selectionEnd()

            # Find the next occurrence
            found = self.find_text(text, forward=True, start_position=start_pos)

            if not found:
                QMessageBox.information(self, tr("search"), tr("no_more_occurrences"))

    def find_previous(self):
        """Find the previous occurrence of the search text"""
        text = self.search_input.text()
        if text:
            # If the search text has changed, start from the end
            if text != self.last_search_text:
                cursor = self.text_edit.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.last_search_position = cursor.position()

            # Start from the beginning of the current selection
            cursor = self.text_edit.textCursor()
            start_pos = cursor.selectionStart()

            # Find the previous occurrence
            found = self.find_text(text, forward=False, start_position=start_pos)

            if not found:
                QMessageBox.information(self, tr("search"), tr("no_more_occurrences"))
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Accept the close event
        event.accept()
        
    def insert_pi_value(self, value):
        """Insert a pi-related value at the current cursor position with specified precision
        
        Args:
            value (float): The value to insert (pi, pi/2, or pi/4)
        """
        # Get the current precision setting
        precision = self.precision_spinbox.value()
        
        # Format the value with the specified precision
        formatted_value = f"{value:.{precision}f}"
        
        # Insert the formatted value at the current cursor position
        cursor = self.text_edit.textCursor()
        cursor.insertText(formatted_value)
        
    def replace_collision(self):
        """Replace collision mesh filenames by adding '_approx' before the file extension
        
        This function modifies the URDF content by finding all collision mesh filenames
        and adding '_approx' before the file extension. For example:
        "../meshes/Link6.STL" becomes "../meshes/Link6_approx.STL"
            
        Returns:
            str: The modified URDF XML content
        """
        content = self.text_edit.toPlainText()
        import re
        
        # Regular expression to find collision mesh filenames
        # This pattern looks for:
        # 1. <collision> tag
        # 2. Any content until it finds a <mesh> tag with a filename attribute
        # 3. The filename attribute value
        pattern = r'(<collision>.*?<mesh\s+filename=")([^"]+)(".*?</collision>)'
        
        # Function to replace the filename by adding '_approx' before the extension
        def add_approx(match):
            prefix = match.group(1)  # The part before the filename
            filename = match.group(2)  # The filename
            suffix = match.group(3)  # The part after the filename
            
            # Split the filename into base and extension
            import os
            base, ext = os.path.splitext(filename)
            
            # Add '_approx' before the extension
            if '_approx' in base:
                new_filename = base + ext  # Already has '_approx', keep as is
            else:
                new_filename = f"{base}_approx{ext}"
            
            # Return the modified string
            return f"{prefix}{new_filename}{suffix}"
        
        # Replace all occurrences in the content using re.sub with the DOTALL flag
        # to make '.' match newlines as well
        modified_content = re.sub(pattern, add_approx, content, flags=re.DOTALL)
        
        self.text_edit.setPlainText(modified_content)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Get file path from command line arguments
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    editor = XMLEditor(file_path)
    editor.replace_collision()
    editor.show()
    
    sys.exit(app.exec_())
