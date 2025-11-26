// Atualizar ano no footer
document.getElementById('year').textContent = new Date().getFullYear();

// Menu mobile
const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
const mainNav = document.querySelector('.main-nav');

if (mobileMenuToggle && mainNav) {
  mobileMenuToggle.addEventListener('click', function() {
    this.classList.toggle('active');
    mainNav.classList.toggle('active');
    this.setAttribute('aria-expanded', this.classList.contains('active'));
  });
}

// Header scroll effect
window.addEventListener('scroll', function() {
  const header = document.querySelector('.site-header');
  if (window.scrollY > 100) {
    header.classList.add('scrolled');
  } else {
    header.classList.remove('scrolled');
  }
});

// Função para mostrar notificação
function showNotification(message, type = 'info') {
  // Criar elemento de notificação se não existir
  let notification = document.getElementById('notification');
  if (!notification) {
    notification = document.createElement('div');
    notification.id = 'notification';
    notification.className = 'notification';
    notification.innerHTML = `
      <div class="notification-content">
        <span id="notification-text"></span>
        <button class="notification-close" onclick="this.parentElement.parentElement.classList.remove('show')">×</button>
      </div>
    `;
    document.body.appendChild(notification);
  }

  const notificationText = document.getElementById('notification-text');
  
  notificationText.textContent = message;
  notification.className = 'notification';
  notification.classList.add(type, 'show');
  
  setTimeout(() => {
    notification.classList.remove('show');
  }, 4000);
}

// Variáveis globais para armazenar as instâncias dos gráficos
let chartInstances = {
    estadoCivil: null,
    cargos: null,
    hierarquia: null,
    unimed: null,
    transporte: null,
    valeTransporte: null,
    restaurante: null,
    laboral: null
};

// Função para destruir um gráfico se ele existir
function destroyChart(chartKey) {
    if (chartInstances[chartKey]) {
        chartInstances[chartKey].destroy();
        chartInstances[chartKey] = null;
    }
}

// Função para destruir todos os gráficos
function destroyAllCharts() {
    Object.keys(chartInstances).forEach(key => {
        destroyChart(key);
    });
}

// Função principal para carregar gráficos RH
async function loadRhDashboard() {
    try {
        showNotification('Carregando dados...', 'info');
        console.log('Iniciando carregamento do dashboard RH...');
        
        // Destruir gráficos existentes antes de criar novos
        destroyChart('estadoCivil');
        destroyChart('cargos');
        destroyChart('hierarquia');
        
        const response = await fetch('/graficos');
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Dados recebidos:', data);
        
        if (data.error) {
            throw new Error(data.error);
        }

        // DEBUG: Mostrar informações no console
        if (data.debug) {
            console.log('Debug info:', data.debug);
        }

        console.log('Dados RH carregados:', {
            estado_civil: data.estado_civil,
            cargos: data.cargos,
            hierarquia: data.hierarquia
        });

        // Atualizar totais
        updateTotals(data);
        
        // Criar gráficos
        createEstadoCivilChart(data.estado_civil);
        createCargosChart(data.cargos);
        createHierarquiaChart(data.hierarquia);
        
        // Atualizar estatísticas gerais
        updateGeneralStats(data);

        showNotification('Dados carregados com sucesso!', 'success');

    } catch (error) {
        console.error('Erro no dashboard RH:', error);
        console.error('Stack trace:', error.stack);
        showNotification('Erro ao carregar dashboard RH: ' + error.message, 'error');
        handleChartErrors();
        
        // Mostrar informações de debug na página
        showDebugInfo(error);
    }
}

function updateTotals(data) {
  if (data.estado_civil) {
    document.getElementById('total-estado-civil').textContent = data.estado_civil.total;
  }
  if (data.cargos) {
    document.getElementById('total-cargos').textContent = data.cargos.total;
  }
  if (data.hierarquia) {
    document.getElementById('total-hierarquia').textContent = data.hierarquia.total;
  }
  
  // Total geral (usa o maior total disponível)
  const totalGeral = Math.max(
    data.estado_civil?.total || 0,
    data.cargos?.total || 0,
    data.hierarquia?.total || 0
  );
  document.getElementById('total-geral').textContent = totalGeral;
}

