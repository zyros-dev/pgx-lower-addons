from flask import Flask, render_template_string
import psutil
import time

app = Flask(__name__)

start_time = time.time()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Server Health</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .status {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        h1 { color: #4a3d8f; margin-top: 0; }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .metric:last-child { border-bottom: none; }
        .label { font-weight: 600; }
        .value { color: #666; }
        .bar {
            height: 20px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }
        .bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #48bb78, #38a169);
            transition: width 0.3s;
        }
        .bar-fill.warning { background: linear-gradient(90deg, #ed8936, #dd6b20); }
        .bar-fill.danger { background: linear-gradient(90deg, #f56565, #e53e3e); }
        .uptime { font-size: 2rem; color: #4a3d8f; font-weight: bold; }
    </style>
</head>
<body>
    <div class="status">
        <h1>🐘 Server Health Monitor</h1>
        <div class="metric">
            <span class="label">Uptime</span>
            <span class="uptime">{{ uptime }}</span>
        </div>
    </div>

    <div class="status">
        <h2>CPU</h2>
        <div class="metric">
            <span class="label">Usage</span>
            <span class="value">{{ cpu }}%</span>
        </div>
        <div class="bar">
            <div class="bar-fill {{ 'danger' if cpu > 80 else ('warning' if cpu > 60 else '') }}"
                 style="width: {{ cpu }}%"></div>
        </div>
    </div>

    <div class="status">
        <h2>Memory</h2>
        <div class="metric">
            <span class="label">Used / Total</span>
            <span class="value">{{ mem_used }} MB / {{ mem_total }} MB</span>
        </div>
        <div class="bar">
            <div class="bar-fill {{ 'danger' if mem_percent > 80 else ('warning' if mem_percent > 60 else '') }}"
                 style="width: {{ mem_percent }}%"></div>
        </div>
    </div>

    <div class="status">
        <h2>Swap</h2>
        <div class="metric">
            <span class="label">Used / Total</span>
            <span class="value">{{ swap_used }} MB / {{ swap_total }} MB</span>
        </div>
        <div class="bar">
            <div class="bar-fill {{ 'danger' if swap_percent > 80 else ('warning' if swap_percent > 60 else '') }}"
                 style="width: {{ swap_percent }}%"></div>
        </div>
    </div>

    <div class="status">
        <h2>Disk</h2>
        <div class="metric">
            <span class="label">Used / Total</span>
            <span class="value">{{ disk_used }} GB / {{ disk_total }} GB</span>
        </div>
        <div class="bar">
            <div class="bar-fill {{ 'danger' if disk_percent > 80 else ('warning' if disk_percent > 60 else '') }}"
                 style="width: {{ disk_percent }}%"></div>
        </div>
    </div>

    <p style="text-align: center; color: #999; margin-top: 20px;">Auto-refreshes every 5 seconds</p>
</body>
</html>
"""

@app.route('/')
def health():
    uptime = int(time.time() - start_time)
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60
    uptime_str = f"{hours}h {minutes}m"

    cpu = round(psutil.cpu_percent(interval=0.1), 1)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage('/')

    return render_template_string(
        HTML_TEMPLATE,
        uptime=uptime_str,
        cpu=cpu,
        mem_used=round(mem.used / 1024 / 1024, 1),
        mem_total=round(mem.total / 1024 / 1024, 1),
        mem_percent=round(mem.percent, 1),
        swap_used=round(swap.used / 1024 / 1024, 1),
        swap_total=round(swap.total / 1024 / 1024, 1),
        swap_percent=round(swap.percent, 1),
        disk_used=round(disk.used / 1024 / 1024 / 1024, 1),
        disk_total=round(disk.total / 1024 / 1024 / 1024, 1),
        disk_percent=round(disk.percent, 1)
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
