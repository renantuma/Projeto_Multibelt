from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
import pandas as pd
import unicodedata
import re
import os
from datetime import datetime
import logging
from database import init_db, Usuario

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# Inicializa o banco de dados
init_db()

# Caminho do Excel
excel_path = r"C:\Users\renan\OneDrive\Área de Trabalho\Multibelt_Final\excel\- Coleta de dados dos colaboradores -.xlsx"

# Cache de dados
data_cache = {
    'df': pd.DataFrame(),
    'last_loaded': None,
    'col_mappings': {}
}

def carregar_excel():
    """Carrega o arquivo Excel e configura as colunas com cache"""
    global data_cache
    
    try:
        # Verifica se precisa recarregar (a cada 5 minutos)
        if (data_cache['last_loaded'] and 
            (datetime.now() - data_cache['last_loaded']).total_seconds() < 300 and
            not data_cache['df'].empty):
            return True
            
        logger.info(f"Carregando Excel: {excel_path}")
        df = pd.read_excel(excel_path).fillna("")
        logger.info(f"Excel carregado com sucesso! Shape: {df.shape}")
        
        # Log de todas as colunas disponíveis para debug
        logger.info("=== COLUNAS DISPONÍVEIS NO EXCEL ===")
        for i, col in enumerate(df.columns):
            logger.info(f"  {i}: '{col}'")
        logger.info("=====================================")
        
        # Detecta automaticamente as colunas - NOME EXATO DA COLUNA
        cols = df.columns.tolist()
        col_mappings = {
            # CORREÇÃO: Busca pela coluna exata "Digite seu nome completo:"
            'nome': encontrar_coluna(cols, ['digite seu nome completo:', 'digite seu nome completo', 'nome completo', 'nome']),
            'cpf': encontrar_coluna(cols, ['digite seu cpf:', 'digite seu cpf', 'cpf']),
            'id': encontrar_coluna(cols, ['digite seu rgi:', 'digite seu rgi', 'rgi', 'id']),
            'cidade': encontrar_coluna(cols, ['em qual cidade você mora', 'cidade']),
            'estado_civil': encontrar_coluna(cols, ['estado civil:', 'estado civil']),
            'cargo': encontrar_coluna(cols, ['qual o seu cargo na empresa', 'cargo']),
            'genero': encontrar_coluna(cols, ['gênero', 'genero']),
            'unimed': encontrar_coluna(cols, ['unimed']),
            'transporte': encontrar_coluna(cols, ['meio de transporte', 'transporte']),
            'vale_transporte': encontrar_coluna(cols, ['vale transporte']),
            'restaurante': encontrar_coluna(cols, ['restaurante']),
            'laboral': encontrar_coluna(cols, ['laboral'])
        }
        
        # VERIFICAÇÃO CRÍTICA - Se não encontrou a coluna de nome, busca manualmente
        if not col_mappings['nome']:
            logger.warning("🚨 COLUNA DE NOME NÃO ENCONTRADA AUTOMATICAMENTE! Buscando manualmente...")
            # Busca manual pela coluna exata
            for col in df.columns:
                if str(col).lower() == 'digite seu nome completo:':
                    col_mappings['nome'] = col
                    logger.info(f"✅ Coluna de nome encontrada manualmente: '{col}'")
                    break
        
        # Log do mapeamento final
        logger.info("=== MAPEAMENTO FINAL DE COLUNAS ===")
        for key, value in col_mappings.items():
            status = "✅" if value else "❌"
            logger.info(f"  {status} {key}: '{value}'")
        logger.info("===================================")
        
        # Pré-computa versões normalizadas para busca
        if col_mappings['nome']:
            df['_norm_nome'] = df[col_mappings['nome']].astype(str).apply(normalize_text)
            # Log de exemplo para debug
            sample_names = df[col_mappings['nome']].head(3).tolist()
            sample_norm = df['_norm_nome'].head(3).tolist()
            logger.info(f"📝 Exemplo de nomes: {sample_names} -> normalizados: {sample_norm}")
            
            # Verifica se há dados reais na coluna
            nomes_validos = df[col_mappings['nome']].dropna()
            logger.info(f"📊 Total de nomes válidos: {len(nomes_validos)}")
            if len(nomes_validos) > 0:
                logger.info(f"📋 Primeiros nomes: {nomes_validos.head(5).tolist()}")
        else:
            logger.error("❌ COLUNA DE NOME NÃO MAPEADA - BUSCA POR NOME NÃO FUNCIONARÁ!")
            df['_norm_nome'] = ""
            
        if col_mappings['cpf']:
            df['_norm_cpf'] = df[col_mappings['cpf']].astype(str).apply(lambda s: re.sub(r"\D", "", str(s)))
        else:
            df['_norm_cpf'] = ""
            
        if col_mappings['id']:
            df['_norm_id'] = df[col_mappings['id']].astype(str).apply(lambda s: str(s).strip().lower())
        else:
            df['_norm_id'] = ""
        
        # Atualiza cache
        data_cache['df'] = df
        data_cache['col_mappings'] = col_mappings
        data_cache['last_loaded'] = datetime.now()
        
        logger.info(f"✅ Cache atualizado com {len(df)} registros")
        return True
        
    except Exception as e:
        logger.error(f"❌ ERRO ao carregar Excel: {e}")
        import traceback
        traceback.print_exc()
        data_cache['df'] = pd.DataFrame()
        return False

