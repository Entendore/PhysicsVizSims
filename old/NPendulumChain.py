# n_pendulum_verlet.py
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Parameters
g = np.array([0, -9.81])   # gravity vector
dt = 0.02
T = 20.0
num_steps = int(T / dt)

N = 8  # number of pendulum links
L = 0.5  # length of each link (m)
origin = np.array([0.0, 0.0])

# Initialize positions in a straight line downwards
pos = np.zeros((N,2))
for i in range(N):
    pos[i] = origin + np.array([0.0, -(i+1)*L])

# previous positions (for Verlet) - start at rest
prev = pos.copy()

# give a small kick to the last bob for dynamics
pos[-1] += np.array([0.2, 0.0])

# constraints: each adjacent pair must be distance L. The first mass is fixed at origin
def satisfy_constraints(pos, origin, L, iterations=10):
    # fix first to origin
    pos[0] = origin
    for _ in range(iterations):
        for i in range(N-1):
            p1 = pos[i]
            p2 = pos[i+1]
            delta = p2 - p1
            dist = np.linalg.norm(delta)
            if dist == 0:
                continue
            diff = (dist - L) / dist
            # how to distribute correction:
            if i == 0:
                # p1 is fixed -> move only p2
                pos[i+1] -= delta * diff
            else:
                pos[i] -= 0.5 * delta * diff
                pos[i+1] += 0.5 * delta * diff
    pos[0] = origin

# storage for animation
xs = np.zeros((num_steps, N))
ys = np.zeros((num_steps, N))

for t in range(num_steps):
    # Verlet integration step
    accel = np.tile(g, (N,1))  # gravity applied to all
    new = 2*pos - prev + accel * dt*dt
    # first particle is anchored at origin -> keep it
    new[0] = origin

    prev = pos.copy()
    pos = new.copy()

    satisfy_constraints(pos, origin, L, iterations=15)

    xs[t] = pos[:,0]
    ys[t] = pos[:,1]

# Animation
fig, ax = plt.subplots(figsize=(6,6))
R = N*L
ax.set_xlim(-R-0.2, R+0.2)
ax.set_ylim(-R-0.2, 0.2)
line, = ax.plot([], [], 'o-', lw=3)
time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes)

def init():
    line.set_data([], [])
    time_text.set_text('')
    return line, time_text

def animate(i):
    line.set_data(xs[i], ys[i])
    time_text.set_text(f't={i*dt:.2f}s')
    return line, time_text

ani = animation.FuncAnimation(fig, animate, frames=num_steps, interval=dt*1000, blit=True, init_func=init)
plt.title(f"{N}-pendulum chain (Verlet constraints)")
plt.show()
