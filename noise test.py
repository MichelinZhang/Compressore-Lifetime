import numpy as np
import matplotlib.pyplot as plt
import nidaqmx
from nidaqmx.constants import TerminalConfiguration, AcquisitionType

# ================= 配置区 =================
DEVICE_NAME = "Dev1"     # 您的设备名
AI_CHANNEL = "ai0"       # 您的通道
SAMPLING_RATE = 1000     # 采样率 (Hz)
DURATION = 2.0           # 采集时长 (秒)
# ==========================================

def analyze_noise():
    print(f"正在采集 {DURATION} 秒的数据进行频谱分析...")
    
    # 1. 采集原始数据
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(
            f"{DEVICE_NAME}/{AI_CHANNEL}",
            terminal_config=TerminalConfiguration.RSE
        )
        task.timing.cfg_samp_clk_timing(
            rate=SAMPLING_RATE,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=int(SAMPLING_RATE * DURATION)
        )
        data = task.read(number_of_samples_per_channel=nidaqmx.constants.READ_ALL_AVAILABLE)

    # 2. 转换为 numpy 数组
    y = np.array(data)
    N = len(y)
    x_time = np.linspace(0, DURATION, N)

    # 3. 计算 FFT (频谱)
    yf = np.fft.fft(y)
    xf = np.fft.fftfreq(N, 1 / SAMPLING_RATE)
    
    # 只取正频率部分
    idx = np.where(xf > 0)
    freqs = xf[idx]
    amplitudes = np.abs(yf[idx])

    # 4. 绘图显示
    plt.figure(figsize=(10, 6))
    
    # 图1: 原始波形
    plt.subplot(2, 1, 1)
    plt.plot(x_time, y)
    plt.title("原始压力波形 (Time Domain)")
    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    plt.grid(True)

    # 图2: 频谱图
    plt.subplot(2, 1, 2)
    plt.plot(freqs, amplitudes)
    plt.title("噪音频谱分析 (Frequency Domain)")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    plt.grid(True)
    
    # 找出最大噪音频率
    peak_freq = freqs[np.argmax(amplitudes)]
    print(f"检测到的最强噪音频率: {peak_freq:.1f} Hz")
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    try:
        analyze_noise()
    except Exception as e:
        print(f"错误: {e}")