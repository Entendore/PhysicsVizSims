# double_pendulum.py
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Params
g = 9.81
m1, m2 = 1.0, 1.0
L1, L2 = 1.0, 1.0
dt = 0.02
T = 20.0

# state: [theta1, omega1, theta2, omega2]
state = np.array([1.0, 0.0, 0.5, 0.0])

def derivs(s):
    th1, w1, th2, w2 = s
    dth1 = w1
    dth2 = w2

    delta = th2 - th1
    denom1 = (m1 + m2)*L1 - m2*L1*np.cos(delta)*np.cos(delta)
    denom2 = (L2/L1)*denom1

    # Equations from standard double pendulum derivation
    num1 = m2*L1*w1*w1*np.sin(delta)*np.cos(delta) + m2*g*np.sin(th2)*np.cos(delta) + m2*L2*w2*w2*np.sin(delta) - (m1 + m2)*g*np.sin(th1)
    a1 = num1 / denom1

    num2 = -m2*L2*w2*w2*np.sin(delta)*np.cos(delta) + (m1 + m2)*(g*np.sin(th1)*np.cos(delta) - L1*w1*w1*np.sin(delta) - g*np.sin(th2))
    a2 = num2 / denom2

    return np.array([dth1, a1, dth2, a2])

def rk4_step(s, dt):
    k1 = derivs(s)
    k2 = derivs(s + 0.5*dt*k1)
    k3 = derivs(s + 0.5*dt*k2)
    k4 = derivs(s + dt*k3)
    return s + (dt/6.0)*(k1 + 2*k2 + 2*k3 + k4)

nsteps = int(T/dt)
history = np.zeros((nsteps, 4))
times = np.linspace(0, T, nsteps)

for i in range(nsteps):
    history[i] = state
    state = rk4_step(state, dt)

# convert to positions
x1 = L1 * np.sin(history[:,0])
y1 = -L1 * np.cos(history[:,0])
x2 = x1 + L2 * np.sin(history[:,2])
y2 = y1 - L2 * np.cos(history[:,2])

# animate
fig, ax = plt.subplots(figsize=(6,6))
ax.set_xlim(-(L1+L2)*1.2, (L1+L2)*1.2)
ax.set_ylim(-(L1+L2)*1.2, (L1+L2)*1.2)
line, = ax.plot([], [], 'o-', lw=2)
trace, = ax.plot([], [], '-', lw=1, alpha=0.6)
time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes)

trail_len = int(1.0/dt)  # 1-second trail

def init():
    line.set_data([], [])
    trace.set_data([], [])
    time_text.set_text('')
    return line, trace, time_text

def animate(i):
    xs = [0, x1[i], x2[i]]
    ys = [0, y1[i], y2[i]]
    line.set_data(xs, ys)
    start = max(0, i-trail_len)
    trace.set_data(x2[start:i+1], y2[start:i+1])
    time_text.set_text(f't={times[i]:.2f}s')
    return line, trace, time_text

ani = animation.FuncAnimation(fig, animate, frames=nsteps, interval=dt*1000, blit=True, init_func=init)
plt.title("Double Pendulum")
plt.show()
