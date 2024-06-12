from flask import Flask, render_template, request
import simpy
import random
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

app = Flask(__name__)  # Inicializa la aplicación Flask

# Modelo de SimPy sin aleatoriedad
def simulate_queue(arrival_rate, service_rate, num_customers, queue_method):
    env = simpy.Environment()  # Crea el entorno de simulación
    if queue_method == "FIFO":
        server = simpy.Resource(env, capacity=1)  # Define un recurso FIFO (Primero en llegar, primero en ser atendido)
    else:
        server = simpy.PriorityResource(env, capacity=1)  # Define un recurso LIFO (Último en llegar, primero en ser atendido) con prioridad
    wait_times = []  # Lista para almacenar los tiempos de espera de los clientes

    def customer(env, name, server, priority=0):
        """
        Proceso de un cliente.
        El cliente solicita el recurso y registra su tiempo de espera.
        """
        arrival_time = env.now  # Tiempo de llegada del cliente
        # Solicita el recurso con prioridad si no es FIFO, de lo contrario sin prioridad
        with server.request(priority=priority) if queue_method != 'FIFO' else server.request() as request:
            yield request  # Espera a que el recurso esté disponible
            wait = env.now - arrival_time  # Calcula el tiempo de espera
            wait_times.append(wait)  # Almacena el tiempo de espera
            yield env.timeout(1 / service_rate)  # Simula el tiempo de servicio determinístico

    def setup(env, arrival_rate, server):
        """
        Configura la llegada de clientes.
        Los clientes llegan a intervalos determinísticos definidos por la tasa de llegada.
        """
        interval = 1 / arrival_rate  # Intervalo determinístico entre llegadas
        for i in range(num_customers):
            env.process(customer(env, f'Customer {i+1}', server, priority=-i if queue_method == 'LIFO' else 0))
            yield env.timeout(interval)  # Intervalo determinístico para la próxima llegada

    env.process(setup(env, arrival_rate, server))  # Inicia el proceso de llegada de clientes
    env.run()  # Ejecuta la simulación hasta que todos los eventos hayan sido procesados

    return wait_times  # Devuelve los tiempos de espera recopilados

# Cálculo de estadísticas
def calculate_statistics(wait_times):
    """
    Calcula estadísticas básicas de los tiempos de espera.
    """
    mean = np.mean(wait_times)  # Media
    median = np.median(wait_times)  # Mediana
    std_dev = np.std(wait_times)  # Desviación estándar
    variance = np.var(wait_times)  # Varianza
    max_wait = np.max(wait_times)  # Tiempo de espera máximo
    min_wait = np.min(wait_times)  # Tiempo de espera mínimo
    
    return mean, median, std_dev, variance, max_wait, min_wait  # Devuelve las estadísticas

@app.route('/')
def index():
    """
    Renderiza la página principal.
    """
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    """
    Ejecuta la simulación en respuesta a una solicitud POST.
    Recoge parámetros del formulario, ejecuta la simulación y muestra los resultados.
    """
    arrival_rate = float(request.form['arrival_rate'])  # Recoge la tasa de llegada
    service_rate = float(request.form['service_rate'])  # Recoge la tasa de servicio
    num_customers = int(request.form['num_customers'])  # Recoge el número de clientes
    queue_method = request.form['queue_method']  # Recoge el método de cola (FIFO o LIFO)

    wait_times = simulate_queue(arrival_rate, service_rate, num_customers, queue_method)  # Ejecuta la simulación

    mean, median, std_dev, variance, max_wait, min_wait = calculate_statistics(wait_times)  # Calcula las estadísticas

    # Crear gráfico de distribución de tiempos de espera
    plt.figure(figsize=(10, 5))
    plt.hist(wait_times, bins=30, edgecolor='k')
    plt.title('Distribución de Tiempos de Espera')
    plt.xlabel('Tiempo de Espera')
    plt.ylabel('Frecuencia')

    # Guardar gráfico en formato base64 para incrustarlo en HTML
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')

    return render_template('result.html', plot_url=plot_url, mean=mean, median=median, 
                           std_dev=std_dev, variance=variance, max_wait=max_wait, min_wait=min_wait)

if __name__ == '__main__':
    app.run(debug=True)  # Ejecuta la aplicación Flask en modo de depuración