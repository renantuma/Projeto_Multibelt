// Elementos DOM
const searchBox = document.getElementById('searchBox');
const clearBtn = document.getElementById('clearBtn');
const table = document.getElementById('resultsTable');
const tableHead = document.getElementById('tableHead');
const tableBody = document.getElementById('tableBody');
const noResults = document.getElementById('noResults');
const countSpan = document.getElementById('count');
const loading = document.getElementById('loading');
const tableContainer = document.getElementById('tableContainer');

// Debounce para evitar muitas requisições
function debounce(fn, delay) {
  let timeoutId;
  return function(...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn.apply(this, args), delay);
  };
}

// Função principal de busca
async function doSearch(q) {
  const query = q.trim();
  
  if (!query) {
    hideAll();
    countSpan.textContent = "0";
    return;
  }
  
  try {
    showLoading();
    hideResults();
    
    // URL CORRIGIDA - usando a rota /search do Flask
    const url = `/search?q=${encodeURIComponent(query)}`;
    console.log('Fazendo requisição para:', url);
    
    const res = await fetch(url);
    
    if (!res.ok) {
      throw new Error(`Erro ${res.status}: ${res.statusText}`);
    }
    
    const data = await res.json();
    console.log('Dados recebidos:', data);
    
    hideLoading();
    renderResults(data.columns || [], data.rows || []);
    
  } catch (err) {
    console.error("Erro na busca:", err);
    hideLoading();
    showError(`Erro ao buscar dados: ${err.message}`);
  }
}

// Funções auxiliares para mostrar/ocultar elementos
function hideAll() {
  table.style.display = "none";
  noResults.style.display = "none";
  loading.style.display = "none";
  // Remove avisos anteriores
  const existingWarning = document.querySelector('.results-warning');
  if (existingWarning) {
    existingWarning.remove();
  }
}

function showLoading() {
  hideAll();
  loading.style.display = "block";
}

function hideLoading() {
  loading.style.display = "none";
}

function hideResults() {
  table.style.display = "none";
  noResults.style.display = "none";
}

function showError(message) {
  noResults.innerHTML = message;
  noResults.style.display = "block";
  table.style.display = "none";
}

// Renderizar resultados na tabela
function renderResults(columns, rows) {
  countSpan.textContent = rows.length;
  
  if (!rows || rows.length === 0) {
    showError("Nenhum resultado encontrado. Tente buscar por nome, ID ou CPF.");
    return;
  }
  
  // Remove avisos anteriores
  const existingWarning = document.querySelector('.results-warning');
  if (existingWarning) {
    existingWarning.remove();
  }
  
  // Configurar cabeçalho da tabela
  tableHead.innerHTML = `<tr>${columns.map(col => `<th>${escapeHtml(col)}</th>`).join('')}</tr>`;
  
  // Configurar corpo da tabela (limite de 500 linhas para performance)
  const maxRows = 500;
  const rowsToShow = rows.slice(0, maxRows);
  
  tableBody.innerHTML = rowsToShow.map(row => 
    `<tr>${columns.map(col => `<td>${escapeHtml(row[col] || '')}</td>`).join('')}</tr>`
  ).join('');
  
  // Mostrar tabela
  table.style.display = "table";
  noResults.style.display = "none";
  
  // Scroll suave para a tabela se houver muitos resultados
  if (rows.length > 10) {
    tableContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  
  // Aviso se alguns resultados foram omitidos
  if (rows.length > maxRows) {
    const warning = document.createElement('div');
    warning.className = 'results-warning';
    warning.innerHTML = `Mostrando ${maxRows} de ${rows.length} resultados. Refine sua busca para ver mais resultados.`;
    tableContainer.insertBefore(warning, table);
  }
}

// Escapar HTML para prevenir XSS
function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Configurar eventos
const debouncedSearch = debounce((event) => {
  doSearch(event.target.value);
}, 300);

searchBox.addEventListener('input', debouncedSearch);

clearBtn.addEventListener('click', () => {
  searchBox.value = "";
  searchBox.focus();
  doSearch('');
});

// Focar no campo de busca ao carregar a página
searchBox.focus();

// Buscar parâmetro da URL se existir
function prefillFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get('q');
  if (q) {
    searchBox.value = q;
    doSearch(q);
  }
}

// Atualizar ano no footer
function updateYear() {
  document.getElementById('year').textContent = new Date().getFullYear();
}

// Dropdown menu functionality
function setupDropdown() {
  const userMenuToggle = document.querySelector('.user-menu-toggle');
  if (userMenuToggle) {
    userMenuToggle.addEventListener('click', function(e) {
      e.stopPropagation();
      const dropdownMenu = this.nextElementSibling;
      const isVisible = dropdownMenu.style.display === 'block';
      dropdownMenu.style.display = isVisible ? 'none' : 'block';
    });

    // Fechar dropdown ao clicar fora
    document.addEventListener('click', function() {
      const dropdowns = document.querySelectorAll('.user-dropdown-menu');
      dropdowns.forEach(dropdown => {
        dropdown.style.display = 'none';
      });
    });
  }
}

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
  updateYear();
  setupDropdown();
  prefillFromUrl();
});

// Tecla Enter para buscar
searchBox.addEventListener('keypress', function(e) {
  if (e.key === 'Enter') {
    doSearch(this.value);
  }
});