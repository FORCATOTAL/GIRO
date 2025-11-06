import pandas as pd
from openpyxl import load_workbook

def main():
    xlsx_path = 'GIRO.xlsx'
    try:
        wb = load_workbook(filename=xlsx_path, read_only=True, data_only=True)
        sheet_names = wb.sheetnames
        print(f"Planilhas encontradas: {sheet_names}")
    except Exception as e:
        print(f"Erro ao abrir workbook: {e}")
        return

    # Ler a primeira planilha com pandas
    try:
        df = pd.read_excel(xlsx_path, sheet_name=0)
    except Exception as e:
        print(f"Erro ao ler a planilha com pandas: {e}")
        return

    # Mostrar informações básicas
    print("\nDimensões da planilha:", df.shape)
    print("\nColunas:")
    for i, c in enumerate(df.columns):
        print(f"  {i}: {c}")

    print("\nAmostra de 5 linhas:")
    with pd.option_context('display.max_columns', None):
        print(df.head(5))

    # Detectar possíveis colunas de item e mês/data
    cols_norm = {c: str(c).strip().lower() for c in df.columns}
    item_candidates = [c for c,n in cols_norm.items() if any(k in n for k in ['item','produto','código','codigo','sku','material','descrição','descricao'])]
    date_candidates = [c for c,n in cols_norm.items() if any(k in n for k in ['data','mês','mes','competência','competencia','emissão','emissao'])]
    value_candidates = [c for c,n in cols_norm.items() if any(k in n for k in ['giro','quantidade','qtd','saida','consumo','movimento'])]

    print("\nPossíveis colunas de item:", item_candidates)
    print("Possíveis colunas de data/mês:", date_candidates)
    print("Possíveis colunas de valor (giro/quantidade):", value_candidates)

if __name__ == '__main__':
    main()