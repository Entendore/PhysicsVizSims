"""N-Pendulum physics engine using Lagrangian mechanics.

Supports multiple integration methods:
- RK4: Fourth-order Runge-Kutta (most accurate)
- Euler: Simple forward Euler (fast but unstable)
- Verlet: Velocity Verlet (good energy conservation)
- PBD: Position-Based Dynamics (stable for large chains)
"""

import math
import numpy as np
from typing import List, Tuple, Optional, Dict


class NPendulumPhysics:
    """
    Equations of motion derived from the Lagrangian for an N-link pendulum.
    
    Coordinate convention:
    - Angles measured from +Y axis (downward), positive clockwise
    - Screen coordinates: +X is right, +Y is down
    - Internal calculations use pixel-space for uniform scaling
    """
    
    SCALE = 100.0  # pixels per metre

    def __init__(
        self,
        n: int = 2,
        lengths: Optional[List[float]] = None,
        masses: Optional[List[float]] = None,
        g: float = 9.81,
        initial_angles: Optional[List[float]] = None,
        integrator: str = "rk4"
    ):
        self.n = n
        self.g_real = g
        self.g = g * self.SCALE  # gravity in px/s²
        self.integrator = integrator.lower()
        self.damping = 0.9999  # velocity damping factor

        # Initialize lengths and masses
        self.lengths = (
            np.ones(n) * self.SCALE if lengths is None
            else np.array(lengths, dtype=float)
        )
        self.masses = (
            np.ones(n) if masses is None
            else np.array(masses, dtype=float)
        )

        # Validate inputs
        self._validate_inputs()

        # State vector: [theta0, omega0, theta1, omega1, ...]
        self.state = np.zeros(2 * n)
        if initial_angles is None:
            self.state[0::2] = np.pi / 2 + np.random.randn(n) * 0.05
        else:
            # FIX: Ensure angles array matches n
            angles = np.array(initial_angles, dtype=float)
            if len(angles) != n:
                angles = np.resize(angles, n)
            self.state[0::2] = angles

        # PBD state (position-based dynamics)
        self.pbd_pos = np.zeros((n, 2))
        self.pbd_prev = np.zeros((n, 2))
        self.pbd_vel = np.zeros((n, 2))
        self._init_pbd()

        # Trail storage
        self.trails: List[List[Tuple[float, float]]] = [[] for _ in range(n)]
        self.max_trail = 600

        # Precomputed cumulative masses
        self._cum = None
        self._rebuild_cache()

    def _validate_inputs(self) -> None:
        """Validate physics parameters."""
        if self.n < 1 or self.n > 50:
            raise ValueError(f"Number of bobs must be between 1 and 50, got {self.n}")
        if len(self.lengths) != self.n:
            raise ValueError(f"Lengths array must have {self.n} elements")
        if len(self.masses) != self.n:
            raise ValueError(f"Masses array must have {self.n} elements")
        if np.any(self.lengths <= 0):
            raise ValueError("All lengths must be positive")
        if np.any(self.masses <= 0):
            raise ValueError("All masses must be positive")
        if self.g_real <= 0:
            raise ValueError("Gravity must be positive")

    def _rebuild_cache(self) -> None:
        """Rebuild cached cumulative mass matrix."""
        self._cum = np.cumsum(self.masses[::-1])[::-1]

    def _init_pbd(self) -> None:
        """Initialize PBD positions from current angular state."""
        self.pbd_pos = np.zeros((self.n, 2))
        self.pbd_vel = np.zeros((self.n, 2))
        prev = np.array([0.0, 0.0])
        
        for i in range(self.n):
            th = self.state[2 * i]
            dx = self.lengths[i] * np.sin(th)
            dy = self.lengths[i] * np.cos(th)
            curr = prev + np.array([dx, dy])
            self.pbd_pos[i] = curr
            
            # Compute velocity from angular velocity
            vx = self.lengths[i] * self.state[2 * i + 1] * np.cos(th)
            vy = -self.lengths[i] * self.state[2 * i + 1] * np.sin(th)
            self.pbd_vel[i] = np.array([vx, vy])
            prev = curr
        
        self.pbd_prev = self.pbd_pos - self.pbd_vel * 0.016

    def _sync_angles_from_pbd(self) -> None:
        """Sync angular state from PBD positions."""
        prev = np.array([0.0, 0.0])
        
        for i in range(self.n):
            d = self.pbd_pos[i] - prev
            norm = np.linalg.norm(d)
            
            if norm < 1e-12:
                self.state[2 * i] = 0.0
                self.state[2 * i + 1] = 0.0
                prev = self.pbd_pos[i]
                continue
            
            # FIX: Corrected angle calculation
            self.state[2 * i] = math.atan2(d[0], d[1])
            
            r_hat = d / norm
            t_hat = np.array([-r_hat[1], r_hat[0]])
            v_tang = np.dot(self.pbd_vel[i], t_hat)
            self.state[2 * i + 1] = v_tang / (self.lengths[i] + 1e-12)
            prev = self.pbd_pos[i]

    def _mu_matrix(self) -> np.ndarray:
        """Compute effective mass matrix mu[i,j] = sum(m_k for k >= max(i,j))."""
        idx = np.arange(self.n)
        return self._cum[np.maximum(idx[:, None], idx[None, :])]

    def _mass_matrix(self, theta: np.ndarray) -> np.ndarray:
        """Compute the generalized mass matrix M(theta)."""
        mu = self._mu_matrix()
        diff = theta[:, None] - theta[None, :]
        ll = self.lengths[:, None] * self.lengths[None, :]
        return ll * np.cos(diff) * mu

    def _forces(self, theta: np.ndarray, omega: np.ndarray) -> np.ndarray:
        """Compute generalized forces (Coriolis + gravity)."""
        mu = self._mu_matrix()
        diff = theta[:, None] - theta[None, :]
        ll = self.lengths[:, None] * self.lengths[None, :]
        
        # Coriolis/centrifugal terms
        coriolis = np.sum(
            ll * np.sin(diff) * mu * (omega ** 2)[None, :], axis=1
        )
        
        # Gravity terms
        gravity = self.g * self.lengths * np.sin(theta) * self._cum
        
        return -coriolis - gravity

    def _derivs(self, state: np.ndarray) -> np.ndarray:
        """Compute state derivatives for ODE integration."""
        theta, omega = state[0::2], state[1::2]
        M = self._mass_matrix(theta)
        F = self._forces(theta, omega)
        
        try:
            alpha = np.linalg.solve(M, F)
        except np.linalg.LinAlgError:
            # Fallback: use pseudoinverse
            alpha = np.linalg.lstsq(M, F, rcond=None)[0]
        
        return np.concatenate([omega, alpha])

    def _step_euler(self, dt: float) -> None:
        """Forward Euler integration step."""
        self.state += dt * self._derivs(self.state)
        self.state[1::2] *= self.damping

    def _step_rk4(self, dt: float) -> None:
        """Fourth-order Runge-Kutta integration step."""
        k1 = self._derivs(self.state)
        k2 = self._derivs(self.state + 0.5 * dt * k1)
        k3 = self._derivs(self.state + 0.5 * dt * k2)
        k4 = self._derivs(self.state + dt * k3)
        self.state += (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

    def _step_verlet(self, dt: float) -> None:
        """Velocity Verlet integration step."""
        n = self.n
        theta = self.state[0::2].copy()
        omega = self.state[1::2].copy()
        
        M = self._mass_matrix(theta)
        F = self._forces(theta, omega)
        
        try:
            alpha0 = np.linalg.solve(M, F)
        except np.linalg.LinAlgError:
            alpha0 = np.linalg.lstsq(M, F, rcond=None)[0]

        new_theta = theta + omega * dt + 0.5 * alpha0 * dt ** 2
        
        tmp = np.zeros(2 * n)
        tmp[0::2] = new_theta
        tmp[1::2] = omega
        alpha1 = self._derivs(tmp)[1::2]

        self.state[0::2] = new_theta
        self.state[1::2] = omega + 0.5 * (alpha0 + alpha1) * dt

    def _step_pbd(self, dt: float, iterations: int = 20) -> None:
        """Position-Based Dynamics integration step."""
        n = self.n
        g_vec = np.array([0.0, self.g])  # +Y is down in screen space
        
        # Verlet integration for prediction
        new_pos = 2 * self.pbd_pos - self.pbd_prev + g_vec * dt ** 2
        self.pbd_prev = self.pbd_pos.copy()
        self.pbd_pos = new_pos.copy()

        # Constraint solving iterations
        origin = np.array([0.0, 0.0])
        for _ in range(iterations):
            for i in range(n):
                p1 = origin if i == 0 else self.pbd_pos[i - 1]
                p2 = self.pbd_pos[i]
                delta = p2 - p1
                dist = np.linalg.norm(delta)
                
                if dist < 1e-12:
                    continue
                
                correction = (dist - self.lengths[i]) / dist * delta
                
                if i == 0:
                    # First link: only move bob (pivot is fixed)
                    self.pbd_pos[0] -= correction
                else:
                    # Other links: move both endpoints based on mass
                    w1 = 1.0 / self.masses[i - 1]
                    w2 = 1.0 / self.masses[i]
                    s = w1 + w2
                    self.pbd_pos[i - 1] += (w1 / s) * correction
                    self.pbd_pos[i] -= (w2 / s) * correction

        # Update velocity with damping
        self.pbd_vel = (self.pbd_pos - self.pbd_prev) / dt * self.damping
        self._sync_angles_from_pbd()

    def step(self, dt: float) -> None:
        """Perform one integration step."""
        dispatch = {
            "euler": self._step_euler,
            "verlet": self._step_verlet,
            "rk4": self._step_rk4,
            "pbd": self._step_pbd,
        }
        
        step_func = dispatch.get(self.integrator, self._step_rk4)
        step_func(dt)
        
        # Normalize angles to [-π, π]
        self.state[0::2] = (self.state[0::2] + np.pi) % (2 * np.pi) - np.pi
        
        # FIX: Guard against numerical instability (NaN / Inf)
        if not np.all(np.isfinite(self.state)):
            self.state = np.nan_to_num(
                self.state, nan=0.0, posinf=0.0, neginf=0.0
            )
            self.clear_trails()

    def get_positions(
        self, origin_x: float, origin_y: float
    ) -> List[Tuple[float, float]]:
        """Returns [pivot, bob0, bob1, ...] in screen pixel coordinates."""
        positions = [(origin_x, origin_y)]
        x, y = origin_x, origin_y
        
        for i in range(self.n):
            x += self.lengths[i] * np.sin(self.state[2 * i])
            y += self.lengths[i] * np.cos(self.state[2 * i])
            positions.append((x, y))
        
        return positions

    def update_trail(self, idx: int, pos: Tuple[float, float]) -> None:
        """Add a position to the trail for bob at index."""
        if idx < 0 or idx >= self.n:
            return
        self.trails[idx].append(pos)
        if len(self.trails[idx]) > self.max_trail:
            self.trails[idx].pop(0)

    def clear_trails(self) -> None:
        """Clear all trail data."""
        self.trails = [[] for _ in range(self.n)]

    def energy(self) -> Tuple[float, float, float]:
        """Compute kinetic, potential, and total energy in SI units."""
        theta, omega = self.state[0::2], self.state[1::2]
        s = self.SCALE
        l_m = self.lengths / s  # Convert to metres
        n = self.n
        
        # Kinetic energy: KE = 0.5 * omega^T * M * omega
        idx = np.arange(n)
        mu = self._cum[np.maximum(idx[:, None], idx[None, :])]
        diff = theta[:, None] - theta[None, :]
        ll = l_m[:, None] * l_m[None, :]
        M = ll * np.cos(diff) * mu
        ke = 0.5 * float(np.dot(omega, np.dot(M, omega)))
        
        # Potential energy: PE = sum(m_i * g * h_i)
        pe = 0.0
        for i in range(n):
            # Height of bob i above its lowest possible position
            h = sum(l_m[j] * (1.0 - np.cos(theta[j])) for j in range(i + 1))
            pe += float(self.masses[i]) * self.g_real * h
        
        return ke, pe, ke + pe

    def to_dict(self) -> Dict:
        """Serialize physics state to dictionary."""
        return {
            "n": self.n,
            "lengths": self.lengths.tolist(),
            "masses": self.masses.tolist(),
            "state": self.state.tolist(),
            "integrator": self.integrator,
            "g": self.g_real,
            "damping": self.damping,
        }

    def from_dict(self, d: Dict) -> None:
        """Deserialize physics state from dictionary."""
        self.n = d["n"]
        self.lengths = np.array(d["lengths"])
        self.masses = np.array(d["masses"])
        self.state = np.array(d["state"])
        self.integrator = d["integrator"]
        self.g_real = d.get("g", 9.81)
        self.damping = d.get("damping", 0.9999)
        self.g = self.g_real * self.SCALE
        self.trails = [[] for _ in range(self.n)]
        self._rebuild_cache()
        self._init_pbd()

    def reset(self, initial_angles: Optional[List[float]] = None) -> None:
        """Reset physics to initial state."""
        self.state = np.zeros(2 * self.n)
        if initial_angles is None:
            self.state[0::2] = np.pi / 2 + np.random.randn(self.n) * 0.05
        else:
            angles = np.array(initial_angles, dtype=float)
            if len(angles) != self.n:
                angles = np.resize(angles, self.n)
            self.state[0::2] = angles
        self.clear_trails()
        self._init_pbd()