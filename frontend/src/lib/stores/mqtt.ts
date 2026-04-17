import { writable, get } from 'svelte/store';
import mqtt, { type MqttClient } from 'mqtt';

type MqttStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

function createMqttStore() {
  const status = writable<MqttStatus>('disconnected');
  const lastError = writable<string>('');

  let client: MqttClient | null = null;

  function connect(aioUsername: string, aioKey: string) {
    if (client) return;
    status.set('connecting');

    client = mqtt.connect('wss://io.adafruit.com:443/mqtt', {
      username: aioUsername,
      password: aioKey,
      clientId: `workshop-pwa-${Math.random().toString(16).slice(2, 8)}`,
      keepalive: 60,
      reconnectPeriod: 5000,
    });

    client.on('connect', () => status.set('connected'));
    client.on('error', (err) => {
      lastError.set(err.message);
      status.set('error');
    });
    client.on('close', () => {
      if (get(status) === 'connected') status.set('disconnected');
    });
  }

  function disconnect() {
    client?.end(true);
    client = null;
    status.set('disconnected');
  }

  function publish(topic: string, payload: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!client || get(status) !== 'connected') {
        reject(new Error('MQTT not connected'));
        return;
      }
      client.publish(topic, payload, { qos: 1 }, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }

  return { status, lastError, connect, disconnect, publish };
}

export const mqttStore = createMqttStore();
