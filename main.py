from flask import Flask, render_template, request
import simpy
import random
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

app = Flask(__name__)

# Modelo de SimPy
def simulate_queue(arrival_rate, service_rate, num_customers, queue_method, max_wait_time, capacity_resource):
    #Se crea el entorno de simulacion
    env = simpy.Environment()
    
    # Crear el recurso basado en el método de cola elegido
    if queue_method == "FIFO":
        server = simpy.Resource(env, capacity=capacity_resource)
    else:
        server = simpy.PriorityResource(env, capacity=capacity_resource)
    
    wait_times = []  # Lista para almacenar los tiempos de espera de los clientes que usan el recurso
    num_retiros = 0  # Contador de clientes que se retiran de la cola

    # Definir la lógica de un cliente en el sistema
    def customer(env, name, server, priority=0):
        nonlocal num_retiros  # Permite modificar el contador num_retiros dentro de esta función
        arrival_time = env.now  # Tiempo de llegada del cliente
        
        # Solicitar acceso al recurso
        if queue_method == 'FIFO':
            #el uso del with garantiza q el recurso se liberara cuando se salga del contexto
            with server.request() as request:
                # Esperar por el recurso o el tiempo máximo de espera
                result = yield request | env.timeout(max_wait_time)
                if request in result:
                    # Si se obtuvo el recurso, calcular el tiempo de espera y usar el recurso
                    wait = env.now - arrival_time
                    wait_times.append(wait)
                    #simulamos con la distribucion exponencial el tiempo en el que se usara el recurso
                    yield env.timeout(service_rate)
                else:
                    # Si se supera el tiempo máximo de espera, el cliente se retira
                    num_retiros += 1
                    
        else:
            with server.request(priority=priority) as request:
                result = yield request | env.timeout(max_wait_time)
                if request in result:
                    wait = env.now - arrival_time
                    wait_times.append(wait)
                    yield env.timeout(service_rate)
                else:
                    num_retiros += 1
                   

    # Configurar el proceso de llegada de clientes
    def setup(env, arrival_rate, server):
        for i in range(num_customers):
            #usamos poisson para la llegada de clientes
            yield env.timeout(arrival_rate)
            #al usar -i los cliente que mas tarde lleguen tendran prioridad
            priority = -i if queue_method == 'LIFO' else 0  # Asignar prioridad si LIFO
            #creamos un nuevo proceso simpy, y llamamos a customer q es quien describe el comportamiento del cliente
            env.process(customer(env, f'Customer {i+1}', server, priority))

    env.process(setup(env, arrival_rate, server))  # Iniciar el proceso de setup
    env.run()  # Ejecutar la simulación hasta que se procesen todos los clientes

    return wait_times, num_retiros

# Cálculo de estadísticas
def calculate_statistics(wait_times):
    # Calcular estadísticas básicas de los tiempos de espera
    mean = np.mean(wait_times)
    median = np.median(wait_times)
    std_dev = np.std(wait_times)
    variance = np.var(wait_times)
    max_wait = np.max(wait_times)
    min_wait = np.min(wait_times)
    
    return round(mean,2), round(median,2), round(std_dev,2), round(variance,2), round(max_wait,2), round(min_wait,2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    # Obtener los datos del formulario
    arrival_rate = float(request.form['arrival_rate'])
    service_rate = float(request.form['service_rate'])
    num_customers = int(request.form['num_customers'])
    max_wait_time = float(request.form['max_wait_time'])
    capacity_resourse = int(request.form['capacity_resourse'])
    queue_method = request.form['queue_method']

    # Ejecutar la simulación de la cola
    wait_times, num_retiros = simulate_queue(arrival_rate, service_rate, num_customers, queue_method, max_wait_time, capacity_resourse)

    # Calcular estadísticas de los tiempos de espera
    mean, median, std_dev, variance, max_wait, min_wait = calculate_statistics(wait_times)

    # Crear gráficos de histograma y de cajas y bigotes
    plt.figure(figsize=(15, 5))

    # Histograma de los tiempos de espera
    plt.subplot(1, 2, 1)
    plt.hist(wait_times, bins=30, edgecolor='k')
    plt.title('Distribución de Tiempos de Espera')
    plt.xlabel('Tiempo de Espera')
    plt.ylabel('Frecuencia')

    # Diagrama de cajas y bigotes
    plt.subplot(1, 2, 2)
    plt.boxplot(wait_times, vert=False)
    plt.title('Diagrama de Cajas y Bigotes')
    plt.xlabel('Tiempo de Espera')

    # Guardar los gráficos en formato base64 para incluirlos en la respuesta HTML
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url_histogram = base64.b64encode(img.getvalue()).decode('utf8')

    plt.close()



    # Renderizar la plantilla result.html con los gráficos y estadísticas
    return render_template('result.html', plot_url_histogram=plot_url_histogram, mean=mean, median=median, 
                           std_dev=std_dev, variance=variance, max_wait=max_wait, min_wait=min_wait,
                           num_retiros=num_retiros)

if __name__ == '__main__':
    app.run(debug=True)