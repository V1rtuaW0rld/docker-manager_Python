        // Simulation des données (à remplacer par des appels API réels)
        let projects = [];
        let isLoading = false;

        // Fonction pour appeler l'API backend
        async function fetchProjects() {
            try {
                const response = await fetch('/api/projects');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return await response.json();
            } catch (error) {
                console.error('Erreur lors du fetch des projets:', error);
                // Fallback avec des données de démo en cas d'erreur
                return [
                    { name: 'demo-nginx', status: 'stopped', path: '/root/projects-docker-compose/demo-nginx' },
                    { name: 'demo-redis', status: 'running', path: '/root/projects-docker-compose/demo-redis' }
                ];
            }
        }

        // Fonction pour appeler l'API de toggle
        async function toggleProject(projectName) {
            try {
                const response = await fetch(`/api/projects/${projectName}/toggle`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return await response.json();
            } catch (error) {
                console.error('Erreur lors du toggle:', error);
                // Simulation pour le développement
                const project = projects.find(p => p.name === projectName);
                if (project) {
                    project.status = project.status === 'running' ? 'stopped' : 'running';
                    return { success: true, action: 'simulated', project: projectName };
                }
                throw error;
            }
        }

        // Rendu de l'interface
function renderProjects() {
    console.log("Affichage des projets:", projects); // Vérification

    const container = document.getElementById('projects-container');

    if (!projects || projects.length === 0) {
        console.warn("Projets introuvables, maintien de l'affichage actuel.");
        return;
    }

    // Mise à jour des compteurs
    const runningCount = projects.filter(p => p.status === 'running').length;
    const stoppedCount = projects.filter(p => p.status === 'stopped').length;
    document.getElementById('running-count').textContent = runningCount;
    document.getElementById('stopped-count').textContent = stoppedCount;

    // Génération de l'affichage des projets
    container.innerHTML = `
        <div class="projects-grid">
            ${projects.map(project => `
                <div class="project-card ${project.status}">
                    <img src="/projects/${project.name}/logo.png" class="project-logo" 
                         onerror="this.style.display='none'" alt="${project.name} logo">

                    <div class="project-name">${project.name}</div>

                    <div class="project-status">
                        <div class="status-dot ${project.status}"></div>
                        <span class="status-text ${project.status}">
                            ${project.status === 'running' ? 'En cours' : 'Arrêté'}
                        </span>
                    </div>

                    <div class="project-actions">
                    <button class="edit-btn" onclick="viewCompose('${project.name}')">
					<img src="/static/icons/view.png" class="action-icon" alt="Voir" style="width: 40px; height: 20px;">
                    </button>

                      </button>
                      <button class="logs-btn" onclick="viewLogs('${project.name}')">
                      <img src="/static/icons/logs.png" class="action-icon" alt="Logs">
                      </button>
					<div class="console-dropdown">
					<div class="hover-group">
						<img src="/static/icons/console.png" 
							class="btn-console action-icon" 
							data-project="${project.name}" 
							alt="Console">
						<ul class="dropdown-menu hidden"></ul>
					</div>
					</div>
					
   
                    </div>

                    <button class="project-btn ${project.status}"
                            onclick="handleProjectToggle('${project.name}')" id="btn-${project.name}">
                        ${project.status === 'running' ? '⏹️ Arrêter' : '▶️ Démarrer'}
                    </button>
                </div>
            `).join('')}
        </div>
    `;


console.log("→ Attachement listeners sur .btn-console :", document.querySelectorAll('.btn-console').length);




document.querySelectorAll('.btn-console').forEach(btn => {
  const dropdown = btn.nextElementSibling;
  const project = btn.dataset.project;

  // Sécurité : reset si tu survoles plusieurs fois
let hoverTimer;

btn.addEventListener('mouseenter', async () => {
    hoverTimer = setTimeout(async () => {
        console.log("→ Hover détecté sur :", project);

        if (!dropdown.classList.contains('loaded')) {
            try {
                const res = await fetch(`/api/projects/${project}/containers`);
                const containers = await res.json();

                dropdown.innerHTML = '';
                containers.forEach(c => {
                    const li = document.createElement('li');
                    li.textContent = c.name;
                    li.classList.add('dropdown-item');
					li.addEventListener('click', () => {
						window.open(`/exec/${c.name}`, '_blank');
					});

                    dropdown.appendChild(li);
                });

                dropdown.classList.add('loaded');
            } catch (err) {
                dropdown.innerHTML = '<li>⚠️ Erreur chargement</li>';
            }
        }

        dropdown.classList.remove('hidden');
    }, 150);
});

btn.addEventListener('mouseleave', () => {
    clearTimeout(hoverTimer);
    setTimeout(() => dropdown.classList.add('hidden'), 300);
});


});
}

// Gestion du clic sur un projet (démarrer ou arrêter)
async function handleProjectToggle(projectName) {
    const button = document.getElementById(`btn-${projectName}`);
    const originalText = button.textContent;

    // Désactive le bouton et affiche une animation de chargement
    button.disabled = true;
    button.innerHTML = '<div class="spinner"></div> Traitement...';

    try {
        // Détermine si le projet doit être démarré ou arrêté
        const project = projects.find(p => p.name === projectName);
        const action = project.status === 'running' ? 'stop' : 'start';

        // Appelle l'API pour démarrer ou arrêter le projet
        const response = await fetch(`/api/projects/${projectName}/${action}`, { method: 'POST' });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // Met à jour l'état du projet après l'action réussie
        project.status = action === 'start' ? 'running' : 'stopped';
        renderProjects();
    } catch (error) {
        console.error('Erreur:', error);
        button.disabled = false;
        button.textContent = originalText;
        alert('Erreur lors de l\'opération. Veuillez réessayer.');
    }
}

        // Actualisation des projets
        async function refreshProjects() {
            const refreshIcon = document.getElementById('refresh-icon');
            refreshIcon.style.animation = 'spin 1s linear infinite';
            
            isLoading = true;
            renderProjects();

            try {
                projects = await fetchProjects();
                renderProjects();
            } catch (error) {
                console.error('Erreur lors du chargement:', error);
                document.getElementById('projects-container').innerHTML = `
                    <div class="error">
                        ❌ Erreur lors du chargement des projets. Veuillez vérifier la connexion au serveur.
                    </div>
                `;
            } finally {
                isLoading = false;
                refreshIcon.style.animation = '';
            }
        }

        document.addEventListener('DOMContentLoaded', async () => {
    const toOpen = sessionStorage.getItem("reopenProject");

    const refreshed = await refreshProjects(); // ← rend la grille visible

    if (toOpen) {
        // on attend un petit peu que le DOM se stabilise visuellement
        setTimeout(() => {
            console.log("Réouverture différée de :", toOpen);
            viewCompose(toOpen);
            sessionStorage.removeItem("reopenProject");
        }, 200);
    }

    setInterval(refreshProjects, 30000);
});

        // Actualisation lors de la mise au premier plan de la page
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                refreshProjects();
            }
        });
		