def encontrar_coluna(colunas, termos_busca):
    """Encontra uma coluna baseada em termos de busca"""
    # Primeiro: busca exata (case insensitive)
    for coluna in colunas:
        coluna_normalizada = str(coluna).lower().strip()
        for termo in termos_busca:
            termo_normalizado = termo.lower().strip()
            if coluna_normalizada == termo_normalizado:
                logger.info(f"✅ ENCONTRADA COLUNA POR BUSCA EXATA: '{coluna}' para termo '{termo}'")
                return coluna
    
    # Segundo: busca por substring
    for coluna in colunas:
        coluna_lower = str(coluna).lower()
        for termo in termos_busca:
            termo_lower = termo.lower()
            if termo_lower in coluna_lower:
                logger.info(f"✅ ENCONTRADA COLUNA POR SUBSTRING: '{coluna}' para termo '{termo}'")
                return coluna
    
    logger.warning(f"❌ NENHUMA COLUNA ENCONTRADA para termos: {termos_busca}")
    return None

def normalize_text(s: str) -> str:
    """Normaliza texto para busca: remove acentos, caracteres especiais e espaços extras"""
    if pd.isna(s) or s is None:
        return ""
    s = str(s)
    # remove acentos
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # deixa só letras, números e espaços
    s = re.sub(r"[^0-9A-Za-z\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower()

def limpar_texto(texto):
    """Remove acentos, converte para minúsculas e tira espaços extras."""
    if not isinstance(texto, str) or pd.isna(texto):
        return ''
    texto = texto.strip().lower()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto


# Middleware para verificar autenticação
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'error')
            return redirect(url_for('login'))
        if session.get('usuario_nome') != 'admin_MultiBelt':
            flash('Acesso não autorizado. Apenas administradores podem acessar esta página.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Rotas de autenticação
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('Por favor, preencha todos os campos.', 'error')
                return render_template('login.html')
            
            # Verifica se é email ou username
            if '@' in username:
                usuario = Usuario.buscar_por_email(username)
            else:
                usuario = Usuario.buscar_por_username(username)
            
            if usuario and usuario.verificar_senha(password):
                session['usuario_id'] = usuario.id
                session['usuario_nome'] = usuario.username
                session.permanent = True
                
                logger.info(f"Login bem-sucedido: {usuario.username}")
                flash('Login realizado com sucesso!', 'success')
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True, 
                        'redirect': url_for('admin')
                    })
                
                return redirect(url_for('admin'))
            else:
                flash('Usuário ou senha incorretos!', 'error')
                
        except Exception as e:
            logger.error(f"ERRO no login: {str(e)}")
            flash('Erro interno do sistema. Tente novamente.', 'error')
    
    return render_template('login.html')

