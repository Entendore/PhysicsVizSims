"""Pendulum canvas widget for rendering the simulation."""

import math
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath
)

from utils import bob_qcolor, lerp_color, is_valid_position
from physics import NPendulumPhysics


class PendulumCanvas(QWidget):
    """Widget that renders the N-pendulum simulation."""
    
    DEFAULT_BG_COLOR = QColor(30, 30, 34)
    DEFAULT_BOB_COLOR = QColor(77, 179, 255)
    DEFAULT_ROD_COLOR = QColor(190, 190, 200)
    DEFAULT_TRAIL_COLOR = QColor(255, 191, 51)
    DEFAULT_BOB_RADIUS = 14
    DEFAULT_PIVOT_RADIUS = 6
    DEFAULT_ROD_WIDTH = 2.5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.physics: NPendulumPhysics = None
        self.running: bool = False
        self.speed: float = 1.0
        self.trace_all: bool = False
        self.bob_radius: int = self.DEFAULT_BOB_RADIUS
        
        # Colors
        self.bob_color = self.DEFAULT_BOB_COLOR
        self.rod_color = self.DEFAULT_ROD_COLOR
        self.trail_color = self.DEFAULT_TRAIL_COLOR
        self.bg_color = self.DEFAULT_BG_COLOR
        
        # Mouse interaction state
        self._dragging: bool = False
        self._drag_idx: int = -1
        
        self.setMinimumSize(400, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    @property
    def origin(self) -> tuple:
        """Get the pivot point in widget coordinates."""
        return (self.width() / 2, 80)

    def init_pendulum(
        self,
        n: int,
        length_m: float,
        mass: float,
        g: float,
        integrator: str
    ) -> None:
        """Initialize a new pendulum simulation."""
        px = length_m * NPendulumPhysics.SCALE
        try:
            self.physics = NPendulumPhysics(
                n=n,
                lengths=[px] * n,
                masses=[mass] * n,
                g=g,
                integrator=integrator
            )
            self.running = False
        except ValueError as e:
            print(f"Failed to initialize pendulum: {e}")
            self.physics = None

    def tick(self, dt: float) -> None:
        """Advance simulation by dt seconds."""
        if not self.physics:
            return
            
        if self.running:
            # Adaptive sub-stepping for stability
            n_sub = max(1, int(self.speed * 4))
            sub_dt = min(dt * self.speed / n_sub, 0.003)
            
            for _ in range(n_sub):
                self.physics.step(sub_dt)
            
            # Update trails
            pos = self.physics.get_positions(*self.origin)
            if self.trace_all:
                for i in range(self.physics.n):
                    self.physics.update_trail(i, pos[i + 1])
            else:
                self.physics.update_trail(self.physics.n - 1, pos[-1])
        
        self.update()

    def paintEvent(self, event) -> None:
        """Render the pendulum simulation."""
        if not self.physics:
            self._draw_empty_state()
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pos = self.physics.get_positions(*self.origin)
        n = self.physics.n
        
        # Background
        painter.fillRect(self.rect(), self.bg_color)
        
        # Draw components in order
        self._draw_trails(painter, n)
        self._draw_rods(painter, pos)
        self._draw_pivot(painter, pos[0])
        self._draw_bobs(painter, pos, n)
        
        painter.end()

    def _draw_empty_state(self) -> None:
        """Draw placeholder when no physics is initialized."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)
        painter.setPen(QColor(100, 100, 100))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No simulation loaded")
        painter.end()

    def _draw_trails(self, painter: QPainter, n: int) -> None:
        """Draw trail paths with fading effect."""
        for i, trail in enumerate(self.physics.trails):
            if len(trail) < 2:
                continue
            
            color = bob_qcolor(i, n) if self.trace_all else self.trail_color
            tlen = len(trail)
            
            # Draw trail in segments with increasing opacity
            num_segments = 4
            for seg in range(num_segments):
                start_idx = int(tlen * seg / num_segments)
                end_idx = int(tlen * (seg + 1) / num_segments)
                pts = trail[start_idx:end_idx + 1]
                
                if len(pts) < 2:
                    continue
                
                # Calculate segment properties
                alpha = int(255 * ((seg + 1) / num_segments) ** 2 * 0.8)
                width = 1.0 + (seg * 0.6)
                
                pen = QPen(QColor(color.red(), color.green(), color.blue(), alpha))
                pen.setWidthF(width)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                
                # Build path with subsampling for performance
                path = QPainterPath()
                path.moveTo(pts[0][0], pts[0][1])
                
                step = max(1, len(pts) // 150)
                for pt in pts[step::step]:
                    path.lineTo(pt[0], pt[1])
                path.lineTo(pts[-1][0], pts[-1][1])
                
                painter.drawPath(path)

    def _draw_rods(self, painter: QPainter, pos: list) -> None:
        """Draw pendulum rods."""
        pen = QPen(self.rod_color, self.DEFAULT_ROD_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        for i in range(len(pos) - 1):
            x1, y1 = pos[i]
            x2, y2 = pos[i + 1]
            
            if is_valid_position(x1, y1) and is_valid_position(x2, y2):
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_pivot(self, painter: QPainter, pivot: tuple) -> None:
        """Draw the pivot point."""
        x, y = pivot
        if not is_valid_position(x, y):
            return
            
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(220, 220, 220)))
        painter.drawEllipse(QPointF(x, y), self.DEFAULT_PIVOT_RADIUS, self.DEFAULT_PIVOT_RADIUS)

    def _draw_bobs(self, painter: QPainter, pos: list, n: int) -> None:
        """Draw pendulum bobs with highlights."""
        for i in range(1, len(pos)):
            x, y = pos[i]
            
            # Skip invalid positions to prevent QPainter crashes
            if not is_valid_position(x, y):
                continue
            
            # Determine bob color
            color = bob_qcolor(i - 1, n) if self.trace_all else self.bob_color
            
            # Main bob
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1.5))
            painter.drawEllipse(QPointF(x, y), self.bob_radius, self.bob_radius)
            
            # Inner highlight for 3D effect
            highlight = lerp_color(color, QColor(255, 255, 255), 0.5)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(highlight))
            painter.drawEllipse(QPointF(x - 3, y - 3), 4, 4)

    def mousePressEvent(self, event) -> None:
        """Handle mouse press for dragging bobs."""
        if (
            self.physics is None
            or self.running
            or event.button() != Qt.MouseButton.LeftButton
        ):
            return
            
        pos = self.physics.get_positions(*self.origin)
        mx, my = event.position().x(), event.position().y()
        
        # Check if click is near any bob
        for i in range(1, len(pos)):
            if math.hypot(mx - pos[i][0], my - pos[i][1]) < self.bob_radius * 2.5:
                self._dragging = True
                self._drag_idx = i - 1
                return

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move for dragging bobs."""
        if not self._dragging:
            return
            
        mx, my = event.position().x(), event.position().y()
        pos = self.physics.get_positions(*self.origin)
        px, py = pos[self._drag_idx]
        
        # Calculate new angle from mouse position
        dx, dy = mx - px, my - py
        self.physics.state[self._drag_idx * 2] = math.atan2(dx, dy)
        self.physics.state[self._drag_idx * 2 + 1] = 0.0
        self.physics.clear_trails()
        
        if self.physics.integrator == "pbd":
            self.physics._init_pbd()
        
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release."""
        self._dragging = False
        self._drag_idx = -1

    def grab_frame(self) -> object:
        """Grab the current frame as a pixmap."""
        return self.grab()