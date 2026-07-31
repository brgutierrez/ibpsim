import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def get_df_shipcalls():
    df = pd.read_csv(os.getenv('VESSELS_DATA'), index_col=0)
    df = df.reindex(
        columns=['PROVISIONAL', 'BUQUE', 'IMO', 'FECHA_ETA', 'HORA_ETA', 'TXTESLORA', 'TXTMANGA', 'TXTVELMAX',
                 'TXTCALADO',
                 'FECHA_ETD', 'HORA_ETD', 'TXTNUMIMO'])
    df['FECHA_ETA'] = pd.to_datetime(df['FECHA_ETA'], format='%m/%d/%Y %H:%M:%S')
    df['HORA_ETA'] = pd.to_datetime(df['HORA_ETA'], format='%m/%d/%Y %H:%M:%S')
    df['FECHA_ETD'] = pd.to_datetime(df['FECHA_ETD'], format='%m/%d/%Y %H:%M:%S')
    df['HORA_ETD'] = pd.to_datetime(df['HORA_ETD'], format='%m/%d/%Y %H:%M:%S')
    df_shipcalls = df.drop(columns=['TXTNUMIMO'])
    return df_shipcalls
