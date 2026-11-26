import streamlit as st
from database.migrations import inicializar_banco
from services.auth_service import verificar_login

st.set_page_config(
    page_title="Kiosk Brands - Sistema PCP",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='15' fill='%23C8102E'/><text x='50' y='65' font-size='50' text-anchor='middle' fill='white' font-family='Arial' font-weight='bold'>KB</text></svg>",
    layout="wide"
)

# ─── CSS Global Moderno ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Font global */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar limpa */
    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 3px solid #C8102E;
    }
    [data-testid="stSidebar"] * {
        color: #1a1a2e !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background-color: #C8102E;
        border: none;
        color: white !important;
        border-radius: 10px;
        font-weight: 600;
        padding: 8px 16px;
        transition: all 0.2s;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #a00d24;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(200,16,46,0.3);
    }

    /* Botões primários */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #C8102E, #e01535) !important;
        color: white !important;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        padding: 10px 24px;
        transition: all 0.2s;
        box-shadow: 0 2px 8px rgba(200,16,46,0.2);
    }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #a00d24, #C8102E) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(200,16,46,0.3);
    }

    /* Botões secundários */
    .stButton > button:not([kind="primary"]) {
        border-radius: 10px;
        transition: all 0.2s;
    }

    /* Download buttons */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #C8102E, #e01535) !important;
        color: white !important;
        border: none;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(200,16,46,0.2);
    }

    /* Tabs modernas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: rgba(255,255,255,0.03);
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab-list"] button {
        border-radius: 10px;
        padding: 8px 20px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background: linear-gradient(135deg, #C8102E, #e01535);
        color: white;
        box-shadow: 0 2px 8px rgba(200,16,46,0.3);
    }

    /* Metrics modernos */
    [data-testid="stMetricValue"] {
        font-weight: 700;
        font-size: 2rem !important;
    }

    /* Headers */
    h1 {
        color: #FAFAFA !important;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    h2, h3 {
        color: #FAFAFA !important;
        font-weight: 600;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    /* Expanders modernos */
    [data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 8px;
    }
    [data-testid="stExpander"] summary {
        font-weight: 600;
    }

    /* Cards KPI */
    .kpi-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 20px 24px;
        text-align: center;
        transition: all 0.3s;
    }
    .kpi-card:hover {
        border-color: rgba(200,16,46,0.3);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    }
    .kpi-card .kpi-icon {
        font-size: 28px;
        margin-bottom: 8px;
    }
    .kpi-card .kpi-value {
        font-size: 32px;
        font-weight: 700;
        color: #FAFAFA;
        line-height: 1.2;
    }
    .kpi-card .kpi-label {
        font-size: 13px;
        color: rgba(250,250,250,0.6);
        font-weight: 500;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Pipeline de etapas */
    .pipeline {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0;
        margin: 20px 0;
        flex-wrap: wrap;
    }
    .pipeline-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 12px 20px;
        border-radius: 12px;
        min-width: 140px;
        text-align: center;
        transition: all 0.2s;
    }
    .pipeline-step .step-icon { font-size: 24px; margin-bottom: 4px; }
    .pipeline-step .step-count { font-size: 24px; font-weight: 700; }
    .pipeline-step .step-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; }
    .pipeline-arrow {
        font-size: 20px;
        color: rgba(250,250,250,0.3);
        margin: 0 4px;
    }

    .step-aguardando { background: rgba(255,193,7,0.12); border: 1px solid rgba(255,193,7,0.3); color: #ffc107; }
    .step-producao { background: rgba(0,123,255,0.12); border: 1px solid rgba(0,123,255,0.3); color: #4da3ff; }
    .step-finalizada { background: rgba(40,167,69,0.12); border: 1px solid rgba(40,167,69,0.3); color: #5cd87e; }
    .step-transferido { background: rgba(108,117,125,0.12); border: 1px solid rgba(108,117,125,0.3); color: #adb5bd; }

    /* Login */
    .login-card {
        max-width: 420px;
        margin: 60px auto;
        padding: 48px;
        background: rgba(255,255,255,0.04);
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }

    /* Welcome */
    .welcome-banner {
        background: linear-gradient(135deg, #C8102E 0%, #8B0000 50%, #1a1a2e 100%);
        padding: 48px;
        border-radius: 20px;
        color: white;
        margin-bottom: 32px;
        box-shadow: 0 8px 32px rgba(200,16,46,0.2);
    }
    .welcome-banner h1 { font-size: 32px; margin-bottom: 8px; }
    .welcome-banner p { font-size: 16px; opacity: 0.85; }

    /* Nav cards */
    .nav-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
    }
    .nav-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 28px;
        transition: all 0.3s;
        cursor: pointer;
    }
    .nav-card:hover {
        border-color: #C8102E;
        background: rgba(200,16,46,0.06);
        transform: translateY(-3px);
        box-shadow: 0 12px 32px rgba(0,0,0,0.2);
    }
    .nav-card .nav-icon { font-size: 32px; margin-bottom: 12px; }
    .nav-card .nav-title {
        font-size: 16px;
        font-weight: 600;
        color: #FAFAFA;
        margin-bottom: 6px;
    }
    .nav-card .nav-desc {
        font-size: 13px;
        color: rgba(250,250,250,0.5);
        line-height: 1.4;
    }

    /* Badges de status */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .badge-aguardando { background: rgba(255,193,7,0.15); color: #ffc107; }
    .badge-producao { background: rgba(0,123,255,0.15); color: #4da3ff; }
    .badge-finalizada { background: rgba(40,167,69,0.15); color: #5cd87e; }
    .badge-transferido { background: rgba(108,117,125,0.15); color: #adb5bd; }

    /* Nav card com botão integrado */
    .nav-card-wrapper {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 24px 24px 16px 24px;
        transition: all 0.3s;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .nav-card-wrapper:hover {
        border-color: rgba(200,16,46,0.4);
        background: rgba(200,16,46,0.04);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    }
    .nav-card-wrapper .nav-icon { font-size: 32px; margin-bottom: 10px; }
    .nav-card-wrapper .nav-desc {
        font-size: 13px;
        color: rgba(250,250,250,0.5);
        line-height: 1.5;
        margin-bottom: 16px;
    }
    /* Botão dentro do card */
    .nav-card-wrapper + div .stButton > button {
        background: linear-gradient(135deg, #C8102E, #e01535) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 20px !important;
        transition: all 0.2s !important;
        box-shadow: 0 2px 8px rgba(200,16,46,0.2) !important;
        margin-top: -12px;
    }
    .nav-card-wrapper + div .stButton > button:hover {
        background: linear-gradient(135deg, #a00d24, #C8102E) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(200,16,46,0.35) !important;
    }

    /* Divider sutil */
    hr {
        border-color: rgba(255,255,255,0.06) !important;
    }

    /* Selectbox & inputs */
    [data-testid="stSelectbox"] label,
    [data-testid="stTextInput"] label,
    [data-testid="stNumberInput"] label,
    [data-testid="stDateInput"] label,
    [data-testid="stMultiSelect"] label {
        font-weight: 500;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        color: rgba(250,250,250,0.6) !important;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar banco de dados
try:
    inicializar_banco()
except Exception as e:
    st.error(f"Erro ao inicializar banco de dados: {e}")


# ─── Sessão persistente ──────────────────────────────────────────────
from utils.session import salvar_sessao, recuperar_sessao, remover_sessao, restaurar_login
restaurar_login()


# Logo
LOGO_PATH = "logo.png"
try:
    st.logo(LOGO_PATH, size="large")
except Exception:
    pass


def login():
    st.markdown("<br><br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try:
            st.image(LOGO_PATH, width=180)
        except Exception:
            pass
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown("#### Acesso ao Sistema")
            email = st.text_input("E-mail", placeholder="seu@email.com")
            senha = st.text_input("Senha", type="password", placeholder="********")
            submit = st.form_submit_button("Entrar", use_container_width=True)

            if submit:
                try:
                    usuario = verificar_login(email, senha)
                    if usuario:
                        user_data = {
                            "id": usuario.id,
                            "nome": usuario.nome,
                            "email": usuario.email,
                            "perfil": usuario.perfil
                        }
                        st.session_state["usuario"] = user_data
                        token = salvar_sessao(user_data)
                        st.session_state["session_token"] = token
                        st.query_params["session"] = token
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("E-mail ou senha incorretos.")
                except Exception as e:
                    st.error(f"Erro durante login: {e}")


def main():
    if "usuario" not in st.session_state:
        login()
        return

    usuario = st.session_state["usuario"]

    with st.sidebar:
        st.markdown(f"**{usuario['nome']}**")
        st.caption(f"{usuario['perfil']}")
        st.divider()
        if st.button("Sair", use_container_width=True):
            token = st.session_state.get("session_token")
            if token:
                remover_sessao(token)
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()

    # Welcome banner
    st.markdown(f"""
    <div class="welcome-banner">
        <h1>Bem-vindo, {usuario['nome']}!</h1>
        <p>Sistema de Planejamento e Controle de Producao — Kiosk Brands</p>
    </div>
    """, unsafe_allow_html=True)

    # Nav cards como botões clicáveis
    nav_items = [
        ("📝", "Criar Programacao", "Inserir SKUs e quantidades para gerar nova programacao de producao.", "pages/2_Criar_Programacao.py"),
        ("👀", "Revisar Programacao", "Revisar itens, reordenar prioridades e finalizar a programacao.", "pages/3_Revisar_Programacao.py"),
        ("🏭", "Producao Ativa", "Acompanhar lotes em producao, iniciar, finalizar e transferir.", "pages/4_Producao_Ativa.py"),
        ("📦", "Estoque de Essencias", "Controlar estoque de materias-primas e registrar movimentacoes.", "pages/5_Estoque.py"),
        ("🗂️", "Cadastro de Produtos", "Gerenciar base de produtos, SKUs e dados de producao.", "pages/6_Cadastro.py"),
        ("⚙️", "Configuracoes", "Gerenciar usuarios, perfis de acesso e parametros do sistema.", "pages/7_Configuracoes.py"),
        ("📊", "Indicadores", "Analise de tempos, produtividade e desempenho da fabrica.", "pages/8_Indicadores.py"),
    ]

    # Linha 1 - 4 cards
    cols1 = st.columns(4)
    for i, (icon, title, desc, page) in enumerate(nav_items[:4]):
        with cols1[i]:
            st.markdown(f"""
            <div class="nav-card-wrapper">
                <div>
                    <div class="nav-icon">{icon}</div>
                    <div class="nav-desc">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"{icon}  {title}", key=f"nav_{i}", use_container_width=True):
                st.switch_page(page)

    # Linha 2 - 3 cards
    cols2 = st.columns(4)
    for i, (icon, title, desc, page) in enumerate(nav_items[4:]):
        with cols2[i]:
            st.markdown(f"""
            <div class="nav-card-wrapper">
                <div>
                    <div class="nav-icon">{icon}</div>
                    <div class="nav-desc">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"{icon}  {title}", key=f"nav_{i+4}", use_container_width=True):
                st.switch_page(page)


if __name__ == "__main__":
    main()
