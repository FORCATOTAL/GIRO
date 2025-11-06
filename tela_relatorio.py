import streamlit as st
import pandas as pd
from pathlib import Path
import subprocess
import io

ARQ_REL_XLSX = Path('RELATORIO_GIRO_MENSAL.xlsx')
ARQ_REL_CSV = Path('RELATORIO_GIRO_MENSAL.csv')

st.set_page_config(page_title='Relatório de Giro Mensal', layout='wide')
st.title('Relatório de Giro por Item')

st.sidebar.header('Opções')

def garantir_relatorio():
    if not ARQ_REL_XLSX.exists():
        origem = Path('GIRO.xlsx')
        df = None
        if origem.exists():
            try:
                df = pd.read_excel(origem, sheet_name=0)
            except Exception as e:
                st.error(f'Erro ao ler GIRO.xlsx: {e}')
        else:
            uploaded = st.sidebar.file_uploader('Enviar GIRO.xlsx', type=['xlsx'])
            if uploaded is not None:
                try:
                    df = pd.read_excel(uploaded, sheet_name=0)
                except Exception as e:
                    st.error(f'Erro ao ler arquivo enviado: {e}')
        if df is not None:
            try:
                import relatorio_giro_mensal as rgm
                resumo, monthly = rgm.calcular_media_mensal(df)
                rgm.salvar_relatorio(resumo, monthly, ARQ_REL_XLSX)
                try:
                    resumo.to_csv(ARQ_REL_CSV, index=False)
                except Exception:
                    pass
                st.toast('Relatório gerado automaticamente a partir do GIRO.xlsx', icon='✅')
            except Exception as e:
                st.error(f'Falha ao gerar relatório: {e}')
        else:
            st.warning('RELATORIO_GIRO_MENSAL.xlsx não encontrado. Carregue o GIRO.xlsx na barra lateral para gerar o relatório.')

def carregar_dados():
    garantir_relatorio()
    if not ARQ_REL_XLSX.exists():
        st.stop()
    resumo = pd.read_excel(ARQ_REL_XLSX, sheet_name='Resumo_Media_Mensal')
    mensal = pd.read_excel(ARQ_REL_XLSX, sheet_name='Mensal_Detalhado')
    # Identificar colunas de mês (formato YYYY-MM)
    month_cols = [c for c in mensal.columns if isinstance(c, str) and pd.Series([c]).str.match(r'^\d{4}-\d{2}$').iloc[0]]
    # Ordenar colunas de mês
    meses_ord = sorted(month_cols)
    # Garantir média diária baseada em dias de calendário do período (todos os dias)
    def preencher_dias_calendario_e_media(res):
        # Se o arquivo ainda não tiver DIAS_CALENDARIO, derivar via MES_INICIAL/MES_FINAL
        if 'DIAS_CALENDARIO' not in res.columns and {'MES_INICIAL','MES_FINAL'}.issubset(set(res.columns)):
            try:
                res['MES_INICIAL'] = pd.to_datetime(res['MES_INICIAL'], errors='coerce')
                res['MES_FINAL'] = pd.to_datetime(res['MES_FINAL'], errors='coerce')
                def dias_intervalo(row):
                    mi, mf = row['MES_INICIAL'], row['MES_FINAL']
                    if pd.isna(mi) or pd.isna(mf):
                        return 0
                    inicio = pd.Timestamp(year=mi.year, month=mi.month, day=1)
                    fim = (pd.Timestamp(year=mf.year, month=mf.month, day=1) + pd.offsets.MonthEnd(1))
                    return (fim - inicio).days + 1
                res['DIAS_CALENDARIO'] = res.apply(dias_intervalo, axis=1)
            except Exception:
                pass
        # Recalcular média diária com base em dias de calendário quando disponível
        if 'DIAS_CALENDARIO' in res.columns:
            res['DIAS_CALENDARIO'] = pd.to_numeric(res['DIAS_CALENDARIO'], errors='coerce').fillna(0)
            res['MEDIA_MENSAL_GIRO'] = res.apply(
                lambda r: (r['QTDE_TOTAL'] / r['DIAS_CALENDARIO']) if r['DIAS_CALENDARIO'] > 0 else 0,
                axis=1
            )
        return res

    resumo = preencher_dias_calendario_e_media(resumo)

    # Garantir presença de DIAS_COM_MOVIMENTO para exibição na UI
    def preencher_dias_com_movimento(res):
        if 'DIAS_COM_MOVIMENTO' not in res.columns:
            try:
                base = pd.read_excel('GIRO.xlsx', sheet_name=0)
                base['DATA_FATURAMENTO'] = pd.to_datetime(base['DATA_FATURAMENTO'], errors='coerce')
                base['QUANTIDADE_FATURADA'] = pd.to_numeric(base['QUANTIDADE_FATURADA'], errors='coerce').fillna(0)
                base = base.dropna(subset=['DATA_FATURAMENTO'])
                base['DIA'] = base['DATA_FATURAMENTO'].dt.date
                dias = (
                    base[base['QUANTIDADE_FATURADA'] > 0]
                    .groupby(['CODPROD','DESCRICAO','UNIDADE'])['DIA']
                    .nunique()
                    .rename('DIAS_COM_MOVIMENTO')
                    .reset_index()
                )
                res = res.merge(dias, on=['CODPROD','DESCRICAO','UNIDADE'], how='left')
            except Exception:
                pass
        return res

    resumo = preencher_dias_com_movimento(resumo)
    return resumo, mensal, meses_ord

