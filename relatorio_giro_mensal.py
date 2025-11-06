import pandas as pd
from pathlib import Path

def calcular_media_mensal(df: pd.DataFrame) -> pd.DataFrame:
    # Normalizar nomes
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Campos necessários
    cod_col = 'CODPROD'
    desc_col = 'DESCRICAO'
    data_col = 'DATA_FATURAMENTO'
    qtd_col = 'QUANTIDADE_FATURADA'
    unidade_col = 'UNIDADE'

    # Garantir tipos
    df[data_col] = pd.to_datetime(df[data_col], errors='coerce')
    df[qtd_col] = pd.to_numeric(df[qtd_col], errors='coerce').fillna(0)

    # Remover linhas sem data
    df = df.dropna(subset=[data_col])

    # Derivar mês (competência)
    df['MES'] = df[data_col].dt.to_period('M').dt.to_timestamp()

    # Agregar por item e mês
    monthly = (
        df.groupby([cod_col, desc_col, unidade_col, 'MES'], as_index=False)[qtd_col]
          .sum()
    )

    # Calcular métricas por item
    # total por item (somando diretamente do dado diário)
    keys = [cod_col, desc_col, unidade_col]
    total_por_item = df.groupby(keys)[qtd_col].sum().rename('QTDE_TOTAL')

    # meses com movimento (contagem de meses com quantidade > 0)
    meses_mov = monthly[monthly[qtd_col] > 0].groupby([cod_col, desc_col, unidade_col])['MES'].nunique().rename('MESES_COM_MOVIMENTO')

    # mês inicial e final (no dado do item)
    min_mes = monthly.groupby([cod_col, desc_col, unidade_col])['MES'].min().rename('MES_INICIAL')
    max_mes = monthly.groupby([cod_col, desc_col, unidade_col])['MES'].max().rename('MES_FINAL')

    # número de meses no intervalo do item (inclui meses sem movimento)
    # diff em meses: (ano2-ano1)*12 + (mes2-mes1) + 1
    comp = pd.concat([min_mes, max_mes], axis=1)
    def meses_intervalo(row):
        mi, mf = row['MES_INICIAL'], row['MES_FINAL']
        return (mf.year - mi.year) * 12 + (mf.month - mi.month) + 1
    comp['MESES_INTERVALO'] = comp.apply(meses_intervalo, axis=1)

    # cálculo adicional para média diária: usar datas reais do intervalo
    min_data = df.groupby(keys)[data_col].min().rename('DATA_INICIAL')
    max_data = df.groupby(keys)[data_col].max().rename('DATA_FINAL')
    comp_dias = pd.concat([min_data, max_data], axis=1)
    def dias_intervalo(row):
        return (row['DATA_FINAL'] - row['DATA_INICIAL']).days + 1 if pd.notnull(row['DATA_FINAL']) and pd.notnull(row['DATA_INICIAL']) else pd.NA
    comp_dias['DIAS_INTERVALO'] = comp_dias.apply(dias_intervalo, axis=1)

    # média diária considerando todos os dias do intervalo do item
    media_diaria = (total_por_item / comp_dias['DIAS_INTERVALO']).rename('MEDIA_MENSAL_GIRO')

    # Montar resumo
    resumo = pd.concat([total_por_item, meses_mov, comp, comp_dias['DIAS_INTERVALO']], axis=1).reset_index()
    # Mantemos o nome da coluna 'MEDIA_MENSAL_GIRO' por compatibilidade com a UI,
    # mas o valor agora representa a média diária do intervalo.
    resumo['MEDIA_MENSAL_GIRO'] = media_diaria.values

    # Ordenar por maior média
    resumo = resumo.sort_values('MEDIA_MENSAL_GIRO', ascending=False)

    return resumo, monthly

def salvar_relatorio(resumo: pd.DataFrame, monthly: pd.DataFrame, caminho_saida: Path):
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
        resumo.to_excel(writer, sheet_name='Resumo_Media_Mensal', index=False)
        # Tabela dinâmica com meses em colunas
        pivot = monthly.pivot_table(index=['CODPROD','DESCRICAO','UNIDADE'], columns='MES', values='QUANTIDADE_FATURADA', aggfunc='sum', fill_value=0)
        # Flatten das colunas MultiIndex
        pivot.columns = [c.strftime('%Y-%m') if hasattr(c, 'strftime') else str(c) for c in pivot.columns]
        pivot = pivot.reset_index()
        pivot.to_excel(writer, sheet_name='Mensal_Detalhado', index=False)

def main():
    origem = Path('GIRO.xlsx')
    destino = Path('RELATORIO_GIRO_MENSAL.xlsx')

    df = pd.read_excel(origem, sheet_name=0)
    resumo, monthly = calcular_media_mensal(df)
    salvar_relatorio(resumo, monthly, destino)

    # Também gerar CSV simples do resumo
    csv_dest = Path('RELATORIO_GIRO_MENSAL.csv')
    resumo.to_csv(csv_dest, index=False)

    # Mostrar top 10 no console
    top10 = resumo[['CODPROD','DESCRICAO','UNIDADE','MEDIA_MENSAL_GIRO','MESES_COM_MOVIMENTO','QTDE_TOTAL','MES_INICIAL','MES_FINAL']].head(10)
    with pd.option_context('display.max_columns', None):
        print("Top 10 itens por média mensal de giro:")
        print(top10.to_string(index=False))
    print(f"\nRelatório salvo em: {destino.resolve()} e {csv_dest.resolve()}")

if __name__ == '__main__':
    main()