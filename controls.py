"""Control panel widget for simulation parameters."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QSlider, QPushButton, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QColorDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class ControlPanel(QWidget):
    """Panel containing all simulation controls."""
    
    # Signals
    preset_changed = Signal(str)
    reset_requested = Signal()
    start_toggled = Signal()
    clear_trails_requested = Signal()
    speed_changed = Signal(float)
    trail_length_changed = Signal(int)
    trace_all_changed = Signal(bool)
    color_changed = Signal(str, object)  # target, color
    save_requested = Signal()
    load_requested = Signal()
    export_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize all UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        self._build_presets(layout)
        self._build_physics(layout)
        self._build_simulation(layout)
        self._build_appearance(layout)
        self._build_energy(layout)
        self._build_files(layout)
        
        layout.addStretch()

    def _make_group(self, layout: QVBoxLayout, title: str) -> QVBoxLayout:
        """Create a styled group box and return its layout."""
        grp = QGroupBox(title)
        grp.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #AAA;
                border: 1px solid #444;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }
        """)
        vbox = QVBoxLayout(grp)
        vbox.setSpacing(4)
        layout.addWidget(grp)
        return vbox

    def _build_presets(self, parent: QVBoxLayout) -> None:
        """Build preset selection controls."""
        vbox = self._make_group(parent, "Presets")
        self.cb_preset = QComboBox()
        self.cb_preset.addItems([
            "Custom", "Single", "Classic Double", "Triple Chaos",
            "Helix", "Cascade", "Long Chain"
        ])
        self.cb_preset.currentTextChanged.connect(self.preset_changed.emit)
        vbox.addWidget(self.cb_preset)

    def _build_physics(self, parent: QVBoxLayout) -> None:
        """Build physics parameter controls."""
        vbox = self._make_group(parent, "Physics")
        
        # Number of bobs
        vbox.addWidget(QLabel("Number of Bobs:"))
        self.spin_n = QSpinBox()
        self.spin_n.setRange(1, 20)
        self.spin_n.setValue(3)
        vbox.addWidget(self.spin_n)
        
        # Link length
        vbox.addWidget(QLabel("Link Length (m):"))
        self.spin_len = QDoubleSpinBox()
        self.spin_len.setRange(0.2, 2.0)
        self.spin_len.setValue(0.8)
        self.spin_len.setSingleStep(0.1)
        vbox.addWidget(self.spin_len)
        
        # Bob mass
        vbox.addWidget(QLabel("Bob Mass (kg):"))
        self.spin_mass = QDoubleSpinBox()
        self.spin_mass.setRange(0.5, 10.0)
        self.spin_mass.setValue(1.0)
        self.spin_mass.setSingleStep(0.1)
        vbox.addWidget(self.spin_mass)
        
        # Gravity
        vbox.addWidget(QLabel("Gravity (m/s²):"))
        self.spin_g = QDoubleSpinBox()
        self.spin_g.setRange(1.0, 25.0)
        self.spin_g.setValue(9.81)
        self.spin_g.setSingleStep(0.1)
        vbox.addWidget(self.spin_g)
        
        # Integrator
        vbox.addWidget(QLabel("Integrator:"))
        self.cb_integ = QComboBox()
        self.cb_integ.addItems(["RK4", "Euler", "Verlet", "PBD"])
        vbox.addWidget(self.cb_integ)

    def _build_simulation(self, parent: QVBoxLayout) -> None:
        """Build simulation control buttons."""
        vbox = self._make_group(parent, "Simulation")
        
        # Speed slider
        vbox.addWidget(QLabel("Speed:"))
        h = QHBoxLayout()
        self.sl_speed = QSlider(Qt.Orientation.Horizontal)
        self.sl_speed.setRange(1, 30)
        self.sl_speed.setValue(10)
        self.lbl_speed = QLabel("1.0x")
        self.sl_speed.valueChanged.connect(self._on_speed_changed)
        h.addWidget(self.sl_speed)
        h.addWidget(self.lbl_speed)
        vbox.addLayout(h)

        # Start/Pause button
        self.btn_start = QPushButton("▶  Start")
        self.btn_start.clicked.connect(self.start_toggled.emit)
        vbox.addWidget(self.btn_start)
        
        # Reset button
        btn_reset = QPushButton("↺  Reset")
        btn_reset.clicked.connect(self.reset_requested.emit)
        vbox.addWidget(btn_reset)
        
        # Clear trails button
        btn_clear = QPushButton("✕  Clear Trails")
        btn_clear.clicked.connect(self.clear_trails_requested.emit)
        vbox.addWidget(btn_clear)

    def _on_speed_changed(self, v: int) -> None:
        """Handle speed slider changes."""
        self.lbl_speed.setText(f"{v/10:.1f}x")
        self.speed_changed.emit(v / 10.0)

    def _build_appearance(self, parent: QVBoxLayout) -> None:
        """Build appearance controls."""
        vbox = self._make_group(parent, "Appearance")
        
        # Trace all bobs checkbox
        self.chk_trace = QCheckBox("Trace all bobs individually")
        self.chk_trace.stateChanged.connect(
            lambda s: self.trace_all_changed.emit(bool(s))
        )
        vbox.addWidget(self.chk_trace)
        
        # Trail length slider
        vbox.addWidget(QLabel("Trail Length:"))
        self.sl_trail = QSlider(Qt.Orientation.Horizontal)
        self.sl_trail.setRange(50, 2000)
        self.sl_trail.setValue(600)
        self.lbl_trail = QLabel("600")
        self.sl_trail.valueChanged.connect(self._on_trail_length_changed)
        h = QHBoxLayout()
        h.addWidget(self.sl_trail)
        h.addWidget(self.lbl_trail)
        vbox.addLayout(h)

        # Color buttons
        btn_bob = QPushButton("Bob Color")
        btn_bob.clicked.connect(lambda: self._pick_color('bob'))
        vbox.addWidget(btn_bob)
        
        btn_rod = QPushButton("Rod Color")
        btn_rod.clicked.connect(lambda: self._pick_color('rod'))
        vbox.addWidget(btn_rod)
        
        btn_trail = QPushButton("Trail Color")
        btn_trail.clicked.connect(lambda: self._pick_color('trail'))
        vbox.addWidget(btn_trail)

    def _on_trail_length_changed(self, v: int) -> None:
        """Handle trail length slider changes."""
        self.lbl_trail.setText(str(v))
        self.trail_length_changed.emit(v)

    def _build_energy(self, parent: QVBoxLayout) -> None:
        """Build energy display labels."""
        vbox = self._make_group(parent, "Energy Monitor")
        
        font = QFont("Consolas", 9)
        
        self.lbl_ke = QLabel("KE:     0.000 J")
        self.lbl_ke.setFont(font)
        self.lbl_pe = QLabel("PE:     0.000 J")
        self.lbl_pe.setFont(font)
        self.lbl_te = QLabel("Tot:    0.000 J")
        self.lbl_te.setFont(font)
        
        vbox.addWidget(self.lbl_ke)
        vbox.addWidget(self.lbl_pe)
        vbox.addWidget(self.lbl_te)

    def _build_files(self, parent: QVBoxLayout) -> None:
        """Build file operation buttons."""
        vbox = self._make_group(parent, "File Operations")
        
        btn_save = QPushButton("Save State")
        btn_save.clicked.connect(self.save_requested.emit)
        vbox.addWidget(btn_save)
        
        btn_load = QPushButton("Load State")
        btn_load.clicked.connect(self.load_requested.emit)
        vbox.addWidget(btn_load)
        
        btn_export = QPushButton("Export PNG")
        btn_export.clicked.connect(self.export_requested.emit)
        vbox.addWidget(btn_export)

    def _pick_color(self, target: str) -> None:
        """Open color picker dialog."""
        initial_colors = {
            'bob': QColor(77, 179, 255),
            'rod': QColor(190, 190, 200),
            'trail': QColor(255, 191, 51)
        }
        color = QColorDialog.getColor(
            initial_colors.get(target, QColor(255, 255, 255)),
            self,
            f"Pick {target} color"
        )
        if color.isValid():
            self.color_changed.emit(target, color)

    def update_energy_display(self, ke: float, pe: float, te: float) -> None:
        """Update the energy labels."""
        self.lbl_ke.setText(f"KE:  {ke:9.3f} J")
        self.lbl_pe.setText(f"PE:  {pe:9.3f} J")
        self.lbl_te.setText(f"Tot: {te:9.3f} J")

    def set_start_button_text(self, text: str) -> None:
        """Update the start/pause button text."""
        self.btn_start.setText(text)

    def set_preset_text(self, text: str) -> None:
        """Set the preset combo box text."""
        self.cb_preset.blockSignals(True)
        self.cb_preset.setCurrentText(text)
        self.cb_preset.blockSignals(False)

    def get_physics_params(self) -> dict:
        """Get current physics parameters."""
        return {
            'n': self.spin_n.value(),
            'length': self.spin_len.value(),
            'mass': self.spin_mass.value(),
            'gravity': self.spin_g.value(),
            'integrator': self.cb_integ.currentText().lower()
        }

    def sync_from_physics(self, n: int, integrator: str) -> None:
        """Sync UI controls from physics state."""
        self.spin_n.setValue(n)
        self.cb_integ.setCurrentText(integrator.capitalize())