resumo, mensal, meses_ord = carregar_dados()

# Filtros
descricao_query = st.sidebar.text_input('Buscar descrição (contém)')
unidades = ['Todas'] + sorted(resumo['UNIDADE'].dropna().unique().tolist())
sel_unid = st.sidebar.selectbox('Filtrar por unidade', unidades)
ordenacao = st.sidebar.selectbox('Ordenar por', ['MEDIA_MENSAL_GIRO', 'QTDE_TOTAL'])
mostrar_todos = st.sidebar.checkbox('Mostrar todos os itens', value=True)
if not mostrar_todos:
    top_n = st.sidebar.slider('Top N itens', min_value=5, max_value=200, value=50, step=5)

df = resumo.copy()
if descricao_query:
    df = df[df['DESCRICAO'].str.contains(descricao_query, case=False, na=False)]
if sel_unid != 'Todas':
    df = df[df['UNIDADE'] == sel_unid]

# Ordenação e top N
df = df.sort_values(ordenacao, ascending=False)
if not mostrar_todos:
    df = df.head(top_n)

# Métricas rápidas
col1, col2, col3, col4 = st.columns(4)
col1.metric('Itens no Top N', len(df))
media_global = df['MEDIA_MENSAL_GIRO'].mean() if len(df) else 0
col2.metric('Média diária (Top N)', f"{media_global:,.2f}")
min_mes = pd.to_datetime(resumo['MES_INICIAL']).min()
max_mes = pd.to_datetime(resumo['MES_FINAL']).max()
col3.metric('Mês inicial', min_mes.strftime('%Y-%m') if pd.notnull(min_mes) else '-')
col4.metric('Mês final', max_mes.strftime('%Y-%m') if pd.notnull(max_mes) else '-')

st.subheader('Resumo')
cols_base = ['CODPROD','DESCRICAO','UNIDADE','MEDIA_MENSAL_GIRO','MESES_COM_MOVIMENTO','QTDE_TOTAL','MES_INICIAL','MES_FINAL']
cols = cols_base.copy()
if 'DIAS_COM_MOVIMENTO' in df.columns:
    cols.insert(4, 'DIAS_COM_MOVIMENTO')  # antes de MESES_COM_MOVIMENTO
df_mostrar = df[cols].rename(columns={
    'MEDIA_MENSAL_GIRO':'Média Diária',
    'DIAS_COM_MOVIMENTO':'Dias com Movimento',
    'MESES_COM_MOVIMENTO':'Meses com Movimento',
    'QTDE_TOTAL':'Qtde Total',
    'MES_INICIAL':'Mês Inicial',
    'MES_FINAL':'Mês Final'
})
st.dataframe(df_mostrar, width='stretch', hide_index=True)

# Seleção de item para detalhamento
st.subheader('Detalhe diário por item')
opcoes_item = df.apply(lambda r: f"{r['CODPROD']} - {r['DESCRICAO']} ({r['UNIDADE']})", axis=1).tolist()
sel_item = st.selectbox('Selecione o item', opcoes_item)

def parse_sel_item(s):
    # Formato: CODPROD - DESCRICAO (UNIDADE)
    try:
        cod = s.split(' - ')[0].strip()
        unid = s.split('(')[-1].rstrip(')')
        return cod, unid
    except Exception:
        return None, None

cod_sel, unid_sel = parse_sel_item(sel_item)
if cod_sel is not None:
    try:
        # Carregar dados originais para detalhar por dia
        base = pd.read_excel('GIRO.xlsx', sheet_name=0)
        base['DATA_FATURAMENTO'] = pd.to_datetime(base['DATA_FATURAMENTO'], errors='coerce')
        base['QUANTIDADE_FATURADA'] = pd.to_numeric(base['QUANTIDADE_FATURADA'], errors='coerce').fillna(0)

        # Filtrar item selecionado
        filtro = (
            base['CODPROD'].astype(str) == str(cod_sel)
        ) & (
            base['UNIDADE'] == unid_sel
        )
        det = base.loc[filtro, ['DATA_FATURAMENTO', 'QUANTIDADE_FATURADA']].dropna(subset=['DATA_FATURAMENTO'])

        if not det.empty:
            # Agregar por dia
            det['DIA'] = det['DATA_FATURAMENTO'].dt.date
            diario = det.groupby('DIA', as_index=False)['QUANTIDADE_FATURADA'].sum()
            ts = pd.DataFrame({'Data': pd.to_datetime(diario['DIA']), 'Quantidade': diario['QUANTIDADE_FATURADA']}).sort_values('Data')
            st.line_chart(ts.set_index('Data'))
            st.dataframe(ts, width='stretch', hide_index=True)
        else:
            st.info('Sem dados diários para o item selecionado.')
    except Exception as e:
        st.error(f'Erro ao carregar detalhamento diário: {e}')

st.divider()
st.caption('Arquivos base: RELATORIO_GIRO_MENSAL.xlsx e RELATORIO_GIRO_MENSAL.csv. Use a barra lateral para gerar/atualizar o relatório a partir do GIRO.xlsx quando necessário.')