# 🐍 Base Python minimaliste
FROM python:3.10-slim

# 🧰 Installer pip + Docker CLI
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y \
    docker-ce-cli \
    && pip install --no-cache-dir --upgrade pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
  docker.io \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# 📦 Dépendances pour compiler ttyd
RUN apt-get update && apt-get install -y \
    build-essential cmake git libjson-c-dev libwebsockets-dev \
    && git clone https://github.com/tsl0922/ttyd.git /opt/ttyd \
    && cd /opt/ttyd && mkdir build && cd build \
    && cmake .. && make && make install \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 📁 Répertoire de travail
WORKDIR /app

# 📦 Copier les fichiers du projet
COPY . /app

# 📦 Installer les dépendances du projet Flask
RUN pip install --no-cache-dir -r requirements.txt

# 🌍 Variables d’environnement
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV DOCKER_PROJECTS_PATH="/root/projects-docker-compose"

# 🔓 Port exposé par Flask
EXPOSE 5000

# 🚀 Lancer Flask en threaded
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--with-threads"]
