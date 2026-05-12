import sys, subprocess, numpy as np, random
from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsEllipseItem
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor

# =====================
# CONFIG
# =====================
WIDTH, HEIGHT = 800, 600
FPS = 60
SAMPLE_RATE = 44100
VIDEO_FILENAME = "simulation_streamed.mp4"

# =====================
# BALL CLASS
# =====================
class Ball(QGraphicsEllipseItem):
    def __init__(self, x, y, vx, vy, r=20):
        super().__init__(-r, -r, r*2, r*2)
        self.setBrush(QBrush(QColor(random.randint(50,255), random.randint(50,255), random.randint(50,255))))
        self.setPos(x,y)
        self.vx, self.vy = vx, vy
        self.r = r

    def move(self, w, h):
        self.setPos(self.x()+self.vx, self.y()+self.vy)
        collisions=[]
        if self.x()-self.r < 0 or self.x()+self.r > w:
            self.vx *= -1
            collisions.append(abs(self.vx))
        if self.y()-self.r < 0 or self.y()+self.r > h:
            self.vy *= -1
            collisions.append(abs(self.vy))
        return collisions

# =====================
# SIMPLE COLLISION DETECTION
# =====================
def handle_collision(b1, b2):
    dx = b1.x()-b2.x()
    dy = b1.y()-b2.y()
    dist = (dx**2+dy**2)**0.5
    if dist < b1.r+b2.r:
        b1.vx, b2.vx = b2.vx, b1.vx
        b1.vy, b2.vy = b2.vy, b1.vy
        return [np.hypot(b1.vx,b1.vy)]
    return []

# =====================
# AUDIO SYNTH
# =====================
def generate_wave(freq, duration, volume=0.2, waveform='sine', pan=0.5):
    t = np.linspace(0, duration, int(SAMPLE_RATE*duration), endpoint=False)
    if waveform=='sine':
        sig = np.sin(2*np.pi*freq*t)
    elif waveform=='square':
        sig = np.sign(np.sin(2*np.pi*freq*t))
    elif waveform=='triangle':
        sig = 2*np.abs(2*((t*freq)%1)-1)-1
    else:
        sig = np.sin(2*np.pi*freq*t)
    # stereo pan
    left = sig * np.sqrt(1-pan) * volume
    right = sig * np.sqrt(pan) * volume
    return np.stack([left,right], axis=-1)

# =====================
# MAIN APPLICATION
# =====================
class Simulation:
    def __init__(self):
        self.app = QApplication(sys.argv)
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        self.scene = QGraphicsScene(0,0,WIDTH,HEIGHT)
        self.view = QGraphicsView(self.scene)
        self.view.resize(WIDTH, HEIGHT)
        self.view.show()

        # create balls
        self.balls = [Ball(random.randint(50,WIDTH-50), random.randint(50,HEIGHT-50),
                           random.uniform(-5,5), random.uniform(-5,5)) for _ in range(5)]
        for b in self.balls:
            self.scene.addItem(b)

        # FFmpeg process
        self.ffmpeg = subprocess.Popen([
            'ffmpeg',
            '-y',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WIDTH}x{HEIGHT}', '-r', str(FPS), '-i', 'pipe:0',
            '-f', 'f32le', '-ar', str(SAMPLE_RATE), '-ac', '2', '-i', 'pipe:1',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', VIDEO_FILENAME
        ], stdin=subprocess.PIPE)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(int(1000/FPS))

    def grab_frame(self):
        img = self.view.grab().toImage().convertToFormat(4) # QImage.Format_RGB888
        width, height = img.width(), img.height()
        ptr = img.bits()
        ptr.setsize(height*width*3)
        arr = np.array(ptr, dtype=np.uint8).reshape((height,width,3))
        return arr

    def update_simulation(self):
        collision_positions=[]
        for ball in self.balls:
            events = ball.move(WIDTH, HEIGHT)
            if events:
                collision_positions.append((ball.x(), ball.y(), events[0]))
        for i in range(len(self.balls)):
            for j in range(i+1,len(self.balls)):
                events = handle_collision(self.balls[i], self.balls[j])
                if events:
                    x = (self.balls[i].x()+self.balls[j].x())/2
                    y = (self.balls[i].y()+self.balls[j].y())/2
                    collision_positions.append((x,y,events[0]))

        # generate audio
        frame_audio = np.zeros((int(SAMPLE_RATE/FPS),2), dtype=np.float32)
        for x,y,speed in collision_positions:
            freq = 200 + speed*200
            waveform = random.choice(['sine','square','triangle'])
            volume = min(speed/20,0.5)
            pan = np.clip(x/WIDTH,0,1)
            vol_y = 1 - np.clip(y/HEIGHT,0,0.5)
            tone = generate_wave(freq, duration=1/FPS, volume=volume*vol_y, waveform=waveform, pan=pan)
            frame_audio[:len(tone)] += tone

        frame_audio = np.nan_to_num(frame_audio, nan=0.0, posinf=1.0, neginf=-1.0)
        frame_audio = np.clip(frame_audio, -1.0, 1.0)

        frame = self.grab_frame()
        try:
            self.ffmpeg.stdin.write(frame.astype(np.uint8).tobytes())
            self.ffmpeg.stdin.write(frame_audio.astype(np.float32).tobytes())
        except BrokenPipeError:
            print("FFmpeg closed pipe. Exiting.")
            self.timer.stop()
            return

    def run(self):
        sys.exit(self.app.exec())

# =====================
# RUN
# =====================
if __name__=="__main__":
    sim = Simulation()
    sim.run()
