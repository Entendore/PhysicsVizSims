"""Application entry point and theme configuration."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor

from main_window import MainWindow


def apply_dark_theme(app: QApplication) -> None:
    """Apply a dark color theme to the application."""
    palette = QPalette()
    
    # Window colors
    palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 34))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 48))
    
    # Tooltip colors
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 220, 220))
    
    # Text colors
    palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 50, 50))
    
    # Button colors
    palette.setColor(QPalette.ColorRole.Button, QColor(55, 55, 60))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
    
    # Link and highlight colors
    palette.setColor(QPalette.ColorRole.Link, QColor(90, 140, 210))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(70, 130, 210))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    
    # Disabled colors (FIX: Correctly use ColorGroup instead of ColorRole)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))
    
    app.setPalette(palette)
    
    # Additional stylesheet for fine-tuning
    app.setStyleSheet("""
        /* Group boxes */
        QGroupBox {
            font-weight: bold;
        }
        
        /* Push buttons */
        QPushButton {
            padding: 6px;
            border-radius: 4px;
            background-color: #3a3a40;
            border: 1px solid #555;
        }
        QPushButton:hover {
            background-color: #4a4a52;
        }
        QPushButton:pressed {
            background-color: #2a2a30;
        }
        QPushButton:disabled {
            background-color: #2a2a2e;
            color: #666;
        }
        
        /* Sliders */
        QSlider::groove:horizontal {
            height: 6px;
            background: #444;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #5898ff;
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }
        QSlider::handle:horizontal:hover {
            background: #6aa8ff;
        }
        
        /* Spin boxes and combo boxes */
        QSpinBox, QDoubleSpinBox, QComboBox {
            padding: 4px;
            background-color: #2a2a2e;
            border: 1px solid #555;
            border-radius: 3px;
        }
        QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #5898ff;
        }
        
        /* Combo box dropdown */
        QComboBox::drop-down {
            border: none;
            background: #3a3a40;
            border-radius: 3px;
        }
        QComboBox QAbstractItemView {
            background-color: #2a2a2e;
            selection-background-color: #5898ff;
        }
        
        /* Check boxes */
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 3px;
            border: 1px solid #555;
            background-color: #2a2a2e;
        }
        QCheckBox::indicator:checked {
            background-color: #5898ff;
        }
        
        /* Scroll bars */
        QScrollBar:vertical {
            background: #2a2a2e;
            width: 10px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #555;
            border-radius: 5px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background: #666;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """)


def main() -> None:
    """Application entry point."""
    app = QApplication(sys.argv)
    
    # Apply application metadata
    app.setApplicationName("N-Pendulum Simulator")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("PendulumSim")
    
    apply_dark_theme(app)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()