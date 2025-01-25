import pika
import json
import random
from datetime import datetime

def callback(ch, method, properties, body):
    device_data = json.loads(body)
    print(f"Looking up IP for: {device_data['fqdn']}")

    # Simulate IP lookup
    device_data['ip_address'] = f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
    device_data['history'].append({'action': 'ip_lookup_completed', 'timestamp': datetime.now().isoformat()})

    save_completed_device(device_data)

def save_completed_device(device_data):
    with open(f"completed_devices/{device_data['id']}.json", 'w') as f:
        json.dump(device_data, f)
    print(f"Device {device_data['id']} completed and saved.")

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.basic_consume(queue='ip_lookup_queue', on_message_callback=callback, auto_ack=True)

print('IP Lookup Service is waiting for messages...')
channel.start_consuming()