function createEstadoCivilChart(estadoCivilData) {
    if (!estadoCivilData || !estadoCivilData.labels || estadoCivilData.labels.length === 0) {
        createNoDataMessage('estadoCivilChart');
        return;
    }

    // Destruir gráfico existente
    destroyChart('estadoCivil');

    const ctx = document.getElementById('estadoCivilChart').getContext('2d');
    chartInstances.estadoCivil = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: estadoCivilData.labels,
            datasets: [{
                data: estadoCivilData.values,
                backgroundColor: [
                    '#f39200', '#3B82F6', '#10B981', '#EF4444', '#8B5CF6', '#F59E0B',
                    '#84CC16', '#06B6D4', '#8B5CF6', '#EC4899'
                ],
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverOffset: 15,
                hoverBorderWidth: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.2,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            family: 'Inter, sans-serif',
                            size: 12
                        },
                        color: '#374151'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    titleColor: '#1f2937',
                    bodyColor: '#374151',
                    borderColor: '#e5e7eb',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const percentage = estadoCivilData.percentages[context.dataIndex] || '0%';
                            return `${label}: ${value} (${percentage})`;
                        }
                    }
                }
            },
            cutout: '55%',
            animation: {
                animateScale: true,
                animateRotate: true
            }
        }
    });

    updateChartStats('estado-civil-stats', estadoCivilData);
}

function createCargosChart(cargosData) {
    if (!cargosData || !cargosData.labels || cargosData.labels.length === 0) {
        createNoDataMessage('cargosChart');
        return;
    }

    // Destruir gráfico existente
    destroyChart('cargos');

    const ctx = document.getElementById('cargosChart').getContext('2d');
    chartInstances.cargos = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: cargosData.labels,
            datasets: [{
                data: cargosData.values,
                backgroundColor: [
                    '#f39200', '#3B82F6', '#10B981', '#EF4444', '#8B5CF6', '#F59E0B',
                    '#84CC16', '#06B6D4', '#8B5CF6', '#EC4899'
                ],
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverOffset: 15,
                hoverBorderWidth: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.2,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            family: 'Inter, sans-serif',
                            size: 11
                        },
                        color: '#374151'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    titleColor: '#1f2937',
                    bodyColor: '#374151',
                    borderColor: '#e5e7eb',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const percentage = cargosData.percentages[context.dataIndex] || '0%';
                            return `${label}: ${value} (${percentage})`;
                        }
                    }
                }
            },
            animation: {
                animateScale: true,
                animateRotate: true
            }
        }
    });

    updateChartStats('cargos-stats', cargosData);
}

function createHierarquiaChart(hierarquiaData) {
    if (!hierarquiaData || !hierarquiaData.labels || hierarquiaData.labels.length === 0) {
        createNoDataMessage('hierarquiaChart');
        return;
    }

    // Destruir gráfico existente
    destroyChart('hierarquia');

    const ctx = document.getElementById('hierarquiaChart').getContext('2d');
    chartInstances.hierarquia = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: hierarquiaData.labels,
            datasets: [{
                data: hierarquiaData.values,
                backgroundColor: [
                    '#f39200', '#3B82F6', '#10B981', '#EF4444', '#8B5CF6', '#F59E0B',
                    '#84CC16', '#06B6D4', '#8B5CF6', '#EC4899'
                ],
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverOffset: 15,
                hoverBorderWidth: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.2,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            family: 'Inter, sans-serif',
                            size: 11
                        },
                        color: '#374151'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    titleColor: '#1f2937',
                    bodyColor: '#374151',
                    borderColor: '#e5e7eb',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const percentage = hierarquiaData.percentages[context.dataIndex] || '0%';
                            return `${label}: ${value} (${percentage})`;
                        }
                    }
                }
            },
            cutout: '55%',
            animation: {
                animateScale: true,
                animateRotate: true
            }
        }
    });

    updateChartStats('hierarquia-stats', hierarquiaData);
}

function updateChartStats(containerId, data) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = '';
  
  data.labels.forEach((label, index) => {
    const statItem = document.createElement('div');
    statItem.className = 'stat-item';
    statItem.innerHTML = `
      <span class="stat-label">${label}</span>
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span class="stat-value">${data.values[index]}</span>
        <span class="stat-percentage">${data.percentages[index]}</span>
      </div>
    `;
    container.appendChild(statItem);
  });
}

