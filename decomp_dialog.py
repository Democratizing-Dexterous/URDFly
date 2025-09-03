#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QSpinBox,
    QMessageBox,
)
from PySide6.QtCore import Qt
from simplify_mesh import create_detailed_approximation


class DecompDialog(QDialog):
    """Dialog for configuring mesh decomposition parameters"""

    def __init__(self, parent=None, collision_mesh_files=None):
        super().__init__(parent)
        self.collision_mesh_files = collision_mesh_files if collision_mesh_files else []
        self.max_convex_hulls = (
            {}
        )  # Dictionary to store maxConvexHulls values for each mesh file
        self.decomposed_mesh_files = None  # To store the result of decomposition
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Decompose Collision Meshes")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Create table for mesh files and maxConvexHulls values
        self.mesh_table = QTableWidget()
        self.mesh_table.setColumnCount(2)  # Mesh file, maxConvexHulls
        self.mesh_table.setHorizontalHeaderLabels(["Mesh File", "maxConvexHulls"])

        # Set row count
        self.mesh_table.setRowCount(len(self.collision_mesh_files))

        # Fill table with mesh files and default maxConvexHulls values
        for i, mesh_file in enumerate(self.collision_mesh_files):
            # Mesh file name
            file_name = (
                mesh_file.split("/")[-1]
                if "/" in mesh_file
                else mesh_file.split("\\")[-1] if "\\" in mesh_file else mesh_file
            )
            file_item = QTableWidgetItem(file_name)
            file_item.setFlags(
                file_item.flags() & ~Qt.ItemIsEditable
            )  # Make it read-only
            self.mesh_table.setItem(i, 0, file_item)

            # Store the full path in the item's data
            file_item.setData(Qt.UserRole, mesh_file)

            # Create a spin box for maxConvexHulls
            spin_box = QSpinBox()
            spin_box.setMinimum(1)
            spin_box.setMaximum(256)
            spin_box.setValue(32)  # Default value
            spin_box.valueChanged.connect(
                lambda value, row=i: self.on_value_changed(row, value)
            )

            # Store the default value in our dictionary
            self.max_convex_hulls[mesh_file] = 32

            # Add the spin box to the table
            self.mesh_table.setCellWidget(i, 1, spin_box)

        # Set column widths
        self.mesh_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )  # Stretch the mesh file column
        self.mesh_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )  # Fit the maxConvexHulls column to content

        main_layout.addWidget(self.mesh_table)

        # Create buttons at the bottom
        buttons_layout = QHBoxLayout()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self.accept)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_ok)

        main_layout.addLayout(buttons_layout)

    def on_value_changed(self, row, value):
        """Handle changes to maxConvexHulls values"""
        # Get the mesh file path from the table
        mesh_file = self.mesh_table.item(row, 0).data(Qt.UserRole)

        # Update the value in our dictionary
        self.max_convex_hulls[mesh_file] = value

    def get_decomposition_params(self):
        """Get the decomposition parameters"""
        return self.max_convex_hulls

    def perform_decomposition(self):
        """Perform mesh decomposition using the current parameters"""
        try:
            # Create a dictionary mapping each mesh file to its maxConvexHulls value
            decomp_params = {}
            for mesh_file, max_hulls in self.max_convex_hulls.items():
                decomp_params[mesh_file] = max_hulls

            # Process each mesh file with its specific maxConvexHulls value
            all_decomposed_files = []
            for mesh_file, max_hulls in decomp_params.items():
                # Call the decomposition function with the specific parameters for this mesh
                decomposed_files = create_detailed_approximation(
                    [mesh_file], maxConvexHulls=max_hulls
                )
                all_decomposed_files.extend(decomposed_files)

            # Store the result
            self.decomposed_mesh_files = all_decomposed_files

            # Show success message
            QMessageBox.information(
                self,
                "Decomposition Complete",
                f"Successfully decomposed {len(all_decomposed_files)} mesh files.",
            )
        except Exception as e:
            # Show error message if decomposition fails
            QMessageBox.critical(
                self, "Decomposition Error", f"Error during decomposition: {str(e)}"
            )

    def get_decomposed_mesh_files(self):
        """Get the decomposed mesh files"""
        return self.decomposed_mesh_files

    def accept(self):
        """Override accept to return the decomposed mesh files"""
        # If decomposition wasn't performed, show a warning
        if self.decomposed_mesh_files is None:
            self.perform_decomposition()

        super().accept()

    def reject(self):
        """Override reject to return None"""
        self.decomposed_mesh_files = None
        super().reject()

    def exec(self):
        """Override exec to return decomposed mesh files or None"""
        result = super().exec()
        if result == QDialog.Accepted:
            return self.decomposed_mesh_files
        else:
            return None
