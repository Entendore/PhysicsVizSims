"""Main application window."""

import json
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QScrollArea, QFileDialog, QMessageBox
)
from PySide6.QtCore import QTimer, Qt

from canvas import PendulumCanvas
from controls import ControlPanel
from physics import NPendulumPhysics


# Preset configurations: (n, angles)
PRESETS = {
    "Single": (1, [3.14159 / 2]),
    "Classic Double": (2, [3.14159 / 2, 3.14159 / 2]),
    "Triple Chaos": (3, [2 * 3.14159 / 3, 3.14159 / 3, 3.14159 / 2]),
    "Helix": (5, [3.14159 / 2, -3.14159 / 2, 3.14159 / 2, -3.14159 / 2, 3.14159 / 2]),
    "Cascade": (8, [3.14159 / 4] * 8),
    "Long Chain": (15, [0.3] * 15)
}


class MainWindow(QMainWindow):
    """Main window containing canvas and controls."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("N-Pendulum Chain Simulator")
        self.resize(1100, 750)
        
        self._setup_ui()
        self._setup_timer()
        self._connect_signals()
        
        # Initial setup after UI is ready
        QTimer.singleShot(50, self.reset_sim)

    def _setup_ui(self) -> None:
        """Initialize UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Canvas
        self.canvas = PendulumCanvas()
        main_layout.addWidget(self.canvas, stretch=3)

        # Controls in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumWidth(320)
        scroll.setMinimumWidth(280)
        
        self.controls = ControlPanel()
        scroll.setWidget(self.controls)
        main_layout.addWidget(scroll, stretch=1)

    def _setup_timer(self) -> None:
        """Setup the simulation timer."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_sim)
        self.timer.start(16)  # ~60 FPS

    def _connect_signals(self) -> None:
        """Connect control panel signals to slots."""
        c = self.controls
        c.preset_changed.connect(self.apply_preset)
        c.reset_requested.connect(self.reset_sim)
        c.start_toggled.connect(self.toggle_sim)
        c.clear_trails_requested.connect(self.clear_trails)
        c.trail_length_changed.connect(self.change_trail_len)
        c.trace_all_changed.connect(self.set_trace_all)
        c.color_changed.connect(self.set_color)
        c.save_requested.connect(self.save_state)
        c.load_requested.connect(self.load_state)
        c.export_requested.connect(self.export_png)

    def update_sim(self) -> None:
        """Update simulation state (called by timer)."""
        if not self.canvas.physics:
            return
            
        self.canvas.speed = self.controls.sl_speed.value() / 10.0
        self.canvas.tick(0.016)
        
        # Update energy display
        ke, pe, te = self.canvas.physics.energy()
        self.controls.update_energy_display(ke, pe, te)

    def toggle_sim(self) -> None:
        """Toggle simulation running state."""
        if not self.canvas.physics:
            return
            
        self.canvas.physics.integrator = self.controls.cb_integ.currentText().lower()
        self.canvas.running = not self.canvas.running
        
        text = "⏸  Pause" if self.canvas.running else "▶  Start"
        self.controls.set_start_button_text(text)

    def reset_sim(self) -> None:
        """Reset simulation with current parameters."""
        params = self.controls.get_physics_params()
        self.canvas.init_pendulum(
            params['n'],
            params['length'],
            params['mass'],
            params['gravity'],
            params['integrator']
        )
        self.controls.set_start_button_text("▶  Start")
        self.controls.set_preset_text("Custom")

    def apply_preset(self, text: str) -> None:
        """Apply a preset configuration."""
        if text not in PRESETS:
            return
            
        n, angles = PRESETS[text]
        self.controls.spin_n.setValue(n)
        self.reset_sim()
        
        if self.canvas.physics:
            # FIX: Ensure angles match n
            if len(angles) != n:
                angles = angles[:n] if len(angles) > n else angles + [angles[-1]] * (n - len(angles))
            self.canvas.physics.state[0::2] = angles
            self.canvas.physics.clear_trails()

    def clear_trails(self) -> None:
        """Clear all trail data."""
        if self.canvas.physics:
            self.canvas.physics.clear_trails()

    def change_trail_len(self, val: int) -> None:
        """Update maximum trail length."""
        if self.canvas.physics:
            self.canvas.physics.max_trail = val

    def set_trace_all(self, enabled: bool) -> None:
        """Set trace all bobs mode."""
        self.canvas.trace_all = enabled

    def set_color(self, target: str, color) -> None:
        """Set a color property on the canvas."""
        if target == 'bob':
            self.canvas.bob_color = color
        elif target == 'rod':
            self.canvas.rod_color = color
        elif target == 'trail':
            self.canvas.trail_color = color

    def save_state(self) -> None:
        """Save physics state to JSON file."""
        if not self.canvas.physics:
            QMessageBox.warning(self, "Warning", "No simulation to save")
            return
            
        path, _ = QFileDialog.getSaveFileName(
            self, "Save State", "", "JSON Files (*.json)"
        )
        if path:
            try:
                with open(path, 'w') as f:
                    json.dump(self.canvas.physics.to_dict(), f, indent=2)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def load_state(self) -> None:
        """Load physics state from JSON file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load State", "", "JSON Files (*.json)"
        )
        if path:
            try:
                with open(path) as f:
                    data = json.load(f)
                    
                self.canvas.physics = NPendulumPhysics()
                self.canvas.physics.from_dict(data)
                self.canvas.running = False
                
                self.controls.set_start_button_text("▶  Start")
                self.controls.sync_from_physics(
                    self.canvas.physics.n,
                    self.canvas.physics.integrator
                )
                self.controls.set_preset_text("Custom")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {e}")

    def export_png(self) -> None:
        """Export canvas to PNG image."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Image", "", "PNG Files (*.png)"
        )
        if path:
            if not path.endswith('.png'):
                path += '.png'
            self.canvas.grab_frame().save(path)