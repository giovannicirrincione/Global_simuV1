from flask import Flask, render_template, request
import simpy
import random
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

app = Flask(__name__)

# Modelo de SimPy
def simulate_queue(arrival_rate, service_rate, num_customers, queue_method):
    env = simpy.Environment()
    if queue_method == "FIFO":
        server = simpy.Resource(env, capacity=1)
    else:
        server = simpy.PriorityResource(env, capacity=1)
    wait_times = []

    def customer(env, name, server, priority=0):
        arrival_time = env.now
        if queue_method == 'FIFO':
            with server.request() as request:
                yield request
                wait = env.now - arrival_time
                wait_times.append(wait)
                yield env.timeout(random.expovariate(service_rate))
        else:
            with server.request(priority=priority) as request:
                yield request
                wait = env.now - arrival_time
                wait_times.append(wait)
                yield env.timeout(random.expovariate(service_rate))

    def setup(env, arrival_rate, server):
        for i in range(num_customers):
            yield env.timeout(random.expovariate(arrival_rate))
            priority = -i if queue_method == 'LIFO' else 0
            env.process(customer(env, f'Customer {i+1}', server, priority))

    env.process(setup(env, arrival_rate, server))
    env.run()

    return wait_times

# Cálculo de estadísticas
def calculate_statistics(wait_times):
    mean = np.mean(wait_times)
    median = np.median(wait_times)
    std_dev = np.std(wait_times)
    variance = np.var(wait_times)
    max_wait = np.max(wait_times)
    min_wait = np.min(wait_times)
    
    return mean, median, std_dev, variance, max_wait, min_wait

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    arrival_rate = float(request.form['arrival_rate'])
    service_rate = float(request.form['service_rate'])
    num_customers = int(request.form['num_customers'])
    queue_method = request.form['queue_method']

    wait_times = simulate_queue(arrival_rate, service_rate, num_customers, queue_method)

    mean, median, std_dev, variance, max_wait, min_wait = calculate_statistics(wait_times)

    # Crear gráfico de histograma y de cajas y bigotes
    plt.figure(figsize=(15, 5))

    # Histograma
    plt.subplot(1, 2, 1)
    plt.hist(wait_times, bins=30, edgecolor='k')
    plt.title('Distribución de Tiempos de Espera')
    plt.xlabel('Tiempo de Espera')
    plt.ylabel('Frecuencia')

    # Cajas y Bigotes
    plt.subplot(1, 2, 2)
    plt.boxplot(wait_times, vert=False)
    plt.title('Diagrama de Cajas y Bigotes')
    plt.xlabel('Tiempo de Espera')

    # Guardar ambos gráficos en formato base64
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url_histogram = base64.b64encode(img.getvalue()).decode('utf8')

    plt.close()

    return render_template('result.html', plot_url_histogram=plot_url_histogram, mean=mean, median=median, 
                           std_dev=std_dev, variance=variance, max_wait=max_wait, min_wait=min_wait)

if __name__ == '__main__':
    app.run(debug=True)