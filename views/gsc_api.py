import streamlit as st
import os
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from io import BytesIO
import time
from googleapiclient import discovery
from pyexcelerate import Workbook
from google_auth_oauthlib.flow import Flow
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
import urllib.parse
import functions as fc
from streamlit_raw_echarts import st_echarts, JsCode
import streamlit_antd_components as sac

# Define o período inicial e final padrão para o slider
date = date.today()
data_final = date - relativedelta(days=2)
data_inicial = date - relativedelta(months=16)
data_padrao = date - relativedelta(months=1)

# Convert secrets from the TOML file to strings
clientSecret = st.secrets["clientSecret"]
clientId = st.secrets["clientId"]
redirectUri = 'https://search-console-api.streamlit.app'

    
href = "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={}&redirect_uri={}&scope=https://www.googleapis.com/auth/webmasters.readonly&access_type=offline&prompt=consent".format(clientId, redirectUri)

credentials = {
    "installed": {
        "client_id": clientId,
        "client_secret": clientSecret,
        "redirect_uris": [],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://accounts.google.com/o/oauth2/token",
    }
}

flow = Flow.from_client_config(
    credentials,
    scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    redirect_uri=redirectUri,
)

auth_url, _ = flow.authorization_url(prompt="consent")
    
def button_callback():
    try:
        st.session_state.my_token_received = True
        code = st.experimental_get_query_params()["code"][0]
        st.session_state.my_token_input = code
    except KeyError or ValueError:
        st.error("⚠️ The parameter 'code' was not found in the URL. Please log in.")

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    modify = st.checkbox("Add Filters")

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filer Dataframe for:", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))

            # Check if the column is numeric and CTR
            is_ctr_column = column == 'CTR' and is_numeric_dtype(df[column])

            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for: {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                
                # If the column is CTR, format the slider values as percentage
                if is_ctr_column:
                    user_num_input = right.slider(
                        f"Values for: {column}",
                        min_value=_min * 100,  # Format as percentage
                        max_value=_max * 100,  # Format as percentage
                        value=(_min * 100, _max * 100),  # Format as percentage
                        step=step * 100,  # Format as percentage
                    )
                    user_num_input = (user_num_input[0] / 100, user_num_input[1] / 100)  # Convert back to float
                else:
                    user_num_input = right.slider(
                        f"Values for: {column}",
                        min_value=_min,
                        max_value=_max,
                        value=(_min, _max),
                        step=step,
                        format="%.2f",  # Formato para exibição
                    )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for: {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"String or Regex for: {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return df

def to_excel(df):
    """
    Converter DataFrame para formato Excel usando PyExcelerate.

    Parâmetros:
        df (pd.DataFrame): O DataFrame a ser convertido.

    Retorna:
        bytes: Os dados do Excel em formato de bytes.
    """
    output = BytesIO()
    wb = Workbook()
    ws = wb.new_sheet("Dados-API-GSC")
    
    # Obter os nomes das colunas do DataFrame
    columns = df.columns.tolist()

    # Converter o DataFrame para uma lista de listas para o PyExcelerate
    data = [columns] + df.values.tolist()

    # Escrever os dados na planilha
    for row_index, row_data in enumerate(data, start=1):
        for col_index, cell_value in enumerate(row_data, start=1):
            ws[row_index][col_index].value = cell_value

    # Salvar o arquivo
    wb.save(output)
    processed_data = output.getvalue()
    return processed_data

def check_input_url(input_url):
    # Verificar se a entrada contém "https://" ou "http://"
    if "https://" in input_url or "http://" in input_url:
        return input_url
    # Caso contrário, assume que é um domínio e adiciona "sc-domain:"
    return f'sc-domain:{input_url}'

@st.cache_resource(show_spinner=False)
def get_webproperty(token):
    flow.fetch_token(code=token)
    credentials = flow.credentials
    service = discovery.build(
        serviceName="webmasters",
        version="v3",
        credentials=credentials,
        cache_discovery=False,
    )

    return service

@st.cache_data(show_spinner=False)
# Definir a função para consultar e processar dados
def get_data(property_url, dimensions, startDate, endDate, url_filter=None, url_operator=None,
            palavra_filter=None, palavra_operator=None):
    service = get_webproperty(st.session_state.my_token_input)

    # Criar uma lista vazia para armazenar as linhas recuperadas da resposta
    data = []
    
    # Definir o limite de linhas desejado para 300.000 linhas
    row_limit = 300000
    
    # Definir o texto de progresso a ser exibido acima da barra de progresso
    progress_text = "Retrieving Metrics. Please Wait. 🐈"

    # Criar o widget de barra de progresso usando o Streamlit
    my_bar = st.progress(0, text=progress_text)

    # Inicializar a variável 'startRow' para rastrear a linha de início de cada solicitação
    startRow = 0

    while startRow == 0 or startRow % 25000 == 0 and startRow < row_limit:
        # Construir o corpo da solicitação com as variáveis especificadas
        request = {
            'startDate': startDate,
            'endDate': endDate,
            'dimensions': dimensions,
            'rowLimit': 25000,
            'startRow': startRow
        }

        if url_filter and url_operator:
            url_dimension_filter = {
                'dimension': 'PAGE',
                'operator': url_filter,
                'expression': url_operator
            }
            request['dimensionFilterGroups'] = [{'filters': [url_dimension_filter]}]

        if palavra_filter and palavra_operator:
            palavra_dimension_filter = {
                'dimension': 'QUERY',
                'operator': palavra_filter,
                'expression': palavra_operator
            }
            if 'dimensionFilterGroups' in request:
                request['dimensionFilterGroups'].append({'filters': [palavra_dimension_filter]})
            else:
                request['dimensionFilterGroups'] = [{'filters': [palavra_dimension_filter]}]

        # Armazenar a resposta da API do Google Search Console
        response = service.searchanalytics().query(siteUrl=property_url, body=request).execute()

        # Obter e atualizar as linhas
        rows = response.get('rows', [])
        startRow = startRow + len(rows)

        # Estender a lista de dados com as linhas
        data.extend(rows)
        
        # Calcular a porcentagem de progresso
        progress_percent = min((startRow / row_limit) * 100, 100)

        # Converter a porcentagem de progresso para um valor entre 0.0 e 1.0
        progress_value = progress_percent / 100.0

        # Atualizar a barra de progresso com o progresso atual
        my_bar.progress(progress_value, text=progress_text)
    
    # Criar um DataFrame a partir da lista de dados
    if dimensions == ['page', 'query']:
        df = pd.DataFrame([
            {
                'Page': row['keys'][0],
                'Keyword': row['keys'][1],
                'Clicks': row['clicks'],
                'Impressions': row['impressions'],
                'CTR': row['ctr'],
                'Position': row['position']
            } for row in data
        ])
    elif dimensions == ['query', 'page']:
        df = pd.DataFrame([
            {
                'Keyword': row['keys'][0],
                'Page': row['keys'][1],
                'Clicks': row['clicks'],
                'Impressions': row['impressions'],
                'CTR': row['ctr'],
                'Position': row['position']
            } for row in data
        ])
    elif dimensions == ['query']:
        df = pd.DataFrame([
            {
                'Keyword': row['keys'][0],
                'Clicks': row['clicks'],
                'Impressions': row['impressions'],
                'CTR': row['ctr'],
                'Position': row['position']
            } for row in data
        ])
    elif dimensions == ['page']:
        df = pd.DataFrame([
            {
                'Page': row['keys'][0],
                'Clicks': row['clicks'],
                'Impressions': row['impressions'],
                'CTR': row['ctr'],
                'Position': row['position']
            } for row in data
        ])
        
    # Atualizar a barra de progresso para 100% para mostrar que o processamento de dados está completo
    my_bar.progress(1.0, text="Processing is now finished 😸")

    # Aguardar por uma curta duração para exibir a mensagem "Processamento de Dados Completo"
    time.sleep(2)

    # Limpar a barra de progresso para removê-la da interface do aplicativo
    my_bar.empty()
        
    return df

@st.cache_data(show_spinner=False)
def get_data_date(property_url, startDate, endDate, url_filter=None, url_operator=None,
                palavra_filter=None, palavra_operator=None):
        service = get_webproperty(st.session_state.my_token_input)

        # Criar uma lista vazia para armazenar as linhas recuperadas da resposta
        data = []
        
        # Definir o limite de linhas desejado para 300.000 linhas
        row_limit = 1000
        
        # Definir o texto de progresso a ser exibido acima da barra de progresso
        progress_text = "Retrieving Metrics. Please Wait. 🐈"

        # Criar o widget de barra de progresso usando o Streamlit
        my_bar = st.progress(0, text=progress_text)

        # Inicializar a variável 'startRow' para rastrear a linha de início de cada solicitação
        startRow = 0

        while startRow == 0 or startRow % 25000 == 0 and startRow < row_limit:
            # Construir o corpo da solicitação com as variáveis especificadas
            request = {
                'startDate': startDate,
                'endDate': endDate,
                'dimensions': 'date',
                'rowLimit': 25000,
                'startRow': startRow
            }

            if url_filter and url_operator:
                url_dimension_filter = {
                    'dimension': 'PAGE',
                    'operator': url_filter,
                    'expression': url_operator
                }
                request['dimensionFilterGroups'] = [{'filters': [url_dimension_filter]}]

            if palavra_filter and palavra_operator:
                palavra_dimension_filter = {
                    'dimension': 'QUERY',
                    'operator': palavra_filter,
                    'expression': palavra_operator
                }
                if 'dimensionFilterGroups' in request:
                    request['dimensionFilterGroups'].append({'filters': [palavra_dimension_filter]})
                else:
                    request['dimensionFilterGroups'] = [{'filters': [palavra_dimension_filter]}]

            # Armazenar a resposta da API do Google Search Console
            response = service.searchanalytics().query(siteUrl=property_url, body=request).execute()

            # Obter e atualizar as linhas
            rows = response.get('rows', [])
            startRow = startRow + len(rows)

            # Estender a lista de dados com as linhas
            data.extend(rows)
            
            # Calcular a porcentagem de progresso
            progress_percent = min((startRow / row_limit) * 100, 100)

            # Converter a porcentagem de progresso para um valor entre 0.0 e 1.0
            progress_value = progress_percent / 100.0

            # Atualizar a barra de progresso com o progresso atual
            my_bar.progress(progress_value, text=progress_text)
        
        df_date = pd.DataFrame([
            {
                'Date': row['keys'][0],
                'Clicks': row['clicks'],
                'Impressions': row['impressions'],
                'CTR': row['ctr'],
                'Position': row['position']
            } for row in data
        ])
            
        # Atualizar a barra de progresso para 100% para mostrar que o processamento de dados está completo
        my_bar.progress(1.0, text="Processing is now finished. 😸")

        # Aguardar por uma curta duração para exibir a mensagem "Processamento de Dados Completo"
        time.sleep(2)

        # Limpar a barra de progresso para removê-la da interface do aplicativo
        my_bar.empty()
            
        return df_date

@st.cache_data(experimental_allow_widgets=True, show_spinner=False)
def criar_grafico_echarts(df_grouped):
    # Formate a coluna 'CTR' do DataFrame
    df_grouped['CTR'] = df_grouped['CTR'].apply(lambda ctr: f"{ctr * 100:.2f}")
    df_grouped['Position'] = df_grouped['Position'].apply(lambda pos: round(pos, 2))

    # Translated ECharts options
    options = {
        "xAxis": {
            "type": "category",
            "data": df_grouped['Date'].tolist(),
            "axisLabel": {
                "formatter": "{value}"
            }
        },
        "yAxis": {"type": "value", "name": ""},
        "grid": {
            "right": 20,
            "left": 65,
            "top": 45,
            "bottom": 50,
        },
        "legend": {
            "show": True,
            "top": "top",
            "align": "auto",
            "selected": {  # Definindo a seleção inicial das séries
                "Clicks": True,         # A série "Clicks" está selecionada
                "Impressions": True,    # A série "Impressions" está selecionada
                "CTR": False,           # A série "CTR" não está selecionada
                "Position": False       # A série "Position" não está selecionada
            }
        },
        "tooltip": {"trigger": "axis", },
        "series": [
            {
                "type": "line",
                "name": "Clicks",
                "data": df_grouped['Clicks'].tolist(),
                "smooth": True,
                "lineStyle": {"width": 2.4, "color": "#8be9fd"},
                "showSymbol": False,  # Remova os marcadores de dados para esta série
            },
            {
                "type": "line",
                "name": "Impressions",
                "data": df_grouped['Impressions'].tolist(),
                "smooth": True,
                "lineStyle": {"width": 2.4, "color": "#ffb86c"},
                "showSymbol": False,  # Remova os marcadores de dados para esta série
            },
            {
                "type": "line",
                "name": "CTR",
                "data": df_grouped['CTR'].tolist(),
                "smooth": True,
                "lineStyle": {"width": 2.4, "color": "#50fa7b"},
                "showSymbol": False,  # Remova os marcadores de dados para esta série
            },
{
    "type": "line",
    "name": "Position",
    "data": df_grouped['Position'].tolist(),
    "smooth": True,
    "lineStyle": {"width": 2.4, "color": "#ff79c6"},
    "showSymbol": False,  # Remova os marcadores de dados para esta série
    "yAxisIndex": 1,  # Indica que esta série usará o segundo eixo Y
    "axisLabel": {
        "show": False  # Oculta os rótulos do eixo Y para esta série
    }
},
        ],

        "yAxis": [
            {"type": "value", "name": ""},
            {"type": "value", "inverse": True, "show": False},  # Segundo eixo Y com a opção "inverse"
        ],
        "backgroundColor": "#282a36",
        "color": ["#8be9fd", "#ffb86c", "#50fa7b", "#ff79c6"],
    }

    # Exibir o gráfico de linha do ECharts usando st_echarts
    st_echarts(option=options, theme='chalk', height=400, width='100%')
    
def createPage():
    # Criando duas colunas para layout
    colunhead, colundhead2 = st.columns([0.06, 0.99])
    
    # Inserindo animação na primeira coluna
    with colunhead:
        st.image(fc.open_image("./assets/robozin2.png"))

    # Inserindo informações de contatos na segunda coluna
    with colundhead2:
        st.header("Google Search Console API")
        st.markdown('<p class="minha-classe">By <a href="https://viniciusstanula.com/en/">Vinicius Stanula</a>, made in Streamlit 🎈</p>', unsafe_allow_html=True)
        
    if "my_token_input" not in st.session_state:
        st.session_state["my_token_input"] = ""

    if "my_token_received" not in st.session_state:
        st.session_state["my_token_received"] = False
        
    if 'dataframe' not in st.session_state:
        st.session_state.dataframe = None
        
    if 'domain' not in st.session_state:
        st.session_state.domain = None
        
    if 'dataframeData' not in st.session_state:
        st.session_state.dataframeData = None
                 
    if 'clicked' not in st.session_state:
        st.session_state.clicked = False

    def click_button():
        st.session_state.clicked = True
               
    st.markdown("----")
    
    with st.expander("🔑 Log in to Google Search Console"):
        # Estilização do link
        link_style = (
            "text-decoration: none;"
            "color: #FFF;"
            "padding: 8px 20px;"
            "border-radius: 4px;"
            "background-color: #DD4B39;"
            "font-size: 16px;"
        )

        # URL que você deseja vincular ao botão
        url = href

        st.markdown('1 - Log in to your Google account:')
        st.markdown(f'<a href="{url}" target="_blank" style="{link_style}">'
                f'<img src="https://s3-us-west-2.amazonaws.com/s.cdpn.io/14082/icon_google.png" alt="Google" style="vertical-align: middle; margin-right: 10px;">'
                f'Login With Google'
                f'</a>', unsafe_allow_html=True)

        st.markdown('2 - Click the Button to grant API access:')
        submit_button = st.button(
            label="Grant API access", on_click=button_callback
        )

        st.markdown('This is your OAuth token:')
        code = st.text_input(
                "",
                key="my_token_input",
                label_visibility="collapsed",
            )

    c1, c2 = st.columns([1.2, 4])

    with c1:
        # Obtém a URL para consulta
        url = st.text_input('Domain:', help='The desired domain or URL for data extraction, precisely as it appears in Google Search Console.')
        property_url = check_input_url(url)
        
        st.session_state.domain = property_url

        # Seleciona as métricas desejadas
        metricas = st.selectbox(
            'Metrics:',
            ("Keywords", "Pages", "Pages per Keyword", "Keywords per Page"), help='Specify the metric you are interested in filtering for.'
        )

        # Define as dimensões de acordo com as métricas selecionadas
        if metricas == "Keywords per Page":
            dimensions = ['page', 'query']
        elif metricas == "Pages per Keyword":
            dimensions = ['query', 'page']
        elif metricas == "Keywords":
            dimensions = ['query']
        elif metricas == "Pages":
            dimensions = ['page']
            
        # Define a opção de filtrar URL e Palavra-Chave
        cf1, cf2 = st.columns(2)
        with cf1:
            filtro_url = st.checkbox("Filter URL")
        with cf2:
            filtro_palavra = st.checkbox("Filter Keyword")     
            
        c1_1, c1_2 = st.columns(2)
        
        # Define valores padrão para as variáveis de filtro
        url_filter = None
        url_operator = None
        palavra_filter = None
        palavra_operator = None    
        
        # Define as opções de filtro para URL
        if filtro_url:
            with c1_1:
                url_filter = st.selectbox('URL', ("contains", "notcontains", "includingRegex", "excludingRegex"))
            with c1_2:
                url_operator = st.text_input('Filter', key='URL_Operador')
                
        # Define as opções de filtro para Palavra-Chave
        if filtro_palavra:
            with c1_1:
                palavra_filter = st.selectbox('Keywords', ("contains", "notcontains", "includingRegex", "excludingRegex"))
            with c1_2:
                palavra_operator = st.text_input('Filter', key='Palavra_Operador')
                
        # Seleciona o período de data desejado
        day = st.date_input(
            "Time Range:",
            (data_padrao, data_final),
            min_value=data_inicial,
            max_value=data_final,
            format="DD/MM/YYYY",
            help='The available time range is the same as what is available in Google Search Console. DD/MM/YYYY Format'
        )
                
        # Botão para buscar os dados
        button = st.button('Buscar Dados ✨', on_click=click_button)
        
    with c2:
        tab1, tab2 = st.tabs(["📅 Date", "📃 Table"])
        with tab1:
            if button:
                try:
                    # Obtém os dados para a aba "Data"
                    df_date = get_data_date(property_url, day[0].strftime("%Y-%m-%d"), day[1].strftime("%Y-%m-%d"),
                            url_filter=url_filter, url_operator=url_operator,
                            palavra_filter=palavra_filter, palavra_operator=palavra_operator)
                    
                    st.session_state.dataframeData = df_date
                except ValueError as e:
                    if "Please supply either code or authorization_response parameters" in str(e):
                        st.error("⚠️Please grant API access. (If you are seeing a chart, it is a cached version)")
                    else:
                        raise e
            if hasattr(st.session_state, 'dataframeData'):
                try:
                    novo_df = st.session_state.dataframeData                   
                    # Agrupa os dados por data e calcula algumas métricas
                    df_grouped = novo_df.groupby('Date').agg({
                        'Clicks': 'sum',
                        'Impressions': 'sum',
                        'CTR': 'mean',
                        'Position': 'mean'
                    }).reset_index()
                   
                    # Calcula algumas métricas gerais
                    Clicks = novo_df['Clicks'].sum()
                    Impressions = novo_df['Impressions'].sum()
                    ctr_mean = novo_df['CTR'].mean()
                    pos_mean = novo_df['Position'].mean()
                    
                    # Exibe as métricas em formato de cartões
                    met1, met2, met3, met4 = st.columns(4)
                        
                    with met1:
                        st.metric('Clicks:', f'{Clicks:,}')
                    with met2:
                        st.metric('Impressions:', f'{Impressions:,}')
                    with met3:
                        st.metric('CTR:', f'{ctr_mean * 100:.2f}%')
                    with met4:
                        st.metric('Position:', f'{pos_mean:.1f}')
                        
                    
                    with st.container():
                        # Plota o gráfico com as métricas agrupadas por data
                        criar_grafico_echarts(df_grouped)
                    
                    # Botão para download dos dados em formato Excel
                    df_xlsx = to_excel(novo_df)
                    excel_date_filename = f'API-GSC-{st.session_state.domain}.xlsx'
                    st.download_button(label='📥 Download Excel',
                                    data=df_xlsx,
                                    file_name=excel_date_filename,
                                      key='download-chart')
                except AttributeError:
                    pass
                                
        with tab2:
            if button:
                try:
                    df = get_data(property_url, dimensions, day[0].strftime("%Y-%m-%d"), day[1].strftime("%Y-%m-%d"),
                    url_filter=url_filter, url_operator=url_operator,
                    palavra_filter=palavra_filter, palavra_operator=palavra_operator)
                    
                    st.session_state.dataframe = df
                except ValueError as e:
                    if "Please supply either code or authorization_response parameters" in str(e):
                        st.error("⚠️Please grant API access. (If you are seeing a chart, it is a cached version)")
                    else:
                        raise e
            if hasattr(st.session_state, 'dataframe'):
                try:
                    # Obtém os dados para a aba "Tabela"
                    met1, met2, met3, met4 = st.columns(4)

                    filtered_df = filter_dataframe(st.session_state.dataframe)
                    
                    # Calcula algumas métricas gerais
                    Clicks = filtered_df['Clicks'].sum()
                    Impressions = filtered_df['Impressions'].sum()
                    ctr_mean = filtered_df['CTR'].mean()
                    pos_mean = filtered_df['Position'].mean()
                    filtered_df['CTR'] = filtered_df['CTR']
                    
                    # Exibe as métricas em formato de cartões
                    with met1:
                        st.metric('Clicks:', f'{Clicks:,}')
                    with met2:
                        st.metric('Impressions:', f'{Impressions:,}')
                    with met3:
                        st.metric('CTR:', f'{ctr_mean * 100:.2f}%')
                    with met4:
                        st.metric('Position:', f'{pos_mean:.1f}')     

                    # Exibe os dados em formato de tabela
                    st.dataframe(filtered_df.assign(CTR=lambda x: x['CTR'].apply(lambda ctr: f"{ctr * 100:.2f}%")), use_container_width=True)
                    
                    gerarExcel = st.checkbox('Generate Excel')
                    if gerarExcel:
                        # Botão para download dos dados em formato Excel
                        df_xlsx = to_excel(filtered_df)
                        excel_filename = f'API-GSC-{st.session_state.domain}.xlsx'
                        st.download_button(label='📥 Download Excel',
                                        data=df_xlsx,
                                        file_name=excel_filename,
                                          key='botao_download_table')
                except TypeError as e:
                        if "NoneType" in str(e):
                            pass
                        else:
                            raise e
                except AttributeError as e:
                    st.error("⚠️ There's no data to be filtered, please fill in the camps on the side.")
                except ValueError as e:
                        if "Please supply either code or authorization_response parameters" in str(e):
                            st.warning("Please supply either code or authorization_response parameters")
                        else:
                            raise e
    return True