function viewLogs(projectName) {
    const overlay = document.getElementById('log-overlay');
    overlay.style.display = "flex"; // Afficher l'overlay

    document.getElementById('log-title').innerText = projectName; // Affiche le nom du projet

    const logContainer = document.getElementById('log-content');
    logContainer.innerHTML = ""; // Nettoyer avant d'afficher de nouveaux logs

    fetch(`/logs/${projectName}`)
        .then(response => {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            function readLogs() {
                reader.read().then(({ done, value }) => {
                    if (done) return;
                    
                    logContainer.innerHTML += `<pre>${decoder.decode(value)}</pre>`;
                    logContainer.scrollTop = logContainer.scrollHeight; // Scroll automatique vers le bas
                    readLogs(); // Continuer la lecture des logs
                });
            }

            readLogs();
        });
}


function closeLogs() {
    document.getElementById('log-overlay').style.display = "none"; // Masquer l'overlay
}

function viewCompose(projectName) {
    const overlay = document.getElementById('compose-overlay');
if (!overlay) {
    console.warn('Impossible d’ouvrir la modale : #compose-overlay introuvable');
    return;
}

    overlay.style.display = "flex"; // Afficher l'overlay

    document.getElementById('compose-title').innerText = projectName; // Affiche le nom du projet

    fetch(`/compose/${projectName}`)
        .then(response => response.text())
        .then(data => {
            document.getElementById('compose-content').innerText = data; // Affichage brut du YAML
        });
}

function closeCompose() {
    document.getElementById('compose-overlay').style.display = "none"; // Masquer l'overlay
}

function redirectToEdit() {
    const projectName = document.getElementById('compose-title').innerText;
    window.location.href = `/edit/${projectName}`;
}

li.addEventListener('click', () => {
    window.open(`/exec/${c.name}`, '_blank');
});