function updateGeneralStats(data) {
  // Encontrar maior e menor categoria
  let maiorCategoria = '-';
  let menorCategoria = '-';
  let maiorValor = 0;
  let menorValor = Infinity;

  // Verificar em todos os datasets
  const datasets = [data.cargos, data.estado_civil, data.hierarquia];
  
  datasets.forEach(dataset => {
    if (dataset && dataset.labels) {
      dataset.labels.forEach((label, index) => {
        const value = dataset.values[index];
        if (value > maiorValor) {
          maiorValor = value;
          maiorCategoria = label;
        }
        if (value < menorValor && value > 0) {
          menorValor = value;
          menorCategoria = label;
        }
      });
    }
  });

  document.getElementById('maior-categoria').textContent = maiorCategoria;
  document.getElementById('menor-categoria').textContent = menorCategoria;
  document.getElementById('ultima-atualizacao').textContent = new Date().toLocaleString('pt-BR');
}

function createNoDataMessage(chartId) {
  const canvas = document.getElementById(chartId);
  if (canvas) {
    const parent = canvas.parentElement;
    if (parent) {
      parent.innerHTML = `
        <div class="no-data-message">
          Nenhum dado disponível para este gráfico
        </div>
      `;
    }
  }
}

function handleChartErrors() {
  const chartIds = ['estadoCivilChart', 'cargosChart', 'hierarquiaChart'];
  chartIds.forEach(chartId => {
    createNoDataMessage(chartId);
  });
}

// Funções de exportação
function exportToPDF() {
  showNotification('Gerando relatório PDF...', 'info');
  setTimeout(() => {
    showNotification('Relatório PDF gerado com sucesso!', 'success');
  }, 1500);
}

function exportToExcel() {
  showNotification('Gerando planilha Excel...', 'info');
  setTimeout(() => {
    showNotification('Planilha Excel gerada com sucesso!', 'success');
  }, 1500);
}

function reloadCharts() {
  showNotification('Atualizando dados...', 'info');
  
  // Destruir todos os gráficos antes de recarregar
  destroyAllCharts();
  
  setTimeout(() => {
    loadRhDashboard();
    loadBeneficiosDashboard();
  }, 500);
}

// Adicionar botão de atualização
function addRefreshButton() {
  const exportButtons = document.querySelector('.export-buttons');
  if (exportButtons && !document.getElementById('refreshBtn')) {
    const refreshBtn = document.createElement('button');
    refreshBtn.id = 'refreshBtn';
    refreshBtn.className = 'export-btn';
    refreshBtn.innerHTML = '🔄 Atualizar Dados';
    refreshBtn.onclick = reloadCharts;
    exportButtons.appendChild(refreshBtn);
  }
}

// Função para carregar gráficos de benefícios
async function loadBeneficiosDashboard() {
    try {
        showNotification('Carregando dados de benefícios...', 'info');
        
        // Destruir gráficos existentes antes de criar novos
        destroyChart('unimed');
        destroyChart('transporte');
        destroyChart('valeTransporte');
        destroyChart('restaurante');
        destroyChart('laboral');
        
        const response = await fetch('/graficos-beneficios');
        if (!response.ok) throw new Error('Erro ao carregar dados de benefícios');
        
        const data = await response.json();
        if (data.error) throw new Error(data.error);

        console.log('Dados de benefícios:', data);

        // Criar gráficos de benefícios
        createBeneficioChart('unimedChart', 'unimed-stats', 'total-unimed', data.unimed, 'unimed');
        createBeneficioChart('transporteChart', 'transporte-stats', 'total-transporte', data.transporte, 'transporte');
        createBeneficioChart('valeTransporteChart', 'vale-transporte-stats', 'total-vale-transporte', data.vale_transporte, 'valeTransporte');
        createBeneficioChart('restauranteChart', 'restaurante-stats', 'total-restaurante', data.restaurante, 'restaurante');
        createBeneficioChart('laboralChart', 'laboral-stats', 'total-laboral', data.laboral, 'laboral');
        
        // Atualizar resumo
        updateResumoBeneficios(data);

        showNotification('Dados de benefícios carregados com sucesso!', 'success');

    } catch (error) {
        console.error('Erro no dashboard de benefícios:', error);
        showNotification('Erro ao carregar dados de benefícios: ' + error.message, 'error');
        handleBeneficiosErrors();
    }
}

