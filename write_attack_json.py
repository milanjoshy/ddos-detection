import json, time
from pathlib import Path
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)
f = log_dir / 'latest_detection.json'
json.dump({
    'timestamp': time.time(),
    'device_id': 'TEST',
    'is_attack': True,
    'attack_probability': 0.9,
    'packet_rate': 500,
    'byte_rate': 40000,
    'syn_ratio': 0.5,
    'unique_src_ips': 100,
    'tcp_count': 1000,
    'udp_count': 0
}, open(f, 'w'))
print('wrote attack sample')
