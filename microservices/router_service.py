import pika
import json
from datetime import datetime

def callback(ch, method, properties, body):
    device_data = json.loads(body)
    print(f"Processing Router: {device_data['fqdn']}")

    # Simulate processing
    device_data['history'].append({'action': 'processed_by_router_service', 'timestamp': datetime.now().isoformat()})

    # If IP address is missing, route to IP Lookup Service
    if not device_data['ip_address']:
        channel.basic_publish(exchange='', routing_key='ip_lookup_queue', body=json.dumps(device_data))
    else:
        save_completed_device(device_data)

def save_completed_device(device_data):
    with open(f"completed_devices/{device_data['id']}.json", 'w') as f:
        json.dump(device_data, f)
    print(f"Device {device_data['id']} completed and saved.")

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.basic_consume(queue='router_queue', on_message_callback=callback, auto_ack=True)

print('Router Service is waiting for messages...')
channel.start_consuming()