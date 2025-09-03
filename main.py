#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import copy
import os
import math
import numpy as np
import tempfile
from math import pi
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QLabel,
    QLineEdit,
    QGridLayout,
    QGroupBox,
    QMessageBox,
    QSlider,
    QTreeWidget,
    QTreeWidgetItem,
    QCheckBox,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QComboBox,
    QScrollArea,
)
from xml_editor import XMLEditor
from mdh_dialog import MDHDialog
from decomp_dialog import DecompDialog
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk

from urdf_parser import URDFParser
from urdf_vtk_model import URDFModel
from simplify_mesh import create_detailed_approximation


class DragDropVTKWidget(QVTKRenderWindowInteractor):
    """Custom VTK widget that supports drag-and-drop of URDF files"""

    def __init__(self, parent=None):
        super().__init__()
        self.parent_viewer = parent
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            # Check if any of the dragged files is a URDF file
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(".urdf"):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(".urdf"):
                        # Load the URDF file
                        if self.parent_viewer:
                            self.parent_viewer.load_urdf_file(file_path)
                        event.acceptProposedAction()
                        return
        event.ignore()


class URDFViewer(QMainWindow):
    """Main application window for URDF viewer"""

    def __init__(self):
        super().__init__()
        self.models = []  # List to store loaded URDF models
        self.models_collision = []
        self.chains = []  # List to store kinematic chains
        self.mdh_frames_actors = []  # List to store MDH frame actors
        self.mdh_text_actors = []  # List to store MDH frame text actors
        self.selected_chain = None  # Currently selected chain
        self.selected_chain_index = 0  # Index of the currently selected chain
        self.current_urdf_file = None  # Path to the currently loaded URDF file
        self.collision_mesh_files = None

        self.joint_sliders = []  # List to store joint angle sliders
        self.joint_values = []  # List to store joint angle values
        self.revolute_joints = []  # List to store revolute joints
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("URDFly")

        # Set window size
        window_width = 1200
        window_height = 800

        # Get screen size and calculate center position
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2

        # Set window geometry to be centered on screen
        self.setGeometry(x, y, window_width, window_height)

        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)

        # Create left panel for controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Create right panel for joint controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Create chain selection combo box
        chain_selection_layout = QVBoxLayout()
        chain_selection_layout.addWidget(QLabel("Select Chain:"))
        self.chain_combo = QComboBox()
        self.chain_combo.currentIndexChanged.connect(self.on_chain_selected)
        chain_selection_layout.addWidget(self.chain_combo)

        # Create link list widget
        chain_selection_layout.addWidget(QLabel("Links:"))
        self.link_list = QListWidget()
        self.link_list.setSelectionMode(QListWidget.SingleSelection)
        self.link_list.itemSelectionChanged.connect(self.on_link_selection_changed)
        chain_selection_layout.addWidget(self.link_list)

        # Create a widget to hold the chain selection layout
        chain_selection_widget = QWidget()
        chain_selection_widget.setLayout(chain_selection_layout)

        # Create button for opening URDF file
        btn_open = QPushButton("Open URDF")
        btn_open.clicked.connect(self.open_urdf_file)

        # Create Edit button
        btn_edit = QPushButton("Edit URDF")
        btn_edit.clicked.connect(self.edit_urdf_file)
        btn_edit.setToolTip("Open the current URDF file in an XML editor")

        # Create MDH button
        btn_mdh = QPushButton("Show MDH Parameters")
        btn_mdh.clicked.connect(self.show_mdh_parameters)

        btn_decomp = QPushButton("Decompose As Collision")
        btn_decomp.clicked.connect(self.decompose_collision_meshes)

        # Create transparency controls
        transparency_group = QGroupBox("")
        transparency_layout = QVBoxLayout()

        # Transparency slider
        transparency_layout.addWidget(QLabel("Transparency:"))
        self.transparency_slider = QSlider(Qt.Horizontal)
        self.transparency_slider.setMinimum(0)
        self.transparency_slider.setMaximum(100)
        self.transparency_slider.setValue(100)  # Default to fully opaque
        self.transparency_slider.setTickPosition(QSlider.TicksBelow)
        self.transparency_slider.setTickInterval(10)
        self.transparency_slider.valueChanged.connect(self.apply_transparency)
        transparency_layout.addWidget(self.transparency_slider)

        transparency_group.setLayout(transparency_layout)

        # Create checkboxes for frame visibility
        visibility_group = QGroupBox("Visibility")
        visibility_layout = QVBoxLayout()

        self.cb_link_frames = QCheckBox("Show Link Frames")
        self.cb_link_frames.setChecked(True)
        self.cb_link_frames.stateChanged.connect(self.toggle_link_frames)

        self.cb_mdh_frames = QCheckBox("Show MDH Frames")
        self.cb_mdh_frames.setChecked(False)
        self.cb_mdh_frames.stateChanged.connect(self.toggle_mdh_frames)

        self.cb_collision = QCheckBox("Show Collision")
        self.cb_collision.setChecked(True)
        self.cb_collision.stateChanged.connect(self.toggle_collision)

        visibility_layout.addWidget(self.cb_link_frames)
        visibility_layout.addWidget(self.cb_mdh_frames)
        visibility_layout.addWidget(self.cb_collision)

        visibility_group.setLayout(visibility_layout)

        # Add widgets to left panel
        left_layout.addWidget(QLabel("Robot Structure:"))
        left_layout.addWidget(chain_selection_widget)
        left_layout.addWidget(btn_open)
        left_layout.addWidget(btn_edit)
        left_layout.addWidget(btn_mdh)
        left_layout.addWidget(btn_decomp)

        left_layout.addWidget(transparency_group)
        left_layout.addWidget(visibility_group)
        left_layout.addStretch()

        # Add current file label at the bottom of left panel
        self.current_file_label = QLabel("Current File: None")
        self.current_file_label.setWordWrap(True)
        self.current_file_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        left_layout.addWidget(self.current_file_label)

        # Set fixed width for left panel
        left_panel.setFixedWidth(300)

        # Create VTK widget for 3D visualization with drag-and-drop support
        self.vtk_widget = DragDropVTKWidget(self)

        # Create a scroll area for joint controls
        joint_scroll_area = QScrollArea()
        joint_scroll_area.setWidgetResizable(True)
        joint_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        joint_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Create a widget to hold all joint controls
        self.joint_container = QWidget()
        self.joint_layout = QVBoxLayout(self.joint_container)

        # Add a label explaining the sliders
        joint_label = QLabel("Adjust joint angles:")
        self.joint_layout.addWidget(joint_label)

        # We'll add sliders dynamically when a URDF is loaded

        # Set the container as the scroll area's widget
        joint_scroll_area.setWidget(self.joint_container)

        # Create a group box to contain the scroll area
        joint_group = QGroupBox("Joints Control")
        joint_group_layout = QVBoxLayout(joint_group)

        # Add reset and random buttons
        buttons_layout = QHBoxLayout()
        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self.reset_joints)
        btn_random = QPushButton("Random")
        btn_random.clicked.connect(self.randomize_joints)
        buttons_layout.addWidget(btn_reset)
        buttons_layout.addWidget(btn_random)
        joint_group_layout.addLayout(buttons_layout)

        joint_group_layout.addWidget(joint_scroll_area)

        # Add joint group to right panel
        right_layout.addWidget(joint_group, 1)  # Give it a stretch factor of 1

        # Set fixed width for right panel
        right_panel.setFixedWidth(300)

        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.vtk_widget, 1)
        main_layout.addWidget(right_panel)

        # Set central widget
        self.setCentralWidget(central_widget)

        # Set up VTK rendering
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.9, 0.9, 0.9)  # Dark gray background
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)

        # Set up interactor
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()

        # Configure interactor style for rotation with left mouse button
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(style)

        # Initialize interactor
        self.interactor.Initialize()

        # Add world axes for reference
        # self.add_world_axes()

        # Start the interactor
        self.interactor.Start()

    def add_world_axes(self):
        """Add world coordinate axes to the scene"""
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(0.1, 0.1, 0.1)  # Set the length of the axes
        axes.SetShaftType(0)
        axes.SetAxisLabels(0)  # Not Show labels
        axes.SetCylinderRadius(0.02)

        # Add the axes to the renderer
        self.renderer.AddActor(axes)

    def load_urdf_file(self, filename):
        """Load a URDF file and visualize the robot"""
        if filename and os.path.exists(filename):
            # Clear previous models
            self.clear_models()

            # Parse the URDF file
            try:
                parser = URDFParser(filename)

                # Get robot info for visualization
                (
                    link_names,
                    link_mesh_files,
                    link_mesh_transformations,
                    link_frames,
                    link_colors,
                    joint_names,
                    joint_frames,
                    joint_types,
                    joint_axes,
                    joint_parent_links,
                    joint_child_links,
                    collision_mesh_files,
                    collision_mesh_transformations,
                ) = parser.get_robot_info()

                # Store revolute joints for slider controls
                self.revolute_joints = []
                for i, joint_type in enumerate(joint_types):
                    if joint_type == "revolute":
                        self.revolute_joints.append(
                            {
                                "name": joint_names[i],
                                "index": i,
                                "parent": joint_parent_links[i],
                                "child": joint_child_links[i],
                                "axis": joint_axes[i],
                            }
                        )

                # Create joint sliders
                self.create_joint_sliders()

                # Get chain information
                self.chains, trees = parser.get_chain_info()

                # Create models for each link
                for i in range(len(link_names)):
                    self.add_urdf_model(
                        link_names[i],
                        link_mesh_files[i],
                        link_mesh_transformations[i],
                        link_frames[i],
                        link_colors[i],
                    )

                # Create models for each collision link
                for i in range(len(collision_mesh_files)):
                    self.add_urdf_model(
                        f"collision_{i}",
                        collision_mesh_files[i],
                        collision_mesh_transformations[i],
                        None,
                        None,
                        model_type="collision",
                    )

                # use link mesh files to be decomposed
                self.collision_mesh_files = [
                    f for f in link_mesh_files if f is not None
                ]

                # Populate the chain tree
                self.populate_chain_tree()

                # Reset camera to show all actors
                self.renderer.ResetCamera()
                self.vtk_widget.GetRenderWindow().Render()

                # Store the current URDF file path only after successful loading
                self.current_urdf_file = filename

                # Update the current file label
                self.update_current_file_label()

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to load URDF file: {str(e)}"
                )

    def open_urdf_file(self):
        """Open a URDF file dialog and load the selected file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open URDF File", "", "URDF Files (*.urdf)"
        )

        if filename:
            self.load_urdf_file(filename)

    def add_urdf_model(
        self, name, mesh_file, mesh_transform, frame, color, model_type="visual"
    ):
        """Add a URDF model to the scene"""
        try:
            # Create a new URDF model with axis text (using link name as the text)
            model = URDFModel(
                name, mesh_file, mesh_transform, frame, color, axis_text=name
            )

            # Add the model to our list
            if model_type == "visual":
                self.models.append(model)
            elif model_type == "collision":
                self.models_collision.append(model)

            # Add the actor to the renderer
            self.renderer.AddActor(model.actor)

            # Add the axes actor to the renderer
            if model.axes_actor is not None:
                self.renderer.AddActor(model.axes_actor)

            # Add the text actor to the renderer if it exists
            if model.text_actor is not None:
                self.renderer.AddActor(model.text_actor)

            # Set initial visibility based on checkbox
            if hasattr(self, "cb_link_frames"):
                if model.axes_actor is not None:
                    model.axes_actor.SetVisibility(self.cb_link_frames.isChecked())
                if model.text_actor is not None:
                    model.text_actor.SetVisibility(self.cb_link_frames.isChecked())

        except Exception as e:
            QMessageBox.warning(
                self, "Warning", f"Failed to load model {name}: {str(e)}"
            )

    def clear_models(self):
        """Clear all models from the scene"""
        # Remove all actors from the renderer
        for model in self.models:
            self.renderer.RemoveActor(model.actor)
            self.renderer.RemoveActor(model.axes_actor)
            if hasattr(model, "text_actor") and model.text_actor is not None:
                self.renderer.RemoveActor(model.text_actor)

        for model in self.models_collision:
            self.renderer.RemoveActor(model.actor)
            self.renderer.RemoveActor(model.axes_actor)
            if hasattr(model, "text_actor") and model.text_actor is not None:
                self.renderer.RemoveActor(model.text_actor)

        # Clear the models list
        self.models = []
        self.models_collision = []

        # Clear the combo box and link list
        self.chain_combo.clear()
        self.link_list.clear()

        # Clear joint sliders
        self.clear_joint_sliders()

        # Clear MDH frames
        for actor in self.mdh_frames_actors:
            self.renderer.RemoveActor(actor)
        self.mdh_frames_actors = []

        # Clear MDH text actors
        for text_actor in self.mdh_text_actors:
            self.renderer.RemoveActor(text_actor)
        self.mdh_text_actors = []

        # Reset selected chain and current URDF file
        self.selected_chain = None
        self.current_urdf_file = None

        # Update current file label
        self.update_current_file_label()

        # Update the rendering
        self.vtk_widget.GetRenderWindow().Render()

    def populate_chain_tree(self):
        """Populate the chain combo box and link list"""
        self.chain_combo.clear()
        self.link_list.clear()

        # Add each chain to the combo box
        for i, chain in enumerate(self.chains):
            self.chain_combo.addItem(f"Chain {i+1}: {chain['name']}", i)

        # Select the first chain by default if available
        if self.chains:
            self.selected_chain_index = 0
            self.selected_chain = self.chains[0]
            self.chain_combo.setCurrentIndex(0)
            self.update_link_list()

    def on_chain_selected(self, index):
        """Handle chain selection from combo box"""
        if index >= 0 and index < len(self.chains):
            # Unhighlight all models first
            for model in self.models:
                model.unhighlight()

            # Set the selected chain
            self.selected_chain_index = index
            self.selected_chain = self.chains[index]

            # Update the link list
            self.update_link_list()

            # Update MDH frames if they are currently visible
            if self.cb_mdh_frames.isChecked() and self.current_urdf_file:
                self.create_mdh_frames(self.selected_chain)

            # Update the rendering
            self.vtk_widget.GetRenderWindow().Render()

    def update_link_list(self):
        """Update the link list based on the selected chain"""
        self.link_list.clear()

        if self.selected_chain:
            # Add links to the list
            for link_name in self.selected_chain["link_names"]:
                item = QListWidgetItem(link_name)
                item.setData(Qt.UserRole, link_name)
                self.link_list.addItem(item)

    def on_link_selection_changed(self):
        """Handle link selection from list"""
        # Unhighlight all models first
        for model in self.models:
            model.unhighlight()

        # Get selected link
        selected_items = self.link_list.selectedItems()
        if selected_items:
            link_name = selected_items[0].data(Qt.UserRole)

            # Highlight the selected link
            for model in self.models:
                if model.name == link_name:
                    model.highlight()
                    print(model.link_frame)
        # Update the rendering
        self.vtk_widget.GetRenderWindow().Render()

    def toggle_collision(self, state):
        visible = state == Qt.Checked

        for model in self.models_collision:
            model.actor.SetVisibility(visible)
            if model.axes_actor is not None:
                model.axes_actor.SetVisibility(visible)
            if hasattr(model, "text_actor") and model.text_actor is not None:
                model.text_actor.SetVisibility(visible)

        # Update the rendering
        self.vtk_widget.GetRenderWindow().Render()

    def toggle_link_frames(self, state):
        """Toggle visibility of link frames and their text labels"""
        visible = state == Qt.Checked

        for model in self.models:
            model.axes_actor.SetVisibility(visible)
            if hasattr(model, "text_actor") and model.text_actor is not None:
                model.text_actor.SetVisibility(visible)

        # Update the rendering
        self.vtk_widget.GetRenderWindow().Render()

    def toggle_mdh_frames(self, state):
        """Toggle visibility of MDH frames"""
        visible = state == Qt.Checked

        # If we want to show MDH frames
        if visible:
            if not self.current_urdf_file:
                QMessageBox.warning(
                    self, "Warning", "Please load a URDF file first. [MDH]"
                )
                self.cb_mdh_frames.setChecked(False)
                return

            if self.selected_chain:
                # Always recreate MDH frames to ensure they're up to date
                self.create_mdh_frames(self.selected_chain)
            else:
                QMessageBox.warning(self, "Warning", "Please select a chain first.")
                self.cb_mdh_frames.setChecked(False)
                return
        else:
            # Hide MDH frames and text
            for actor in self.mdh_frames_actors:
                actor.SetVisibility(False)
            for text_actor in self.mdh_text_actors:
                text_actor.SetVisibility(False)

        # Update the rendering
        self.vtk_widget.GetRenderWindow().Render()

    def create_mdh_frames(self, chain):
        """Create MDH frame actors for the selected chain"""
        # Clear existing MDH frames
        for actor in self.mdh_frames_actors:
            self.renderer.RemoveActor(actor)
        self.mdh_frames_actors = []

        # Clear existing MDH text actors
        for text_actor in self.mdh_text_actors:
            self.renderer.RemoveActor(text_actor)
        self.mdh_text_actors = []

        # Create a fresh parser instance to ensure we get the latest data
        parser = URDFParser(self.current_urdf_file)

        # Get chain information to ensure we have the latest chain data
        chains, _ = parser.get_chain_info()

        # Find the matching chain in the updated chains list
        current_chain = None
        for c in chains:
            if c["name"] == chain["name"]:
                current_chain = c
                break

        # If we couldn't find a matching chain, use the provided chain
        if current_chain is None:
            current_chain = chain

        # Get MDH frames using the current chain
        mdh_frames = parser.get_mdh_frames(current_chain)
        # update mdh_frames using joint position

        mdh_frames = parser.update_mdh_frames(mdh_frames, self.joint_values)

        # Create axes actors for each MDH frame
        for i, frame in enumerate(mdh_frames):
            axes = vtk.vtkAxesActor()
            axes.SetTotalLength(0.05, 0.05, 0.05)  # Set the length of the axes
            axes.SetShaftType(0)
            axes.SetAxisLabels(0)
            axes.SetCylinderRadius(0.01)

            # Create transform
            vtk_transform = vtk.vtkTransform()
            vtk_transform.SetMatrix(frame.flatten())
            axes.SetUserTransform(vtk_transform)

            # Add to renderer
            self.renderer.AddActor(axes)
            self.mdh_frames_actors.append(axes)

            # Set initial visibility based on checkbox
            axes.SetVisibility(self.cb_mdh_frames.isChecked())

            # Create text label for MDH frame
            text_actor = vtk.vtkCaptionActor2D()
            text_actor.SetCaption(f"MDH{i}")
            text_actor.GetTextActor().SetTextScaleModeToNone()
            text_actor.GetCaptionTextProperty().SetFontSize(14)
            text_actor.GetCaptionTextProperty().SetColor(
                0, 0, 1
            )  # Blue text for MDH frames
            text_actor.GetCaptionTextProperty().SetBold(False)

            # Position the text at the end of the z-axis
            z_endpoint = [0, 0, 0.05, 1]  # Same length as axes
            transformed_point = vtk_transform.TransformPoint(
                z_endpoint[0], z_endpoint[1], z_endpoint[2]
            )
            text_actor.SetAttachmentPoint(
                transformed_point[0], transformed_point[1], transformed_point[2]
            )

            # Configure the caption
            text_actor.BorderOff()
            text_actor.LeaderOff()
            text_actor.ThreeDimensionalLeaderOff()
            text_actor.SetPadding(2)

            # Add to renderer
            self.renderer.AddActor(text_actor)
            self.mdh_text_actors.append(text_actor)

            # Set initial visibility based on checkbox
            text_actor.SetVisibility(self.cb_mdh_frames.isChecked())

        # Update the rendering
        self.vtk_widget.GetRenderWindow().Render()

    def show_mdh_parameters(self):
        """Show MDH parameters in a dialog"""
        if not self.selected_chain:
            QMessageBox.warning(
                self, "Warning", "Please select a chain first to view MDH parameters."
            )
            return

        if not self.current_urdf_file:
            QMessageBox.warning(
                self, "Warning", "Please load a URDF file first. [SHOW MDH]"
            )
            return

        # Create a fresh parser instance to ensure we get the latest MDH parameters
        parser = URDFParser(self.current_urdf_file)

        # Get chain information to ensure we have the latest chain data
        chains, _ = parser.get_chain_info()

        # Find the matching chain in the updated chains list
        current_chain = None
        for chain in chains:
            if chain["name"] == self.selected_chain["name"]:
                current_chain = chain
                break

        # If we couldn't find a matching chain, use the selected chain
        if current_chain is None:
            current_chain = self.selected_chain

        # Get MDH parameters using the current chain
        _, _, _, mdh_parameters = parser.get_mdh_parameters(current_chain)

        # Create and show the new MDH dialog
        dialog = MDHDialog(self, current_chain["name"], mdh_parameters)
        dialog.exec()

    def apply_transparency(self):
        """Apply transparency to virtual loaded models"""
        # Get transparency value from slider (convert from 0-100 to 0.0-1.0)
        transparency = self.transparency_slider.value() / 100.0

        # Apply the transparency to virtual models
        for model in self.models:
            model.set_transparency(transparency)

        # Update the rendering
        self.vtk_widget.GetRenderWindow().Render()

    def create_joint_sliders(self):
        """Create sliders for controlling joint angles"""
        # Clear existing sliders
        self.clear_joint_sliders()

        # Initialize joint values array with zeros
        self.joint_values = [0.0] * len(self.revolute_joints)

        # Create a slider for each revolute joint
        for i, joint in enumerate(self.revolute_joints):
            # Create a group for this joint
            joint_box = QGroupBox(joint["name"])
            joint_box_layout = QVBoxLayout(joint_box)

            # Create a horizontal layout for slider and value label
            slider_layout = QHBoxLayout()

            # Create a slider
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(-314)  # -π in hundredths
            slider.setMaximum(314)  # π in hundredths
            slider.setValue(0)  # Default to 0
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(157)  # π/2 in hundredths

            # Create a label to show the current value
            value_label = QLabel("0.00")
            value_label.setMinimumWidth(
                40
            )  # Set minimum width to ensure consistent alignment
            value_label.setAlignment(
                Qt.AlignRight | Qt.AlignVCenter
            )  # Right-align the text

            # Connect the slider to update function
            slider.valueChanged.connect(
                lambda val, idx=i, label=value_label: self.update_joint_angle(
                    val, idx, label
                )
            )

            # Add slider and label to the horizontal layout
            slider_layout.addWidget(slider, 1)  # Give slider a stretch factor of 1
            slider_layout.addWidget(value_label)

            # Add the horizontal layout to the joint box
            joint_box_layout.addLayout(slider_layout)

            # Add the joint box to the joint layout
            self.joint_layout.addWidget(joint_box)

            # Store the slider for later access
            self.joint_sliders.append(slider)

    def clear_joint_sliders(self):
        """Clear all joint sliders"""
        # Clear the joint values
        self.joint_values = []

        # Clear the sliders list
        self.joint_sliders = []

        # Remove all widgets from the joint layout
        if hasattr(self, "joint_layout"):
            while self.joint_layout.count():
                item = self.joint_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

    def update_joint_angle(self, value, index, label):
        """Update joint angle when slider is moved"""
        # Convert slider value to radians (from hundredths)
        angle = value / 100.0

        # Update the label
        label.setText(f"{angle:.2f}")

        # Store the value
        self.joint_values[index] = angle

        # Update the model
        self.update_model_with_joint_angles()

    def reset_joints(self):
        """Reset all joints to zero position"""
        if not self.joint_sliders or not self.joint_values:
            return

        # Set all sliders to zero
        for i, slider in enumerate(self.joint_sliders):
            slider.setValue(0)

        # Update the model
        self.update_model_with_joint_angles()

    def randomize_joints(self):
        """Set all joints to random values"""
        if not self.joint_sliders or not self.joint_values:
            return

        # Set all sliders to random values between min and max
        for i, slider in enumerate(self.joint_sliders):
            random_value = np.random.randint(slider.minimum(), slider.maximum())
            slider.setValue(random_value)

        # Update the model
        self.update_model_with_joint_angles()

    def update_model_with_joint_angles(self):
        """Update the model visualization with current joint angles"""
        if not self.current_urdf_file:
            return

        # Create a fresh parser instance
        parser = URDFParser(self.current_urdf_file)

        # Get updated robot info with joint angles
        (
            link_names,
            link_mesh_files,
            link_mesh_transformations,
            link_frames,
            link_colors,
            joint_names,
            joint_frames,
            joint_types,
            joint_axes,
            joint_parent_links,
            joint_child_links,
            collision_mesh_files,
            collision_mesh_transformations,
        ) = parser.get_robot_info(qs=self.joint_values)

        # Update existing models with new transformations
        for i, model in enumerate(self.models):
            if i < len(link_names) and model.name == link_names[i]:
                # Update mesh transformation
                model.apply_transform(link_mesh_transformations[i])

                # Update axes and text actors
                if model.axes_actor:
                    vtk_transform = vtk.vtkTransform()
                    vtk_transform.SetMatrix(link_frames[i].flatten())
                    model.axes_actor.SetUserTransform(vtk_transform)

                if model.text_actor:
                    # Update text position based on new frame
                    z_endpoint = [
                        0,
                        0,
                        0.05,
                        1,
                    ]  # Same axis_length as in create_axes_actor
                    vtk_transform = vtk.vtkTransform()
                    vtk_transform.SetMatrix(link_frames[i].flatten())
                    transformed_point = vtk_transform.TransformPoint(
                        z_endpoint[0], z_endpoint[1], z_endpoint[2]
                    )
                    model.text_actor.SetAttachmentPoint(
                        transformed_point[0], transformed_point[1], transformed_point[2]
                    )

        # Update existing models with new transformations
        for i, model in enumerate(self.models_collision):
            # Update mesh transformation
            model.apply_transform(collision_mesh_transformations[i])

            # Update axes and text actors
            if model.axes_actor:
                vtk_transform = vtk.vtkTransform()
                vtk_transform.SetMatrix(collision_mesh_transformations[i].flatten())
                model.axes_actor.SetUserTransform(vtk_transform)

            if model.text_actor:
                # Update text position based on new frame
                z_endpoint = [0, 0, 0.05, 1]  # Same axis_length as in create_axes_actor
                vtk_transform = vtk.vtkTransform()
                vtk_transform.SetMatrix(collision_mesh_transformations[i].flatten())
                transformed_point = vtk_transform.TransformPoint(
                    z_endpoint[0], z_endpoint[1], z_endpoint[2]
                )
                model.text_actor.SetAttachmentPoint(
                    transformed_point[0], transformed_point[1], transformed_point[2]
                )

        # Update MDH frames if they are visible
        if (
            hasattr(self, "cb_mdh_frames")
            and self.cb_mdh_frames.isChecked()
            and self.selected_chain
        ):
            self.create_mdh_frames(self.selected_chain)

        # Update the rendering
        self.vtk_widget.GetRenderWindow().Render()

    def edit_urdf_file(self, replace_collision=False):
        """Open the current URDF file in the XML editor"""
        if not self.current_urdf_file:
            QMessageBox.warning(
                self, "Warning", "Please load a URDF file first. [Edit]"
            )
            return

        # Create and show the XML editor window with update callback
        self.editor = XMLEditor(self.current_urdf_file, self.update_model_from_xml)
        if replace_collision:
            self.editor.replace_collision()
        self.editor.show()

    def update_model_from_xml(self, xml_content):
        """Update the model using XML content from the editor"""
        try:
            # Create a temporary file to store the XML content

            if "_temp.urdf" not in self.current_urdf_file:
                temp_path = self.current_urdf_file.lower().replace(
                    ".urdf", "_temp.urdf"
                )
            else:
                temp_path = self.current_urdf_file.lower()

            with open(temp_path, "w", encoding="utf-8") as temp_file:
                temp_file.write(xml_content)

            # Clear previous models
            self.clear_models()

            # Parse the URDF from the temporary file
            parser = URDFParser(temp_path)

            # Get robot info for visualization
            (
                link_names,
                link_mesh_files,
                link_mesh_transformations,
                link_frames,
                link_colors,
                joint_names,
                joint_frames,
                joint_types,
                joint_axes,
                joint_parent_links,
                joint_child_links,
                collision_mesh_files,
                collision_mesh_transformations,
            ) = parser.get_robot_info()

            # Store revolute joints for slider controls
            self.revolute_joints = []
            for i, joint_type in enumerate(joint_types):
                if joint_type == "revolute":
                    self.revolute_joints.append(
                        {
                            "name": joint_names[i],
                            "index": i,
                            "parent": joint_parent_links[i],
                            "child": joint_child_links[i],
                            "axis": joint_axes[i],
                        }
                    )

            # Create joint sliders
            self.create_joint_sliders()

            # Get chain information
            self.chains, trees = parser.get_chain_info()

            # Create models for each link
            for i in range(len(link_names)):
                self.add_urdf_model(
                    link_names[i],
                    link_mesh_files[i],
                    link_mesh_transformations[i],
                    link_frames[i],
                    link_colors[i],
                )

            # Create models for each collision link
            for i in range(len(collision_mesh_files)):
                self.add_urdf_model(
                    f"",
                    collision_mesh_files[i],
                    collision_mesh_transformations[i],
                    None,
                    None,
                    model_type="collision",
                )

            self.cb_collision.setChecked(True)
            self.transparency_slider.setValue(100)

            # Populate the chain tree
            self.populate_chain_tree()

            # Reset camera to show all actors
            # self.renderer.ResetCamera()
            self.vtk_widget.GetRenderWindow().Render()

            # Store the temporary file path as the current URDF file
            # This allows further editing and updates
            self.current_urdf_file = temp_path

            # Update current file label
            self.update_current_file_label()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to update model from XML: {str(e)}"
            )

    def update_current_file_label(self):
        """Update the current file label with the current URDF file path"""
        if self.current_urdf_file:
            # Extract just the filename from the path for cleaner display
            filename = os.path.basename(self.current_urdf_file)
            self.current_file_label.setText(f"Current File: {filename}")
        else:
            self.current_file_label.setText("Current File: None")

    def decompose_collision_meshes(self):
        """Handle decomposition of collision meshes"""
        if not self.collision_mesh_files:
            QMessageBox.warning(
                self,
                "Warning",
                "No collision meshes available. Please load a URDF file first.",
            )
            return

        # Create and show the decomposition dialog
        dialog = DecompDialog(self, self.collision_mesh_files)

        decomposed_mesh_files = dialog.exec()

        if decomposed_mesh_files is not None:
            self.edit_urdf_file(replace_collision=True)

    def closeEvent(self, event):
        """Handle window close event"""
        # Close any open XML editor windows
        if hasattr(self, "editor") and self.editor is not None:
            self.editor.close()

        # Properly clean up the VTK widget
        self.vtk_widget.GetRenderWindow().Finalize()
        self.vtk_widget.close()

        # Exit the application
        QApplication.quit()

        event.accept()


def main():
    """Main function to run the application"""
    app = QApplication(sys.argv)
    viewer = URDFViewer()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
