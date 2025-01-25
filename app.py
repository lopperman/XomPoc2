from flask import Flask, render_template, request, redirect, url_for
import pika
import json
import uuid
from datetime import datetime
from queue import Queue
from pika.exceptions import StreamLostError, ConnectionClosedByBroker

# Initialize the Flask app
app = Flask(__name__)

# RabbitMQ Connection Pool
class RabbitMQConnectionPool:
    def __init__(self, max_connections=5):
        self.max_connections = max_connections
        self._pool = Queue(max_connections)
        for _ in range(max_connections):
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    heartbeat=600,  # 10-minute heartbeat
                    blocked_connection_timeout=300  # 5-minute timeout
                )
            )
            self._pool.put(connection)

    def get_connection(self):
        return self._pool.get()

    def release_connection(self, connection):
        self._pool.put(connection)

# Initialize the connection pool
connection_pool = RabbitMQConnectionPool()

# Declare queues (ensure they exist)
def declare_queues():
    connection = connection_pool.get_connection()
    channel = connection.channel()
    channel.queue_declare(queue='router_queue', durable=True)
    channel.queue_declare(queue='firewall_queue', durable=True)
    channel.queue_declare(queue='switch_queue', durable=True)
    channel.queue_declare(queue='ip_lookup_queue', durable=True)
    connection_pool.release_connection(connection)

# Declare queues on startup
declare_queues()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        device_type = request.form['device_type']
        fqdn = request.form['fqdn']
        config = request.form['config']
        is_virtual = request.form.get('is_virtual', False)
        ip_address = request.form.get('ip_address', '')

        device_data = {
            'id': str(uuid.uuid4()),
            'device_type': device_type,
            'fqdn': fqdn,
            'config': config,
            'is_virtual': is_virtual == 'true',
            'ip_address': ip_address,
            'history': [{'action': 'submitted', 'timestamp': datetime.now().isoformat()}]
        }

        # Get a connection from the pool
        connection = connection_pool.get_connection()
        channel = connection.channel()

        try:
            # Publish to the appropriate queue based on device type
            if device_type == 'Router':
                channel.basic_publish(exchange='', routing_key='router_queue', body=json.dumps(device_data))
            elif device_type == 'Firewall':
                channel.basic_publish(exchange='', routing_key='firewall_queue', body=json.dumps(device_data))
            elif device_type == 'Switch':
                channel.basic_publish(exchange='', routing_key='switch_queue', body=json.dumps(device_data))
        except (StreamLostError, ConnectionClosedByBroker) as e:
            print(f"Failed to publish message: {e}. Retrying...")
            # Reconnect and retry
            connection = connection_pool.get_connection()
            channel = connection.channel()
            if device_type == 'Router':
                channel.basic_publish(exchange='', routing_key='router_queue', body=json.dumps(device_data))
            elif device_type == 'Firewall':
                channel.basic_publish(exchange='', routing_key='firewall_queue', body=json.dumps(device_data))
            elif device_type == 'Switch':
                channel.basic_publish(exchange='', routing_key='switch_queue', body=json.dumps(device_data))
        finally:
            # Release the connection back to the pool
            connection_pool.release_connection(connection)

        return redirect(url_for('index'))

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)