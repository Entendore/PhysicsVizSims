# single_pendulum.py
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Parameters
g = 9.81
L = 1.0      # length (m)
m = 1.0      # mass (kg)
b = 0.0      # damping coefficient (viscous)
dt = 0.02
T = 20.0

# Initial state: theta (rad), omega (rad/s)
state = np.array([1.0, 0.0])

def derivatives(s):
    theta, omega = s
    dtheta = omega
    domega = - (g/L) * np.sin(theta) - (b/m)*omega
    return np.array([dtheta, domega])

def rk4_step(s, dt):
    k1 = derivatives(s)
    k2 = derivatives(s + 0.5*dt*k1)
    k3 = derivatives(s + 0.5*dt*k2)
    k4 = derivatives(s + dt*k3)
    return s + (dt/6.0)*(k1 + 2*k2 + 2*k3 + k4)

# Prepare time series
nsteps = int(T/dt)
thetas = np.zeros(nsteps)
times = np.linspace(0, T, nsteps)

for i in range(nsteps):
    thetas[i] = state[0]
    state = rk4_step(state, dt)

# Animation
fig, ax = plt.subplots(figsize=(5,5))
ax.set_xlim(-L*1.2, L*1.2)
ax.set_ylim(-L*1.2, L*1.2)
line, = ax.plot([], [], 'o-', lw=3)
time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes)

def init():
    line.set_data([], [])
    time_text.set_text('')
    return line, time_text

def animate(i):
    th = thetas[i]
    x = L * np.sin(th)
    y = -L * np.cos(th)
    line.set_data([0, x], [0, y])
    time_text.set_text(f't = {times[i]:.2f}s')
    return line, time_text

ani = animation.FuncAnimation(fig, animate, frames=nsteps, interval=dt*1000, blit=True, init_func=init)
plt.title("Single Pendulum")
plt.show()