@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    """Página para recuperação de senha"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            flash('Por favor, informe seu email.', 'error')
            return render_template('esqueci-senha.html')
        
        # Aqui você pode implementar a lógica de recuperação de senha
        # Por exemplo, enviar email com link de redefinição
        
        flash('Se o email existir em nosso sistema, você receberá instruções para redefinir sua senha.', 'info')
        return redirect(url_for('login'))
    
    return render_template('esqueci-senha.html')

@app.route('/criar_conta', methods=['GET', 'POST'])
def criar_conta():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm-password', '')
        
        # Validações
        if not all([username, email, password]):
            flash('Todos os campos são obrigatórios!', 'error')
            return render_template('criar-conta.html')
        
        if password != confirm_password:
            flash('As senhas não coincidem!', 'error')
            return render_template('criar-conta.html')
        
        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres!', 'error')
            return render_template('criar-conta.html')
        
        # Tenta criar o usuário
        if Usuario.criar_usuario(username, email, password):
            flash('Conta criada com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username ou email já estão em uso!', 'error')
    
    return render_template('criar-conta.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('home'))

# Rotas principais
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/sobre')
def sobre():
    return render_template('segunda-tela.html')

@app.route('/admin')
@login_required
@admin_required
def admin():
    """Página administrativa com busca de colaboradores"""
    # Carrega o Excel para garantir que os dados estão disponíveis
    excel_carregado = carregar_excel() and not data_cache['df'].empty
    
    # Obtém informações básicas para mostrar na página
    df = data_cache['df'] if excel_carregado else pd.DataFrame()
    col_mappings = data_cache['col_mappings'] if excel_carregado else {}
    
    # Informações para debug
    estado_civil_col = col_mappings.get('estado_civil', 'Não encontrada')
    cargo_col = col_mappings.get('cargo', 'Não encontrada')
    nome_col = col_mappings.get('nome', 'Não encontrada')
    total_colaboradores = len(df) if not df.empty else 0
    
    # Log para debug
    logger.info(f"Renderizando admin - Nome: {nome_col}, Estado Civil: {estado_civil_col}, Cargo: {cargo_col}")
    
    return render_template(
        'index.html',  # CORRIGIDO: usando index.html
        estado_civil_col=estado_civil_col,
        cargo_col=cargo_col,
        nome_col=nome_col,
        total_colaboradores=total_colaboradores,
        excel_carregado=excel_carregado
    )

# Rotas de dados
@app.route('/chart-data')
@login_required
def chart_data():
    """Dados para o gráfico de distribuição por cidade"""
    try:
        if not carregar_excel() or data_cache['df'].empty:
            return jsonify({'error': 'Arquivo Excel não carregado'})

        df = data_cache['df']
        col_mappings = data_cache['col_mappings']
        
        coluna_cidade = col_mappings.get('cidade')
        if not coluna_cidade:
            return jsonify({'error': 'Coluna de cidade não encontrada'})

        # Processa dados de cidade
        cidades_limpa = df[coluna_cidade].dropna().astype(str).apply(limpar_texto)

        # Dicionário para corrigir grafias diferentes
        substituicoes = {
            'ibipora': 'Ibiporã', 'ibiporã': 'Ibiporã', 'londrina': 'Londrina',
            'cambe': 'Cambé', 'varzea grande': 'Várzea Grande', 
            'jandaia do sul': 'Jandaia do Sul', 'arapongas': 'Arapongas',
            'jataizinho': 'Jataizinho', 'pitangueiras': 'Pitangueiras',
            'rancho alegre': 'Rancho Alegre', 'tamarana': 'Tamarana',
        }

        cidades_padronizadas = cidades_limpa.map(lambda x: substituicoes.get(x, x.title()))
        cidade_counts = cidades_padronizadas.value_counts()

        # Prepara os dados pro gráfico
        labels = [str(x) for x in cidade_counts.index]
        values = [int(x) for x in cidade_counts.values]
        total = int(sum(values))
        percentages = [f"{round((v / total) * 100, 1)}%" for v in values] if total > 0 else []

        return jsonify({
            'labels': labels,
            'values': values,
            'percentages': percentages,
            'total': total
        })

    except Exception as e:
        logger.error(f"Erro em chart-data: {e}")
        return jsonify({'error': str(e)})

@app.route('/graficos')
@login_required
def graficos():
    """Dados para os gráficos de RH (Estado Civil, Cargos, etc.) - API para AJAX"""
    try:
        logger.info("=== INICIANDO PROCESSAMENTO DE GRÁFICOS ===")
        
        if not carregar_excel() or data_cache['df'].empty:
            logger.error("Excel não carregado")
            return jsonify({'error': 'Arquivo Excel não carregado'})

        df = data_cache['df']
        col_mappings = data_cache['col_mappings']

        logger.info("Processando gráficos de RH...")
        logger.info(f"Coluna estado civil: '{col_mappings.get('estado_civil')}'")
        logger.info(f"Coluna cargo: '{col_mappings.get('cargo')}'")
        logger.info(f"Total de linhas no DataFrame: {len(df)}")

        # DEBUG DETALHADO: Verificar se as colunas existem e mostrar dados
        estado_civil_col = col_mappings.get('estado_civil')
        cargo_col = col_mappings.get('cargo')
        
        if estado_civil_col and estado_civil_col in df.columns:
            estado_civil_data = df[estado_civil_col].dropna()
            logger.info(f"Estado Civil - Total respostas: {len(estado_civil_data)}")
            logger.info(f"Estado Civil - Valores únicos: {estado_civil_data.astype(str).unique().tolist()}")
        else:
            logger.warning(f"Coluna estado civil não encontrada: {estado_civil_col}")
        
        if cargo_col and cargo_col in df.columns:
            cargo_data = df[cargo_col].dropna()
            logger.info(f"Cargo - Total respostas: {len(cargo_data)}")
            logger.info(f"Cargo - Valores únicos: {cargo_data.astype(str).unique().tolist()}")
        else:
            logger.warning(f"Coluna cargo não encontrada: {cargo_col}")

        # Processa diferentes tipos de dados
        logger.info("Processando estado civil...")
        dados_estado_civil = processar_estado_civil(estado_civil_col)
        
        logger.info("Processando cargos...")
        dados_cargos = processar_cargos(cargo_col)
        
        logger.info("Processando gênero por estado civil...")
        dados_genero_estado_civil = processar_genero_estado_civil(
            col_mappings.get('genero'), 
            estado_civil_col
        )
        
        logger.info("Processando hierarquia...")
        dados_hierarquia = processar_hierarquia(dados_cargos)

        logger.info("=== FINALIZADO PROCESSAMENTO DE GRÁFICOS ===")

        return jsonify({
            'estado_civil': dados_estado_civil,
            'cargos': dados_cargos,
            'genero_estado_civil': dados_genero_estado_civil,
            'hierarquia': dados_hierarquia,
            'debug': {
                'estado_civil_col': estado_civil_col,
                'cargo_col': cargo_col,
                'total_linhas': len(df)
            }
        })

    except Exception as e:
        logger.error(f"Erro em graficos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

def processar_estado_civil(coluna):
    """Processa coluna de estado civil"""
    if not coluna or coluna not in data_cache['df'].columns:
        logger.warning(f"Coluna de estado civil não encontrada: '{coluna}'")
        return criar_dados_vazios("Estado Civil")
    
    df = data_cache['df']
    logger.info(f"Processando estado civil da coluna: '{coluna}'")
    
    # Verifica se há dados na coluna
    if df[coluna].isna().all():
        logger.warning(f"Coluna '{coluna}' está vazia")
        return criar_dados_vazios("Estado Civil")
    
    # Pega os dados e remove valores vazios
    dados = df[coluna].dropna()
    logger.info(f"Total de respostas de estado civil: {len(dados)}")
    
    # Converte para string e aplica limpeza
    dados_limpos = dados.astype(str).apply(limpar_texto)
    
    # Log para debug - mostra valores únicos ANTES do mapeamento
    logger.info(f"Valores únicos em estado civil (limpos): {dados_limpos.unique()}")
    
    # Mapeamento para estado civil - MAIS ABRANGENTE
    mapeamento = {
        'solteiro': 'Solteiro(a)', 
        'solteira': 'Solteiro(a)', 
        'solteiro.': 'Solteiro(a)',
        'solteiro (a)': 'Solteiro(a)', 
        'solteiro(a)': 'Solteiro(a)', 
        'solteiro (a).': 'Solteiro(a)',
        'solteiroa': 'Solteiro(a)',
        'solteiroo': 'Solteiro(a)',
        
        'casado': 'Casado(a)', 
        'casada': 'Casado(a)', 
        'casado.': 'Casado(a)',
        'casado (a)': 'Casado(a)', 
        'casado(a)': 'Casado(a)', 
        'casado (a).': 'Casado(a)',
        'casadoa': 'Casado(a)',
        
        'divorciado': 'Divorciado(a)', 
        'divorciada': 'Divorciado(a)', 
        'divorciado.': 'Divorciado(a)',
        'divorciado (a)': 'Divorciado(a)', 
        'divorciado(a)': 'Divorciado(a)',
        
        'viuvo': 'Viúvo(a)', 
        'viuva': 'Viúvo(a)', 
        'viuvo.': 'Viúvo(a)',
        
        'uniao estavel': 'União Estável',
        'uniao estável': 'União Estável',
        'união estável': 'União Estável',
        'uniaoestavel': 'União Estável',
        
        'separado': 'Separado(a)', 
        'separada': 'Separado(a)',
        'separado judicialmente': 'Separado(a)'
    }
    
    # Aplica o mapeamento, mantendo o original se não encontrar
    dados_mapeados = dados_limpos.map(lambda x: mapeamento.get(x, x.title()))
    
    # Log para debug - mostra valores únicos DEPOIS do mapeamento
    logger.info(f"Valores únicos em estado civil (mapeados): {dados_mapeados.unique()}")
    
    contagem = dados_mapeados.value_counts()
    
    logger.info(f"Contagem estado civil: {contagem.to_dict()}")
    
    labels = [str(x) for x in contagem.index]
    values = [int(x) for x in contagem.values]
    total = sum(values)
    percentages = [f"{round((v / total) * 100, 1)}%" for v in values] if total > 0 else []
    
    return {
        'labels': labels,
        'values': values,
        'percentages': percentages,
        'total': total
    }

def processar_cargos(coluna):
    """Processa coluna de cargos"""
    if not coluna or coluna not in data_cache['df'].columns:
        logger.warning(f"Coluna de cargo não encontrada: '{coluna}'")
        return criar_dados_vazios("Cargos")
    
    df = data_cache['df']
    logger.info(f"Processando cargos da coluna: '{coluna}'")
    
    # Verifica se há dados na coluna
    if df[coluna].isna().all():
        logger.warning(f"Coluna '{coluna}' está vazia")
        return criar_dados_vazios("Cargos")
    
    # Pega os dados e remove valores vazios
    dados = df[coluna].dropna()
    logger.info(f"Total de respostas de cargos: {len(dados)}")
    
    # Converte para string e aplica limpeza
    dados_limpos = dados.astype(str).apply(limpar_texto)
    
    # Log para debug - mostra valores únicos ANTES do mapeamento
    logger.info(f"Valores únicos em cargos (limpos): {dados_limpos.unique()}")
    
    # Mapeamento de cargos - MAIS SIMPLES E DIRETO
    mapeamento_cargos = {
        # Operacional/Produção
        'operador': 'Operacional', 
        'operadora': 'Operacional', 
        'auxiliar': 'Operacional',
        'auxiliar de producao': 'Operacional', 
        'costureira': 'Operacional',
        'operador de empilhadeira': 'Operacional', 
        'operador de prensa': 'Operacional',
        'motorista': 'Operacional', 
        'servico geral': 'Operacional', 
        'expedicao': 'Operacional',
        'expedidor': 'Operacional', 
        'almoxarifado': 'Operacional', 
        'funcionario': 'Operacional',
        'abrir ponta embalagem prensa': 'Operacional', 
        'auxiliar administrativo': 'Operacional',
        'auxiliar comercial': 'Operacional', 
        'auxiliar no setor comercial': 'Operacional',
        'aux almoxarifado': 'Operacional', 
        'auxiliar de producao solda': 'Operacional',
        
        # Técnico/Correias
        'tecnico em correias': 'Técnico Correias', 
        'tecnico em correia': 'Técnico Correias',
        'tecnico de correia': 'Técnico Correias', 
        'tecnico em correias i': 'Técnico Correias',
        'tecnico em correias ii': 'Técnico Correias', 
        'tecnico em correia i': 'Técnico Correias',
        'tecnico em correias 1': 'Técnico Correias', 
        'tecnico em correia 1': 'Técnico Correias',
        'tecnico em correias i d': 'Técnico Correias', 
        'tec em correias 1': 'Técnico Correias',
        'tec em corria i b': 'Técnico Correias', 
        'tecnico de correia operador 4.5': 'Técnico Correias', 
        'tecno de correia': 'Técnico Correias',
        'tecnico de correio': 'Técnico Correias', 
        'tecno em correias trabalho no insumos': 'Técnico Correias',
        'tec em correias ii': 'Técnico Correias', 
        'tecnico 2': 'Técnico Correias',
        
        # Técnico/Borracha
        'tecnico em borracha': 'Técnico Borracha', 
        'tecnico de borracha': 'Técnico Borracha',
        'tecnico em borracha operador de maquina': 'Técnico Borracha',
        
        # Técnico/Qualidade
        'inspetor de qualidade': 'Técnico Qualidade', 
        'inspetora de qualidade': 'Técnico Qualidade',
        'tec de qualidade': 'Técnico Qualidade',
        
        # Analistas
        'analista': 'Analista',
        'analista de suporte junior': 'Analista', 
        'analista de comercio exterior': 'Analista',
        'analista de credito': 'Analista', 
        'analista de pcp': 'Analista', 
        'analista de pcm': 'Analista',
        'analista de rh': 'Analista', 
        'analista finaceiro': 'Analista', 
        'analista de compras': 'Analista',
        'analista de ti': 'Analista',
        
        # Assistentes
        'assistente': 'Assistente',
        'assistente de logistica': 'Assistente', 
        'assistente de compras': 'Assistente',
        'assistente de sac': 'Assistente', 
        'assistente de inteligencia comercial': 'Assistente',
        'assistente de cobranca': 'Assistente',
        
        # Comercial/Vendas
        'comercial': 'Comercial',
        'vendedor': 'Comercial',
        'consultor': 'Comercial',
        'consultora de vendas': 'Comercial', 
        'consultor comercial': 'Comercial',
        'consultor externo de vendas': 'Comercial', 
        'vendedor externo': 'Comercial',
        
        # Gerência
        'gerente': 'Gerência',
        'gerente de producao': 'Gerência', 
        'gerente de qualidade': 'Gerência',
        'gerente nacional de vendas': 'Gerência', 
        'gerente de marketing': 'Gerência',
        'gerente de filial': 'Gerência', 
        'gerente de vendas': 'Gerência',
        'gerente de produtos industriais': 'Gerência',
        
        # Supervisão/Coordenação
        'supervisor': 'Supervisão',
        'coordenador': 'Supervisão',
        'lider': 'Supervisão',
        'encarregado': 'Supervisão',
        'supervisor de correia em v e expedicao': 'Supervisão', 
        'sup producao': 'Supervisão',
        'supervisor contabil': 'Supervisão', 
        'lider de producao': 'Supervisão',
        'lider de setor': 'Supervisão', 
        'encarregado de producao': 'Supervisão',
        'coordenadora administrativa': 'Supervisão',
        'coordenador de pcp': 'Supervisão', 
        'coordenador de manutencao': 'Supervisão',
        
        # Estagiários
        'estagiario': 'Estagiário', 
        'estagiária': 'Estagiário',
        'estagiario(a)': 'Estagiário',
        
        # Outros Especializados
        'designer': 'Especializado',
        'designer grafico': 'Especializado', 
        'importacoes': 'Especializado',
        'ergometria': 'Especializado'
    }

    def mapear_cargo(cargo):
        cargo_limpo = limpar_texto(cargo)
        
        # Verifica mapeamentos específicos primeiro
        for key, value in mapeamento_cargos.items():
            if key in cargo_limpo:
                return value
        
        # Fallback para categorias gerais baseado em palavras-chave
        if any(palavra in cargo_limpo for palavra in ['tecnico', 'tecnica', 'tec']):
            return 'Técnico'
        elif 'analista' in cargo_limpo:
            return 'Analista'
        elif 'assistente' in cargo_limpo:
            return 'Assistente'
        elif any(palavra in cargo_limpo for palavra in ['gerente', 'gestor']):
            return 'Gerência'
        elif any(palavra in cargo_limpo for palavra in ['supervisor', 'coordenador', 'lider', 'encarregado']):
            return 'Supervisão'
        elif any(palavra in cargo_limpo for palavra in ['vendedor', 'consultor', 'comercial']):
            return 'Comercial'
        elif any(palavra in cargo_limpo for palavra in ['operador', 'auxiliar', 'motorista', 'expedidor']):
            return 'Operacional'
        else:
            return 'Outros'

    cargos_padronizados = dados_limpos.apply(mapear_cargo)
    
    # Log dos cargos mapeados
    logger.info(f"Cargos mapeados: {cargos_padronizados.unique()}")
    
    contagem = cargos_padronizados.value_counts()
    logger.info(f"Contagem cargos: {contagem.to_dict()}")

    # Agrupa categorias com poucos registros
    min_registros = max(1, len(dados_limpos) * 0.03)  # Reduzido para 3% para capturar mais categorias
    contagem_filtrada = contagem[contagem >= min_registros]
    outros = contagem[contagem < min_registros].sum()
    
    if outros > 0:
        contagem_filtrada['Outros'] = outros

    labels = [str(x) for x in contagem_filtrada.index]
    values = [int(x) for x in contagem_filtrada.values]
    total = sum(values)
    percentages = [f"{round((v / total) * 100, 1)}%" for v in values] if total > 0 else []
    
    return {
        'labels': labels,
        'values': values,
        'percentages': percentages,
        'total': total
    }

def processar_genero_estado_civil(coluna_genero, coluna_estado_civil):
    """Processa dados de gênero por estado civil"""
    if not coluna_genero or not coluna_estado_civil:
        return criar_dados_grafico_barras_vazio()
    
    df = data_cache['df']
    
    try:
        df_filtrado = df[[coluna_genero, coluna_estado_civil]].dropna()
        
        # Limpa e padroniza os dados
        df_filtrado['genero_limpo'] = df_filtrado[coluna_genero].astype(str).apply(limpar_texto)
        df_filtrado['genero_limpo'] = df_filtrado['genero_limpo'].map({
            'masculino': 'Masculino', 'm': 'Masculino', 'homem': 'Masculino',
            'feminino': 'Feminino', 'f': 'Feminino', 'mulher': 'Feminino'
        })

        df_filtrado['estado_civil_limpo'] = df_filtrado[coluna_estado_civil].astype(str).apply(limpar_texto)
        df_filtrado['estado_civil_limpo'] = df_filtrado['estado_civil_limpo'].map({
            'casado': 'Casado(a)', 'casada': 'Casado(a)', 'solteiro': 'Solteiro(a)', 'solteira': 'Solteiro(a)',
            'divorciado': 'Divorciado(a)', 'divorciada': 'Divorciado(a)', 'viuvo': 'Viúvo(a)', 'viuva': 'Viúvo(a)',
            'uniao estavel': 'União Estável', 'uniao estável': 'União Estável'
        })

        # Filtra dados válidos
        df_filtrado = df_filtrado[
            (df_filtrado['genero_limpo'].isin(['Masculino', 'Feminino'])) & 
            (df_filtrado['estado_civil_limpo'].notna())
        ]

        if df_filtrado.empty:
            return criar_dados_grafico_barras_vazio()

        # Agrupa por estado civil e gênero
        genero_estado_civil = df_filtrado.groupby(['estado_civil_limpo', 'genero_limpo']).size().unstack(fill_value=0)
        
        labels = genero_estado_civil.index.tolist()
        dados_masculino = genero_estado_civil.get('Masculino', pd.Series([0]*len(labels))).tolist()
        dados_feminino = genero_estado_civil.get('Feminino', pd.Series([0]*len(labels))).tolist()

        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Masculino',
                    'data': dados_masculino,
                    'backgroundColor': '#3B82F6'
                },
                {
                    'label': 'Feminino',
                    'data': dados_feminino,
                    'backgroundColor': '#EC4899'
                }
            ]
        }

    except Exception as e:
        logger.error(f"Erro ao processar gênero por estado civil: {e}")
        return criar_dados_grafico_barras_vazio()

def processar_hierarquia(dados_cargos):
    """Processa hierarquia baseada nos cargos"""
    if not dados_cargos or not dados_cargos['labels']:
        return criar_dados_vazios("Hierarquia")

    hierarquia_mapping = {
        'Operacional': 'Operacional',
        'Técnico Correias': 'Técnico',
        'Técnico Borracha': 'Técnico', 
        'Técnico Qualidade': 'Técnico',
        'Técnico': 'Técnico',
        'Analista': 'Técnico',
        'Assistente': 'Administrativo',
        'Comercial': 'Comercial',
        'Gerência': 'Gerência',
        'Supervisão': 'Supervisão',
        'Estagiário': 'Estagiário',
        'Especializado': 'Especializado'
    }

    # Processa hierarquia
    hierarquia_data = {}
    for label, value in zip(dados_cargos['labels'], dados_cargos['values']):
        categoria = hierarquia_mapping.get(label, 'Outros')
        hierarquia_data[categoria] = hierarquia_data.get(categoria, 0) + value

    labels = list(hierarquia_data.keys())
    values = list(hierarquia_data.values())
    total = sum(values)
    percentages = [f"{round((v / total) * 100, 1)}%" for v in values] if total > 0 else []

    return {
        'labels': labels,
        'values': values,
        'percentages': percentages,
        'total': total
    }

@app.route('/graficos-beneficios')
@login_required
def graficos_beneficios():
    """Dados para os gráficos de benefícios"""
    try:
        if not carregar_excel() or data_cache['df'].empty:
            return jsonify({'error': 'Arquivo Excel não carregado'})

        df = data_cache['df']
        col_mappings = data_cache['col_mappings']

        logger.info("Processando gráficos de benefícios...")
        
        # Processa diferentes benefícios usando as colunas mapeadas
        dados_unimed = processar_coluna_sim_nao(col_mappings.get('unimed'), "Unimed")
        dados_transporte = processar_coluna_transporte(col_mappings.get('transporte'))
        dados_vale_transporte = processar_coluna_sim_nao(col_mappings.get('vale_transporte'), "Vale Transporte")
        dados_restaurante = processar_coluna_sim_nao(col_mappings.get('restaurante'), "Restaurante")
        dados_laboral = processar_coluna_sim_nao(col_mappings.get('laboral'), "Laboral")

        logger.info(f"Benefícios processados - Unimed: {dados_unimed['total']}, Transporte: {dados_transporte['total']}")

        return jsonify({
            'unimed': dados_unimed,
            'transporte': dados_transporte,
            'vale_transporte': dados_vale_transporte,
            'restaurante': dados_restaurante,
            'laboral': dados_laboral
        })

    except Exception as e:
        logger.error(f"Erro em graficos-beneficios: {e}")
        return jsonify({'error': str(e)})

def processar_coluna_sim_nao(coluna, titulo):
    """Processa colunas com respostas Sim/Não"""
    if not coluna or coluna not in data_cache['df'].columns:
        logger.warning(f"Coluna '{titulo}' não encontrada: '{coluna}'")
        return criar_dados_vazios(titulo)
    
    df = data_cache['df']
    logger.info(f"Processando coluna: '{coluna}' para {titulo}")
    
    dados_limpos = df[coluna].dropna().astype(str).apply(limpar_texto)
    
    # Log para ver os dados brutos
    logger.info(f"Valores únicos na coluna {titulo}: {dados_limpos.unique()}")
    
    # Mapeamento de respostas
    mapeamento = {
        'sim': 'Sim', 's': 'Sim', 'ssim': 'Sim', 'siim': 'Sim',
        'nao': 'Não', 'não': 'Não', 'n': 'Não',
        'as vezes': 'Às vezes', 'asvezes': 'Às vezes', 'quando': 'Às vezes',
        'raramente': 'Raramente', 'pouco': 'Raramente', 'poucas vezes': 'Raramente',
        'sempre': 'Sempre', 'sempre.': 'Sempre', 'todo dia': 'Sempre', 'todos os dias': 'Sempre',
        'nunca': 'Nunca', 'nunca.': 'Nunca', 'jamais': 'Nunca'
    }
    
    dados_mapeados = dados_limpos.map(lambda x: mapeamento.get(x, x.title()))
    
    # Log para ver os dados mapeados
    logger.info(f"Valores mapeados para {titulo}: {dados_mapeados.unique()}")
    
    contagem = dados_mapeados.value_counts()
    
    # Log da contagem
    logger.info(f"Contagem {titulo}: {contagem.to_dict()}")
    
    labels = [str(x) for x in contagem.index]
    values = [int(x) for x in contagem.values]
    total = sum(values)
    percentages = [f"{round((v / total) * 100, 1)}%" for v in values] if total > 0 else []
    
    return {
        'labels': labels,
        'values': values,
        'percentages': percentages,
        'total': total,
        'titulo': titulo
    }

def processar_coluna_transporte(coluna):
    """Processa coluna de meio de transporte"""
    if not coluna or coluna not in data_cache['df'].columns:
        logger.warning(f"Coluna de transporte não encontrada: '{coluna}'")
        return criar_dados_vazios("Transporte")
    
    df = data_cache['df']
    logger.info(f"Processando coluna de transporte: '{coluna}'")
    
    dados_limpos = df[coluna].dropna().astype(str).apply(limpar_texto)
    
    # Log para ver os dados brutos
    logger.info(f"Valores únicos na coluna transporte: {dados_limpos.unique()}")
    
    # Mapeamento de transportes
    mapeamento = {
        'carro': 'Carro', 'carro proprio': 'Carro', 'carro próprio': 'Carro',
        'onibus': 'Ônibus', 'ônibus': 'Ônibus', 'onibus urbano': 'Ônibus',
        'moto': 'Moto', 'motocicleta': 'Moto', 'moto propria': 'Moto',
        'caminhada': 'Caminhada', 'pe': 'Caminhada', 'a pe': 'Caminhada', 'a pé': 'Caminhada',
        'bicicleta': 'Bicicleta', 'bike': 'Bicicleta',
        'van': 'Van', 'van fretada': 'Van',
        'carona': 'Carona', 'carona com colega': 'Carona',
        'uber': 'Uber/Táxi', 'taxi': 'Uber/Táxi', 'táxi': 'Uber/Táxi',
        'transporte publico': 'Transporte Público', 'transporte público': 'Transporte Público',
        'transporte da empresa': 'Transporte da Empresa', 'transporte fretado': 'Transporte da Empresa',
        'onibus da empresa': 'Transporte da Empresa'
    }
    
    dados_mapeados = dados_limpos.map(lambda x: mapeamento.get(x, x.title()))
    
    # Log para ver os dados mapeados
    logger.info(f"Transportes mapeados: {dados_mapeados.unique()}")
    
    contagem = dados_mapeados.value_counts()
    
    # Log da contagem
    logger.info(f"Contagem transportes: {contagem.to_dict()}")
    
    # Agrupa categorias com poucos registros
    min_registros = max(2, len(dados_limpos) * 0.05)
    contagem_filtrada = contagem[contagem >= min_registros]
    outros = contagem[contagem < min_registros].sum()
    
    if outros > 0:
        contagem_filtrada['Outros'] = outros
    
    labels = [str(x) for x in contagem_filtrada.index]
    values = [int(x) for x in contagem_filtrada.values]
    total = sum(values)
    percentages = [f"{round((v / total) * 100, 1)}%" for v in values] if total > 0 else []
    
    return {
        'labels': labels,
        'values': values,
        'percentages': percentages,
        'total': total,
        'titulo': 'Meio de Transporte'
    }

def criar_dados_vazios(titulo="Dados não disponíveis"):
    """Retorna estrutura vazia para dados não encontrados"""
    logger.warning(f"Criando dados vazios para: {titulo}")
    return {
        'labels': [],
        'values': [],
        'percentages': [],
        'total': 0,
        'titulo': titulo
    }

def criar_dados_grafico_barras_vazio():
    """Retorna estrutura vazia para gráfico de barras"""
    return {
        'labels': [],
        'datasets': [
            {
                'label': 'Masculino',
                'data': [],
                'backgroundColor': '#3B82F6'
            },
            {
                'label': 'Feminino',
                'data': [],
                'backgroundColor': '#EC4899'
            }
        ]
    }

@app.route('/graficos-page')
@login_required
def graficos_page():
    """Rota para renderizar a página HTML dos gráficos"""
    # Primeiro verifica se o Excel foi carregado
    if not carregar_excel() or data_cache['df'].empty:
        flash('Erro ao carregar dados do Excel. Verifique o arquivo.', 'error')
    
    # Obtém informações básicas para mostrar na página
    df = data_cache['df']
    col_mappings = data_cache['col_mappings']
    
    # Informações para debug na página
    estado_civil_col = col_mappings.get('estado_civil', 'Não encontrada')
    cargo_col = col_mappings.get('cargo', 'Não encontrada')
    total_colaboradores = len(df) if not df.empty else 0
    
    # Log para debug
    logger.info(f"Renderizando graficos-page - Estado Civil: {estado_civil_col}, Cargo: {cargo_col}")
    
    return render_template(
        'graficos.html',
        estado_civil_col=estado_civil_col,
        cargo_col=cargo_col,
        total_colaboradores=total_colaboradores
    )

@app.route('/search')
@login_required
def search():
    """Rota de busca de colaboradores - VERSÃO OTIMIZADA"""
    try:
        if not carregar_excel() or data_cache['df'].empty:
            return jsonify({
                "columns": [], 
                "rows": [], 
                "error": "Banco de dados não carregado. Contate o administrador."
            })

        q = request.args.get('q', '').strip()
        df = data_cache['df']
        col_mappings = data_cache['col_mappings']

        if not q:
            return jsonify({"columns": [], "rows": []})

        q_norm = normalize_text(q)
        q_digits = re.sub(r"\D", "", q)
        results = []
        
        # Log para debug
        logger.info(f"Busca recebida: '{q}' (normalizada: '{q_norm}', dígitos: '{q_digits}')")
        logger.info(f"Coluna de nome mapeada: '{col_mappings.get('Digite o seu nome completo:')}'")
        
        # Verifica se a coluna de nome está disponível
        if not col_mappings.get('nome'):
            logger.error("COLUNA DE NOME NÃO MAPEADA - não é possível buscar por nome")
            return jsonify({
                "columns": [], 
                "rows": [], 
                "error": "Coluna de nome não encontrada no banco de dados"
            })

        # Busca otimizada usando operações vetorizadas do pandas
        mask = pd.Series([False] * len(df))
        
        # Busca por nome (substring) - usando operação vetorizada
        if q_norm:
            nome_mask = df['_norm_nome'].str.contains(q_norm, na=False)
            mask = mask | nome_mask
            logger.info(f"Encontrados {nome_mask.sum()} resultados por nome")
        
        # Busca por CPF (exato)
        if col_mappings['cpf'] and q_digits:
            cpf_mask = df['_norm_cpf'] == q_digits
            mask = mask | cpf_mask
            logger.info(f"Encontrados {cpf_mask.sum()} resultados por CPF")
        
        # Busca por ID (substring)
        if col_mappings['id'] and q:
            id_mask = df['_norm_id'].str.contains(q.lower(), na=False)
            mask = mask | id_mask
            logger.info(f"Encontrados {id_mask.sum()} resultados por ID")
        
        # Aplica a máscara combinada
        resultados_df = df[mask]
        
        # Se não encontrou resultados, tenta busca mais ampla por palavras individuais
        if len(resultados_df) == 0 and q_norm:
            logger.info("Tentando busca mais ampla por palavras individuais...")
            palavras = q_norm.split()
            for palavra in palavras:
                if len(palavra) > 2:
                    palavra_mask = df['_norm_nome'].str.contains(palavra, na=False)
                    resultados_df = pd.concat([resultados_df, df[palavra_mask]])
            
            # Remove duplicatas
            resultados_df = resultados_df.drop_duplicates()
        
        # Limita o número de resultados
        resultados_df = resultados_df.head(500)
        
        # Converte para formato de dicionário
        results = []
        for _, row in resultados_df.iterrows():
            record = {col: ("" if pd.isna(row[col]) else str(row[col])) for col in df.columns}
            results.append(record)

        logger.info(f"Busca finalizada: {len(results)} resultados encontrados")
        
        return jsonify({
            "columns": df.columns.tolist(), 
            "rows": results,
            "total": len(results)
        })

    except Exception as e:
        logger.error(f"ERRO na busca: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "columns": [], 
            "rows": [], 
            "error": "Erro interno na busca"
        }), 500

@app.route('/health')
def health_check():
    """Rota para verificar a saúde da aplicação"""
    excel_loaded = carregar_excel() and not data_cache['df'].empty
    return jsonify({
        'status': 'healthy',
        'excel_loaded': excel_loaded,
        'excel_rows': len(data_cache['df']) if excel_loaded else 0,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/debug/colunas')
@login_required
def debug_colunas():
    """Rota para debug - mostra informações sobre as colunas detectadas"""
    if not carregar_excel() or data_cache['df'].empty:
        return jsonify({'error': 'Excel não carregado'})
    
    df = data_cache['df']
    col_mappings = data_cache['col_mappings']
    
    info = {
        'colunas_disponiveis': df.columns.tolist(),
        'mapeamento': col_mappings,
        'total_linhas': len(df)
    }
    
    # Adiciona informações sobre dados de exemplo para colunas importantes
    for coluna in ['nome', 'estado_civil', 'cargo']:
        if col_mappings.get(coluna) and col_mappings[coluna] in df.columns:
            dados_coluna = df[col_mappings[coluna]].dropna().head(10).tolist()
            info[f'dados_{coluna}'] = dados_coluna
    
    return jsonify(info)

if __name__ == '__main__':
    # Carrega o Excel na inicialização
    carregar_excel()
    app.run(host='0.0.0.0', port=5000, debug=True)