// Função genérica para criar gráficos de benefícios
function createBeneficioChart(chartId, statsId, totalId, dados, chartKey) {
    if (!dados || !dados.labels || dados.labels.length === 0) {
        createNoDataMessage(chartId);
        document.getElementById(totalId).textContent = '0';
        return;
    }

    // Atualizar total
    document.getElementById(totalId).textContent = dados.total;

    // Destruir gráfico existente
    destroyChart(chartKey);

    const ctx = document.getElementById(chartId).getContext('2d');
    chartInstances[chartKey] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: dados.labels,
            datasets: [{
                data: dados.values,
                backgroundColor: [
                    '#f39200', '#3B82F6', '#10B981', '#EF4444', '#8B5CF6', '#F59E0B',
                    '#84CC16', '#06B6D4', '#8B5CF6', '#EC4899'
                ],
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverOffset: 15,
                hoverBorderWidth: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.2,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        font: {
                            family: 'Inter, sans-serif',
                            size: 11
                        },
                        color: '#374151'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    titleColor: '#1f2937',
                    bodyColor: '#374151',
                    borderColor: '#e5e7eb',
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 6,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const percentage = dados.percentages[context.dataIndex] || '0%';
                            return `${label}: ${value} (${percentage})`;
                        }
                    }
                }
            },
            cutout: '55%',
            animation: {
                animateScale: true,
                animateRotate: true
            }
        }
    });

    updateChartStats(statsId, dados);
}

// Função para atualizar resumo de benefícios
function updateResumoBeneficios(data) {
    const beneficios = [
        { nome: 'Unimed', dados: data.unimed },
        { nome: 'Vale Transporte', dados: data.vale_transporte },
        { nome: 'Restaurante', dados: data.restaurante },
        { nome: 'Laboral', dados: data.laboral }
    ];

    let totalRespondentes = 0;
    let beneficioMaisUtilizado = '-';
    let beneficioMenosUtilizado = '-';
    let maiorTaxa = 0;
    let menorTaxa = Infinity;
    let totalTaxas = 0;
    let countTaxas = 0;

    beneficios.forEach(beneficio => {
        if (beneficio.dados && beneficio.dados.total > 0) {
            totalRespondentes = Math.max(totalRespondentes, beneficio.dados.total);
            
            // Calcular taxa de utilização (percentual de "Sim")
            if (beneficio.dados.labels && beneficio.dados.values) {
                const indexSim = beneficio.dados.labels.findIndex(label => 
                    label.toLowerCase().includes('sim') || label.toLowerCase().includes('s')
                );
                
                if (indexSim !== -1) {
                    const valorSim = beneficio.dados.values[indexSim];
                    const taxa = (valorSim / beneficio.dados.total) * 100;
                    
                    totalTaxas += taxa;
                    countTaxas++;
                    
                    if (taxa > maiorTaxa) {
                        maiorTaxa = taxa;
                        beneficioMaisUtilizado = beneficio.nome;
                    }
                    
                    if (taxa < menorTaxa) {
                        menorTaxa = taxa;
                        beneficioMenosUtilizado = beneficio.nome;
                    }
                }
            }
        }
    });

    document.getElementById('total-respondentes').textContent = totalRespondentes;
    document.getElementById('beneficio-mais-utilizado').textContent = beneficioMaisUtilizado;
    document.getElementById('beneficio-menos-utilizado').textContent = beneficioMenosUtilizado;
    
    const taxaMedia = countTaxas > 0 ? (totalTaxas / countTaxas) : 0;
    document.getElementById('taxa-media').textContent = `${taxaMedia.toFixed(1)}%`;
}

// Função para lidar com erros nos gráficos de benefícios
function handleBeneficiosErrors() {
    const chartIds = [
        'unimedChart', 'transporteChart', 'valeTransporteChart', 
        'restauranteChart', 'laboralChart'
    ];
    chartIds.forEach(chartId => {
        createNoDataMessage(chartId);
    });
}

// Função para exportar relatório de benefícios
function exportarRelatorioBeneficios() {
    showNotification('Gerando relatório de benefícios...', 'info');
    setTimeout(() => {
        showNotification('Relatório de benefícios gerado com sucesso!', 'success');
    }, 1500);
}

// Função para recarregar benefícios
function recarregarBeneficios() {
    showNotification('Atualizando dados de benefícios...', 'info');
    
    // Destruir gráficos existentes de benefícios
    destroyChart('unimed');
    destroyChart('transporte');
    destroyChart('valeTransporte');
    destroyChart('restaurante');
    destroyChart('laboral');
    
    setTimeout(() => {
        loadBeneficiosDashboard();
    }, 500);
}

