from flask import Flask, jsonify, request, render_template, send_file, send_from_directory, Response, redirect, url_for
from PIL import Image
import os
import subprocess
import socket


app = Flask(__name__, static_folder='static')

# Répertoire où sont stockés les projets Docker Compose
DOCKER_PROJECTS_PATH = os.getenv("DOCKER_PROJECTS_PATH", "/root/projects-docker-compose")

from concurrent.futures import ThreadPoolExecutor

@app.route('/api/projects', methods=['GET'])
def list_projects():
    """Lister les projets Docker Compose (avec parallélisation du statut)"""
    
    # 🔍 Lister les dossiers valides contenant un docker-compose.yml
    project_dirs = sorted([
        item for item in os.listdir(DOCKER_PROJECTS_PATH)
        if os.path.isdir(os.path.join(DOCKER_PROJECTS_PATH, item)) and
           os.path.exists(os.path.join(DOCKER_PROJECTS_PATH, item, 'docker-compose.yml'))
    ], key=str.lower)  # ⬅️ Tri alphabétique insensible à la casse

    def build_project_entry(item):
        path = os.path.join(DOCKER_PROJECTS_PATH, item)
        status = get_project_status(path)
        return {'name': item, 'status': status}

    # ⚙️ Parallélisation de la construction des entrées
    with ThreadPoolExecutor(max_workers=8) as executor:
        projects = list(executor.map(build_project_entry, project_dirs))

    return jsonify(projects)


def get_project_status(project_path):
    """Vérifier si un projet est en cours d'exécution"""
    result = subprocess.run(['docker', 'compose', 'ps', '-q'], cwd=project_path, capture_output=True, text=True)
    return 'running' if result.stdout.strip() else 'stopped'

@app.route('/api/containers', methods=['GET'])
def list_containers():
    """Lister tous les conteneurs en cours d'exécution"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.ID}} {{.Image}} {{.Names}}'],
            capture_output=True, text=True
        )
        containers = [
            {'id': line.split()[0], 'image': line.split()[1], 'name': line.split()[2]}
            for line in result.stdout.strip().split('\n')
            if line
        ]
        return jsonify(containers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_name>/start', methods=['POST'])
def start_project(project_name):
    """Démarrer un projet Docker Compose"""
    project_path = os.path.join(DOCKER_PROJECTS_PATH, project_name)
    if not os.path.exists(os.path.join(project_path, 'docker-compose.yml')):
        return jsonify({'error': 'Projet introuvable'}), 404

    try:
        subprocess.run(['docker', 'compose', 'up', '-d'], cwd=project_path, check=True)
        return jsonify({'status': 'started', 'project': project_name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_name>/stop', methods=['POST'])
def stop_project(project_name):
    """Arrêter un projet Docker Compose"""
    project_path = os.path.join(DOCKER_PROJECTS_PATH, project_name)
    if not os.path.exists(os.path.join(project_path, 'docker-compose.yml')):
        return jsonify({'error': 'Projet introuvable'}), 404

    try:
        subprocess.run(['docker', 'compose', 'down'], cwd=project_path, check=True)
        return jsonify({'status': 'stopped', 'project': project_name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_name>/restart', methods=['POST'])
def restart_project(project_name):
    """Redémarrer un projet Docker Compose"""
    project_path = os.path.join(DOCKER_PROJECTS_PATH, project_name)
    if not os.path.exists(os.path.join(project_path, 'docker-compose.yml')):
        return jsonify({'error': 'Projet introuvable'}), 404

    try:
        subprocess.run(['docker', 'compose', 'restart'], cwd=project_path, check=True)
        return jsonify({'status': 'restarted', 'project': project_name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/projects/<project_name>/logo.png')
def get_logo(project_name):
    """Servir les logos des projets Docker Compose avec redimensionnement"""
    logo_path = os.path.join(DOCKER_PROJECTS_PATH, project_name, "logo.png")

    if not os.path.exists(logo_path):
        return '', 404  # Retourne 404 si le logo est introuvable
    
    # Charger et redimensionner l’image
    img = Image.open(logo_path)
    img.thumbnail((50, 50))  # Taille maximale sans déformation

    # Sauvegarder l’image temporairement et l’envoyer
    temp_path = f"/tmp/{project_name}_logo_resized.png"
    img.save(temp_path, format="PNG")

    return send_file(temp_path, mimetype='image/png')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


@app.route('/')
def home():
    """Afficher l'interface HTML"""
    return render_template('index.html')



