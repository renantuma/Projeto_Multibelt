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
  const notification = document.getElementById('notification');
  const notificationText = document.getElementById('notification-text');
  
  notificationText.textContent = message;
  notification.className = 'notification';
  notification.classList.add(type, 'show');
  
  setTimeout(() => {
    notification.classList.remove('show');
  }, 4000);
}

// Função para simular teste de funcionalidade
async function testFunctionality() {
  const testButton = document.getElementById('testButton');
  const btnText = testButton.querySelector('.btn-text');
  
  // Estado de carregamento
  testButton.classList.add('loading');
  btnText.textContent = 'Testando...';
  
  try {
    // Simular uma requisição de teste
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Simular sucesso (80% de chance) ou erro (20% de chance)
    const isSuccess = Math.random() > 0.2;
    
    if (isSuccess) {
      testButton.classList.add('success');
      btnText.textContent = 'Sucesso!';
      showNotification('Funcionalidade testada com sucesso! Todos os sistemas estão operando normalmente.', 'success');
    } else {
      testButton.classList.add('error');
      btnText.textContent = 'Erro!';
      showNotification('Falha no teste. Verifique a conexão e tente novamente.', 'error');
    }
    
    // Restaurar estado normal após 2 segundos
    setTimeout(() => {
      testButton.classList.remove('loading', 'success', 'error');
      btnText.textContent = 'Testar Funcionalidade';
    }, 2000);
    
  } catch (error) {
    console.error('Erro no teste:', error);
    testButton.classList.add('error');
    btnText.textContent = 'Erro!';
    showNotification('Erro inesperado durante o teste.', 'error');
    
    // Restaurar estado normal após 2 segundos
    setTimeout(() => {
      testButton.classList.remove('loading', 'error');
      btnText.textContent = 'Testar Funcionalidade';
    }, 2000);
  }
}

// Adicionar evento de clique ao botão de teste
document.getElementById('testButton').addEventListener('click', testFunctionality);

// Dados mock para o gráfico (substituir por dados reais da API)
const mockChartData = {
  total: 245,
  labels: ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Porto Alegre", "Curitiba", "Salvador"],
  values: [85, 42, 38, 28, 25, 27],
  percentages: ["34.7%", "17.1%", "15.5%", "11.4%", "10.2%", "11.0%"]
};

async function loadChart() {
  try {
    // Tentar carregar dados da API, usar mock se falhar
    let data;
    try {
      const res = await fetch('{{ url_for("chart_data") }}');
      if (res.ok) {
        data = await res.json();
      } else {
        throw new Error('API não disponível');
      }
    } catch (error) {
      console.warn('Usando dados mock para o gráfico:', error);
      data = mockChartData;
    }

    // Atualiza o total de trabalhadores
    document.getElementById('total-trabalhadores').textContent = data.total;

    // Cria a lista de cidades
    const cidadesList = document.getElementById('cidades-list');
    cidadesList.innerHTML = '';
    
    data.labels.forEach((cidade, index) => {
      const div = document.createElement('div');
      div.style.padding = '5px 0';
      div.style.borderBottom = '1px solid #eee';
      div.innerHTML = `<strong>${cidade}:</strong> ${data.values[index]} (${data.percentages[index]})`;
      cidadesList.appendChild(div);
    });

    // Cria o gráfico de pizza
    const ctx = document.getElementById('miniChart').getContext('2d');
    new Chart(ctx, {
      type: 'pie',
      data: {
        labels: data.labels,
        datasets: [{
          data: data.values,
          backgroundColor: [
            '#f39200', '#2b2b2b', '#4CAF50', '#2196F3', 
            '#9C27B0', '#FF9800', '#795548', '#607D8B'
          ],
          borderWidth: 2,
          borderColor: '#fff',
          hoverOffset: 15
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: {
              boxWidth: 12,
              padding: 15,
              color: '#fff',
              font: {
                family: 'Inter, sans-serif'
              }
            }
          },
          tooltip: {
            backgroundColor: 'rg(26, 26, 26, 0.9)',
            titleColor: '#fff',
            bodyColor: '#fff',
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.raw || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value} (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  } catch (error) {
    console.error('Erro ao carregar gráfico:', error);
    showNotification('Erro ao carregar dados do gráfico.', 'error');
  }
}

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
  loadChart();
  
  // Fechar menu ao clicar em um link
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      if (mainNav.classList.contains('active')) {
        mobileMenuToggle.classList.remove('active');
        mainNav.classList.remove('active');
        mobileMenuToggle.setAttribute('aria-expanded', 'false');
      }
    });
  });
});