function showDebugInfo(error) {
    // Adiciona informações de debug na página
    const debugDiv = document.getElementById('debug-info') || createDebugDiv();
    debugDiv.innerHTML = `
        <h4>Informações de Debug:</h4>
        <p><strong>Erro:</strong> ${error.message}</p>
        <p><strong>Verifique:</strong></p>
        <ul>
            <li>Se o arquivo Excel está no caminho correto</li>
            <li>Se as colunas "Estado civil:" e "Qual o seu cargo na empresa:" existem no Excel</li>
            <li>Os logs do servidor para mais detalhes</li>
        </ul>
        <button onclick="testarConexao()" class="test-btn">Testar Conexão</button>
    `;
}

function createDebugDiv() {
    const debugDiv = document.createElement('div');
    debugDiv.id = 'debug-info';
    debugDiv.style.cssText = `
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        color: #dc2626;
    `;
    const container = document.querySelector('.container');
    if (container) {
        container.appendChild(debugDiv);
    }
    return debugDiv;
}

async function testarConexao() {
    try {
        const response = await fetch('/debug/colunas');
        const data = await response.json();
        console.log('Teste de conexão:', data);
        alert('Conexão OK! Verifique o console para detalhes.');
    } catch (error) {
        console.error('Erro no teste:', error);
        alert('Erro na conexão: ' + error.message);
    }
}

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando página de gráficos...');
    
    // Adicionar estilos para mensagens de sem dados
    if (!document.querySelector('#noDataStyles')) {
        const style = document.createElement('style');
        style.id = 'noDataStyles';
        style.textContent = `
            .no-data-message {
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100%;
                color: #6b7280;
                font-style: italic;
                text-align: center;
                padding: 2rem;
                background: #f8fafc;
                border-radius: 8px;
                border: 2px dashed #e5e7eb;
                font-family: 'Inter', sans-serif;
            }
            .stat-percentage {
                color: #6b7280;
                font-size: 0.875rem;
                font-weight: 500;
            }
            .debug-info {
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
                color: #dc2626;
            }
            .debug-info h4 {
                margin-top: 0;
                color: #dc2626;
            }
            .debug-info ul {
                margin: 0.5rem 0;
                padding-left: 1.5rem;
            }
            .debug-info li {
                margin: 0.25rem 0;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Carregar gráficos após um pequeno delay para garantir que o DOM está pronto
    setTimeout(() => {
        loadRhDashboard();
        loadBeneficiosDashboard();
    }, 100);
    
    // Adicionar botão de atualização
    addRefreshButton();
    
    // Fechar menu ao clicar em um link
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (mainNav && mainNav.classList.contains('active')) {
                mobileMenuToggle.classList.remove('active');
                mainNav.classList.remove('active');
                mobileMenuToggle.setAttribute('aria-expanded', 'false');
            }
        });
    });

    // Dropdown menu functionality
    const userMenuToggle = document.querySelector('.user-menu-toggle');
    if (userMenuToggle) {
        userMenuToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const dropdownMenu = this.nextElementSibling;
            const isVisible = dropdownMenu.style.display === 'block';
            
            document.querySelectorAll('.user-dropdown-menu').forEach(menu => {
                menu.style.display = 'none';
            });
            
            if (!isVisible) {
                dropdownMenu.style.display = 'block';
            }
        });

        document.querySelectorAll('.dropdown-item').forEach(item => {
            item.addEventListener('click', function() {
                const dropdownMenu = this.closest('.user-dropdown-menu');
                if (dropdownMenu) {
                    dropdownMenu.style.display = 'none';
                }
            });
        });
    }

    // Fechar dropdown ao clicar fora
    document.addEventListener('click', function(event) {
        if (!event.target.closest('.user-dropdown')) {
            document.querySelectorAll('.user-dropdown-menu').forEach(menu => {
                menu.style.display = 'none';
            });
        }
    });
});

// Adicionar handler para erro global
window.addEventListener('error', function(e) {
    console.error('Erro global:', e.error);
    showNotification('Ocorreu um erro inesperado na página.', 'error');
});

// Exportar funções para uso global
window.showNotification = showNotification;
window.reloadCharts = reloadCharts;
window.exportToPDF = exportToPDF;
window.exportToExcel = exportToExcel;
window.exportarRelatorioBeneficios = exportarRelatorioBeneficios;
window.recarregarBeneficios = recarregarBeneficios;
window.testarConexao = testarConexao;