import subprocess

@app.route('/logs/<project_name>')
def get_logs(project_name):
    """Récupérer les logs en streaming, avec gestion insensible à la casse"""
    
    # Trouver le bon nom du conteneur
    result = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"], capture_output=True, text=True)
    container_names = result.stdout.splitlines()
    
    real_name = next((name for name in container_names if name.lower() == project_name.lower()), None)
    
    if not real_name:
        return f"Conteneur '{project_name}' introuvable.", 404
    
    # Lancer les logs Docker en streaming
    def generate():
        log_process = subprocess.Popen(["docker", "logs", "-f", real_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in iter(log_process.stdout.readline, ''):
            yield f"data: {line.strip()}\n\n"  # Format EventSource

    return Response(generate(), content_type='text/event-stream')

@app.route('/compose/<project_name>')
def get_compose_file(project_name):
    """Lire le fichier docker-compose.yml du projet"""
    compose_path = f"{DOCKER_PROJECTS_PATH}/{project_name}/docker-compose.yml"

    if not os.path.exists(compose_path):
        return f"Fichier `docker-compose.yml` introuvable pour {project_name}.", 404

    with open(compose_path, "r") as file:
        content = file.read()

    return Response(content, content_type="text/plain")


@app.route('/edit/<project_name>', methods=['GET'])
def edit_compose(project_name):
    path = os.path.join(DOCKER_PROJECTS_PATH, project_name, 'docker-compose.yml')
    if not os.path.isfile(path):
        return f"Fichier introuvable pour {project_name}", 404

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    return render_template('edit.html', project_name=project_name, compose_content=content)

@app.route('/edit/<project_name>', methods=['POST'])
def save_compose(project_name):
    new_content = request.form['compose_content']
    path = os.path.join(DOCKER_PROJECTS_PATH, project_name, 'docker-compose.yml')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return redirect(url_for('index'))
import subprocess

def get_containers_for_project(project_name):
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        containers = [
            {"name": name}
            for name in result.stdout.strip().split("\n")
            if project_name.lower() in name.lower()
        ]
        return containers

    except subprocess.CalledProcessError as e:
        print(f"Erreur Docker : {e.stderr}")
        return []

@app.route('/api/projects/<project_name>/containers')
def get_project_containers(project_name):
    containers = get_containers_for_project(project_name)
    return jsonify(containers)

@app.route('/')
def index():
    return render_template('index.html')

def get_free_port():
    """Trouve un port libre pour ttyd"""
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def get_server_ip():
    """Renvoie l'IP réseau réelle du serveur (pas 127.0.0.1)"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # ping fictif juste pour récupérer une IP locale
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

import subprocess

def get_shell(container_name):
    # Tester bash
    try:
        subprocess.run(['docker', 'exec', container_name, 'bash', '-c', 'exit'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return 'bash'
    except subprocess.CalledProcessError:
        pass

    # Tester sh
    try:
        subprocess.run(['docker', 'exec', container_name, 'sh', '-c', 'exit'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return 'sh'
    except subprocess.CalledProcessError:
        pass

    return None  # Aucun shell disponible
    
def start_terminal(container, shell, port):
    ttyd_cmd = [
        'ttyd',
        '--port', str(port),
        '--interface', '0.0.0.0',
        'docker', 'exec', '-it', container, shell
    ]
    subprocess.Popen(ttyd_cmd)
    
@app.route('/exec/<container>')
def open_terminal(container):
    """Ouvre une console web vers un conteneur Docker grâce à ttyd en mode conteneurisé"""
    shell = get_shell(container)
    if not shell:
        return f"Aucun shell interactif trouvé dans le conteneur {container}", 500

    port = get_free_port()

    try:
        start_terminal(container, shell, port)
        ip = request.host.split(':')[0]
        return redirect(f"http://{ip}:{port}")
    except Exception as e:
        return f"Erreur lors de l'ouverture du terminal pour {container} : {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
