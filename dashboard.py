# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import datetime
import logging
from utils import sanitizar_nome_arquivo, generate_csv_zip, extrair_cils_do_xlsx

logger = logging.getLogger(__name__)

# Tentar importar Plotly com fallback
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

def mostrar_dashboard_geral(db_manager):
    """Dashboard geral com métricas e visualizações com seleção de critérios."""
    st.markdown("## 📊 Dashboard Geral - Métricas do Sistema")
    
    if not PLOTLY_AVAILABLE:
        st.error("""
        ❌ **Plotly não está disponível**
        
        Para visualizar os gráficos, instale o Plotly:
        ```bash
        pip install plotly
        ```
        """)
        return
    
    # --- SELEÇÃO DE CRITÉRIOS PARA DASHBOARD ---
    st.markdown("### 🔍 Seleção de Critérios para Análise")
    
    criterios_dashboard = [
        "Criterio", 
        "Anomalia", 
        "EST_CTR", 
        "sit_div", 
        "est_inspec",
        "desv"
    ]
    
    col1, col2 = st.columns(2)
    
    with col1:
        criterio_principal = st.selectbox(
            "Critério Principal para Análise:",
            criterios_dashboard,
            index=0,
            help="Selecione o critério principal para os gráficos e análises"
        )
    
    with col2:
        # Filtro opcional por valor específico do critério
        valores_criterio = db_manager.obter_valores_unicos(criterio_principal.lower())
        filtro_valor = st.selectbox(
            f"Filtrar por valor específico de {criterio_principal}:",
            ["Todos"] + (valores_criterio if valores_criterio else []),
            help="Opcional: selecione um valor específico para filtrar os dados"
        )
    
    st.markdown("---")
    
    # Obter dados com base nos critérios selecionados
    with st.spinner("Carregando dados do dashboard..."):
        estatisticas = db_manager.obter_estatisticas_gerais()
        metricas = db_manager.obter_metricas_operacionais()
        
        # Obter dados específicos para o critério selecionado
        dados_criterio_selecionado = db_manager.obter_dados_para_dashboard(criterio_principal, filtro_valor if filtro_valor != "Todos" else None)
    
    if not estatisticas:
        st.error("❌ Não foi possível carregar os dados do dashboard.")
        return
    
    stats = estatisticas['estatisticas_gerais']
    
    # Métricas Principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total de Registros",
            value=f"{stats.get('total_registros', 0):,}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="CILs Únicos",
            value=f"{stats.get('cils_unicos', 0):,}",
            delta=None
        )
    
    with col3:
        progresso_percent = (stats.get('registros_em_progresso', 0) / max(stats.get('total_registros', 1), 1)) * 100
        st.metric(
            label="Em Progresso",
            value=f"{stats.get('registros_em_progresso', 0):,}",
            delta=f"{progresso_percent:.1f}%"
        )
    
    with col4:
        st.metric(
            label="Valor Total",
            value=f"R$ {stats.get('total_valor', 0):,.2f}",
            delta=None
        )
    
    st.markdown("---")
    
    # Gráficos e Visualizações baseados no critério selecionado
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Gráfico de Distribuição pelo Critério Selecionado
        if dados_criterio_selecionado and 'distribuicao_criterio' in dados_criterio_selecionado:
            df_criterio = pd.DataFrame(dados_criterio_selecionado['distribuicao_criterio'])
            if not df_criterio.empty:
                try:
                    # Limitar a 15 itens para melhor visualização
                    df_criterio = df_criterio.head(15)
                    
                    fig_criterio = px.pie(
                        df_criterio, 
                        values='quantidade', 
                        names=criterio_principal.lower(),
                        title=f'Distribuição por {criterio_principal}',
                        hole=0.4
                    )
                    fig_criterio.update_layout(
                        showlegend=True,
                        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.1)
                    )
                    st.plotly_chart(fig_criterio, use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao criar gráfico de {criterio_principal}: {e}")
                    # Fallback: mostrar tabela
                    st.dataframe(df_criterio, use_container_width=True)
            else:
                st.info(f"ℹ️ Sem dados de {criterio_principal} para exibir")
        else:
            st.info(f"ℹ️ Aguardando dados de {criterio_principal}")
    
    with col_right:
        # Gráfico de Barras com Valor Total por Critério
        if dados_criterio_selecionado and 'distribuicao_criterio' in dados_criterio_selecionado:
            df_criterio_valor = pd.DataFrame(dados_criterio_selecionado['distribuicao_criterio'])
            if not df_criterio_valor.empty:
                try:
                    # Ordenar por valor total e limitar a 10 itens
                    df_criterio_valor = df_criterio_valor.nlargest(10, 'total_valor')
                    
                    fig_barras = px.bar(
                        df_criterio_valor,
                        x=criterio_principal.lower(),
                        y='total_valor',
                        title=f'Top 10 {criterio_principal} por Valor Total',
                        color='total_valor',
                        labels={'total_valor': 'Valor Total (R$)', criterio_principal.lower(): criterio_principal}
                    )
                    fig_barras.update_layout(
                        xaxis_tickangle=-45,
                        showlegend=False
                    )
                    st.plotly_chart(fig_barras, use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao criar gráfico de barras: {e}")
                    st.dataframe(df_criterio_valor, use_container_width=True)
            else:
                st.info(f"ℹ️ Sem dados de valor para {criterio_principal}")
    
    # --- ANÁLISE COMPARATIVA ENTRE CRITÉRIOS ---
    st.markdown("### 📈 Análise Comparativa")
    
    col_comp1, col_comp2 = st.columns(2)
    
    with col_comp1:
        # Selecionar segundo critério para comparação
        criterio_comparacao = st.selectbox(
            "Critério para Comparação:",
            [c for c in criterios_dashboard if c != criterio_principal],
            help="Selecione um segundo critério para análise comparativa"
        )
    
    with col_comp2:
        if st.button("🔄 Gerar Análise Comparativa", type="secondary"):
            with st.spinner("Gerando análise comparativa..."):
                dados_comparacao = db_manager.obter_dados_para_dashboard(criterio_comparacao, None)
                
                if dados_comparacao and 'distribuicao_criterio' in dados_comparacao:
                    df_comparacao = pd.DataFrame(dados_comparacao['distribuicao_criterio'])
                    if not df_comparacao.empty:
                        st.info(f"**Distribuição por {criterio_comparacao}**")
                        
                        # Gráfico de comparação
                        try:
                            df_comparacao_top = df_comparacao.nlargest(8, 'quantidade')
                            
                            fig_comparacao = px.bar(
                                df_comparacao_top,
                                x=criterio_comparacao.lower(),
                                y=['quantidade', 'total_valor'],
                                title=f'Comparação: {criterio_comparacao} (Quantidade vs Valor)',
                                barmode='group'
                            )
                            fig_comparacao.update_layout(xaxis_tickangle=-45)
                            st.plotly_chart(fig_comparacao, use_container_width=True)
                        except Exception as e:
                            st.error(f"Erro ao criar gráfico de comparação: {e}")
                            st.dataframe(df_comparacao[['quantidade', 'total_valor']].head(10), use_container_width=True)
    
    # --- ESTATÍSTICAS DETALHADAS DO CRITÉRIO SELECIONADO ---
    st.markdown(f"### 📋 Estatísticas Detalhadas - {criterio_principal}")
    
    if dados_criterio_selecionado and 'distribuicao_criterio' in dados_criterio_selecionado:
        df_detalhes = pd.DataFrame(dados_criterio_selecionado['distribuicao_criterio'])
        
        if not df_detalhes.empty:
            # Métricas resumidas
            total_registros_criterio = df_detalhes['quantidade'].sum()
            total_valor_criterio = df_detalhes['total_valor'].sum()
            valor_medio = total_valor_criterio / total_registros_criterio if total_registros_criterio > 0 else 0
            
            col_met1, col_met2, col_met3 = st.columns(3)
            
            with col_met1:
                st.metric(
                    f"Total Registros ({criterio_principal})",
                    f"{total_registros_criterio:,}"
                )
            
            with col_met2:
                st.metric(
                    f"Valor Total ({criterio_principal})",
                    f"R$ {total_valor_criterio:,.2f}"
                )
            
            with col_met3:
                st.metric(
                    f"Valor Médio ({criterio_principal})",
                    f"R$ {valor_medio:,.2f}"
                )
            
            # Tabela detalhada
            st.dataframe(
                df_detalhes.rename(columns={
                    criterio_principal.lower(): criterio_principal,
                    'quantidade': 'Quantidade',
                    'total_valor': 'Valor Total (R$)'
                }),
                use_container_width=True,
                height=400
            )
            
            # Opção de download
            csv = df_detalhes.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Download Dados Detalhados",
                data=csv,
                file_name=f"dashboard_{criterio_principal}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    # Mapa de Calor Geográfico (mantido da versão anterior)
    st.markdown("### 🗺️ Densidade Geográfica")
    if metricas.get('geolocalizacao'):
        df_geo = pd.DataFrame(metricas['geolocalizacao'])
        if not df_geo.empty and len(df_geo) > 1:
            try:
                # Usar coordenadas médias como centro do mapa
                lat_center = df_geo['lat'].mean()
                lon_center = df_geo['long'].mean()
                
                fig_mapa = px.density_mapbox(
                    df_geo,
                    lat='lat',
                    lon='long',
                    z='densidade',
                    radius=20,
                    center=dict(lat=lat_center, lon=lon_center),
                    zoom=10,
                    mapbox_style="open-street-map",
                    title="Densidade de Registros por Localização"
                )
                st.plotly_chart(fig_mapa, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao criar mapa: {e}")
                st.info("📍 **Dados de localização disponíveis:**")
                st.dataframe(df_geo[['lat', 'long', 'densidade']].head(10), use_container_width=True)
        else:
            st.info("ℹ️ Dados geográficos insuficientes para exibir o mapa")
    else:
        st.info("ℹ️ Sem dados de geolocalização disponíveis")

def mostrar_relatorio_operacional(db_manager):
    """Relatório operacional detalhado."""
    st.markdown("## 📈 Relatório Operacional")
    
    # Filtros
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        criterios = db_manager.obter_valores_unicos('criterio')
        filtro_criterio = st.selectbox("Filtrar por Critério:", [""] + (criterios if criterios else []))
    
    with col2:
        pts = db_manager.obter_valores_unicos('pt')
        filtro_pt = st.selectbox("Filtrar por PT:", [""] + (pts if pts else []))
    
    with col3:
        localidades = db_manager.obter_valores_unicos('localidade')
        filtro_localidade = st.selectbox("Filtrar por Localidade:", [""] + (localidades if localidades else []))
    
    with col4:
        estados = ["", "prog", ""]
        filtro_estado = st.selectbox("Filtrar por Estado:", estados)
    
    # Aplicar filtros
    filtros = {}
    if filtro_criterio and filtro_criterio != "":
        filtros['criterio'] = filtro_criterio
    if filtro_pt and filtro_pt != "":
        filtros['pt'] = filtro_pt
    if filtro_localidade and filtro_localidade != "":
        filtros['localidade'] = filtro_localidade
    if filtro_estado and filtro_estado != "":
        filtros['estado'] = filtro_estado
    
    if st.button("🔄 Gerar Relatório", type="primary"):
        with st.spinner("Gerando relatório..."):
            df_relatorio = db_manager.gerar_relatorio_detalhado(filtros)
            
        if not df_relatorio.empty:
            st.success(f"✅ Relatório gerado com {len(df_relatorio)} registros")
            
            # Métricas do relatório
            total_valor = df_relatorio['valor'].sum()
            media_valor = df_relatorio['valor'].mean()
            registros_prog = len(df_relatorio[df_relatorio['estado'] == 'prog'])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total do Relatório", f"R$ {total_valor:,.2f}")
            col2.metric("Valor Médio", f"R$ {media_valor:,.2f}")
            col3.metric("Em Progresso", registros_prog)
            
            # Tabela de dados
            st.dataframe(df_relatorio, use_container_width=True)
            
            # Opção de download
            csv = df_relatorio.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"relatorio_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ Nenhum dado encontrado com os filtros aplicados")

def mostrar_analise_eficiencia(db_manager):
    """Análise de eficiência por PT e Localidade."""
    st.markdown("## 📊 Análise de Eficiência")
    
    if not PLOTLY_AVAILABLE:
        st.error("Plotly necessário para visualizações gráficas. Instale com: pip install plotly")
        # Mostrar apenas tabelas
        with st.spinner("Carregando métricas de eficiência..."):
            metricas = db_manager.obter_metricas_operacionais()
        
        if metricas.get('eficiencia_pt'):
            df_eficiencia = pd.DataFrame(metricas['eficiencia_pt'])
            st.dataframe(df_eficiencia, use_container_width=True)
        return
    
    with st.spinner("Carregando métricas de eficiência..."):
        metricas = db_manager.obter_metricas_operacionais()
    
    if not metricas.get('eficiencia_pt'):
        st.info("ℹ️ Sem dados de eficiência disponíveis")
        return
    
    df_eficiencia = pd.DataFrame(metricas['eficiencia_pt'])
    
    # Gráfico de eficiência
    try:
        fig_eficiencia = px.bar(
            df_eficiencia.head(10),
            x='pt',
            y='percentual_progresso',
            title='Top 10 PTs por Percentual em Progresso',
            color='percentual_progresso',
            labels={'percentual_progresso': '% em Progresso', 'pt': 'PT'}
        )
        fig_eficiencia.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_eficiencia, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao criar gráfico de eficiência: {e}")
    
    # Tabela detalhada
    st.markdown("### 📋 Detalhamento por PT")
    st.dataframe(
        df_eficiencia[['pt', 'total_registros', 'em_progresso', 'percentual_progresso', 'valor_total']],
        use_container_width=True
    )
    
    # Análise por localidade
    if metricas.get('top_localidades'):
        st.markdown("### 🏙️ Top Localidades por Valor")
        df_localidades = pd.DataFrame(metricas['top_localidades'])
        
        try:
            fig_localidades = px.treemap(
                df_localidades.head(8),
                path=['localidade'],
                values='valor_total',
                title='Distribuição de Valor por Localidade (Top 8)'
            )
            st.plotly_chart(fig_localidades, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao criar treemap: {e}")
            st.dataframe(df_localidades, use_container_width=True)

def mostrar_relatorio_usuarios(db_manager):
    """Relatório de atividade de usuários."""
    st.markdown("## 👥 Relatório de Usuários")
    
    if not PLOTLY_AVAILABLE:
        st.warning("Gráficos de usuários não disponíveis sem Plotly")
    
    try:
        usuarios = db_manager.obter_usuarios()
        
        if usuarios:
            df_usuarios = pd.DataFrame(usuarios, columns=['ID', 'Username', 'Nome', 'Role', 'Data_Criacao'])
            
            # Estatísticas de usuários
            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Usuários", len(usuarios))
            
            admin_count = len(df_usuarios[df_usuarios['Role'] == 'Administrador'])
            tecnico_count = len(df_usuarios[df_usuarios['Role'] == 'Técnico'])
            assistente_count = len(df_usuarios[df_usuarios['Role'] == 'Assistente Administrativo'])
            
            col2.metric("Administradores", admin_count)
            col3.metric("Técnicos/Assistentes", tecnico_count + assistente_count)
            
            # Gráfico de distribuição por role
            if PLOTLY_AVAILABLE:
                try:
                    role_count = df_usuarios['Role'].value_counts()
                    fig_roles = px.pie(
                        values=role_count.values,
                        names=role_count.index,
                        title='Distribuição de Usuários por Função'
                    )
                    st.plotly_chart(fig_roles, use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao criar gráfico de roles: {e}")
            
            # Tabela de usuários
            st.markdown("### 📋 Lista de Usuários")
            st.dataframe(df_usuarios, use_container_width=True)
            
        else:
            st.info("ℹ️ Nenhum usuário cadastrado no sistema")
            
    except Exception as e:
        st.error(f"❌ Erro ao carregar relatório de usuários: {e}")

def reset_state_form(db_manager, reset_key):
    """Formulário para resetar o estado 'prog'."""
    st.markdown("### 🔄 Resetar Estado de Registros")
    
    tipos_reset = ["PT", "LOCALIDADE", "AVULSO"]
    tipo_reset = st.selectbox("Selecione o Tipo de Reset:", tipos_reset, key=f"reset_type_{reset_key}")
    
    valor_reset = ""
    if tipo_reset in ["PT", "LOCALIDADE"]:
        coluna = tipo_reset
        valores_unicos = db_manager.obter_valores_unicos(coluna)
        if valores_unicos:
            valores_unicos.insert(0, "Selecione...")
            valor_reset = st.selectbox(f"Selecione o valor de **{coluna}** a resetar:", valores_unicos, key=f"reset_value_{reset_key}")
        else:
            st.warning(f"Nenhum valor encontrado para {coluna}")
            
    elif tipo_reset == "AVULSO":
        st.warning("⚠️ O reset 'Avulso' apagará o estado 'prog' de **TODOS** os registros no banco, independentemente de PT/Localidade.")
        
    if st.button(f"🔴 Confirmar Reset - {tipo_reset}", key=f"reset_button_{reset_key}", type="primary"):
        if tipo_reset in ["PT", "LOCALIDADE"] and valor_reset in ["Selecione...", ""]:
            st.error("Por favor, selecione um valor válido para PT ou Localidade.")
        else:
            with st.spinner("Resetando estado..."):
                sucesso, resultado = db_manager.resetar_estado(tipo_reset, valor_reset)
            if sucesso:
                st.success(f"✅ Reset concluído. {resultado} registro(s) tiveram o estado 'prog' removido.")
            else:
                st.error(f"❌ Falha ao resetar: {resultado}")

def manager_page(db_manager):
    """Página principal após o login."""
    
    user = st.session_state['user']
    st.sidebar.markdown(f"**👤 Usuário:** {user['nome']}")
    st.sidebar.markdown(f"**🎯 Função:** {user['role']}")
    
    # Botão de Logout
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state['authenticated'] = False
        st.session_state['user'] = None
        logger.info(f"Logout realizado por: {user['nome']}")
        st.rerun()

    # --- Alteração de Senha Pessoal ---
    st.sidebar.markdown("---")
    with st.sidebar.expander("🔐 Alterar Minha Senha"):
        with st.form("alterar_minha_senha"):
            nova_senha = st.text_input("Nova Senha", type="password", key="nova_senha_pessoal")
            confirmar_senha = st.text_input("Confirmar Nova Senha", type="password", key="confirmar_senha_pessoal")
            if st.form_submit_button("Alterar Minha Senha", use_container_width=True):
                if nova_senha and confirmar_senha:
                    if nova_senha == confirmar_senha:
                        if len(nova_senha) >= 6:
                            sucesso, mensagem = db_manager.alterar_senha(user['id'], nova_senha)
                            if sucesso:
                                st.success("✅ Senha alterada com sucesso!")
                            else:
                                st.error(f"❌ {mensagem}")
                        else:
                            st.error("❌ A senha deve ter pelo menos 6 caracteres.")
                    else:
                        st.error("❌ As senhas não coincidem.")
                else:
                    st.error("❌ Preencha todos os campos.")

    st.title(f"Bem-vindo(a), {user['nome']}!")
    
    # --- Controle de Acesso Baseado em Role ---
    if user['role'] == 'Administrador':
        st.header("Gerenciamento de Dados e Relatórios")
        
        # NOVAS ABAS PARA ADMINISTRADOR
        tabs = [
            "Dashboard Geral", 
            "Relatório Operacional", 
            "Análise de Eficiência", 
            "Relatório de Usuários",
            "Importação", 
            "Geração de Folhas", 
            "Gerenciamento de Usuários", 
            "Reset de Estado"
        ]
        selected_tab = st.selectbox("Selecione a Ação:", tabs)
        
    elif user['role'] == 'Assistente Administrativo':
        st.header("Geração de Folhas de Trabalho")
        selected_tab = "Geração de Folhas"
        
    elif user['role'] == 'Técnico':
        st.header("Geração de Folhas de Trabalho")
        selected_tab = "Geração de Folhas"
        
    else:
        st.error("❌ Role de usuário não reconhecido.")
        return

    # =========================================================================
    # NOVAS ABAS DE RELATÓRIOS (APENAS ADMINISTRADOR)
    # =========================================================================
    
    if selected_tab == "Dashboard Geral":
        if user['role'] != 'Administrador':
            st.error("❌ Acesso negado. Apenas Administradores podem acessar o dashboard.")
            return
        mostrar_dashboard_geral(db_manager)
        
    elif selected_tab == "Relatório Operacional":
        if user['role'] != 'Administrador':
            st.error("❌ Acesso negado. Apenas Administradores podem acessar relatórios.")
            return
        mostrar_relatorio_operacional(db_manager)
        
    elif selected_tab == "Análise de Eficiência":
        if user['role'] != 'Administrador':
            st.error("❌ Acesso negado. Apenas Administradores podem acessar análises.")
            return
        mostrar_analise_eficiencia(db_manager)
        
    elif selected_tab == "Relatório de Usuários":
        if user['role'] != 'Administrador':
            st.error("❌ Acesso negado. Apenas Administradores podem acessar relatórios de usuários.")
            return
        mostrar_relatorio_usuarios(db_manager)
        
    # =========================================================================
    # ABAS ORIGINAIS (MANTIDAS)
    # =========================================================================
    
    elif selected_tab == "Importação":
        if user['role'] != 'Administrador':
            st.error("❌ Acesso negado. Apenas Administradores podem importar dados.")
            return
            
        st.markdown("### 📥 Importação de Arquivo CSV (Tabela BD)")
        st.warning("⚠️ Atenção: A importação **substituirá** todos os dados existentes na tabela BD, exceto os registros que já estavam com o estado 'prog'.")

        uploaded_file = st.file_uploader("Selecione o arquivo CSV:", type=["csv"], key="import_csv")

        if uploaded_file is not None:
            if st.button("Processar e Importar para o Banco de Dados", type="primary"):
                with st.spinner("Processando e importando..."):
                    if db_manager.importar_csv(uploaded_file, 'BD'):
                        st.success("🎉 Importação concluída com sucesso!")
                        st.info("O banco de dados foi atualizado.")
                    else:
                        st.error("Falha na importação. Verifique o formato do arquivo e o console para detalhes.")
                        
    elif selected_tab == "Geração de Folhas":
        st.markdown("### 📝 Geração de Folhas de Trabalho")

        tipos_folha = ["PT", "LOCALIDADE", "AVULSO"]
        tipo_selecionado = st.radio("Tipo de Geração:", tipos_folha, horizontal=True)
        
        valor_selecionado = None
        arquivo_xlsx = None
        
        if tipo_selecionado in ["PT", "LOCALIDADE"]:
            coluna = tipo_selecionado
            valores_unicos = db_manager.obter_valores_unicos(coluna)
            if valores_unicos:
                valores_unicos.insert(0, "Selecione...")
                valor_selecionado = st.selectbox(f"Selecione o valor de **{coluna}**:", valores_unicos)
                if valor_selecionado == "Selecione...":
                    valor_selecionado = None
            else:
                st.warning(f"Nenhum valor encontrado para {coluna}")
                
        elif tipo_selecionado == "AVULSO":
            st.markdown("""
            #### 📋 Importar Lista de CILs via Arquivo XLSX
            
            **Instruções:**
            1. Prepare um arquivo Excel (.xlsx) com uma coluna contendo os CILs
            2. A coluna preferencialmente deve se chamar **'cil'**
            3. Faça o upload do arquivo abaixo
            4. O sistema irá automaticamente detectar e extrair os CILs
            """)
            
            arquivo_xlsx = st.file_uploader(
                "Faça upload do arquivo XLSX com a lista de CILs", 
                type=["xlsx"], 
                key="upload_cils_xlsx",
                help="O arquivo deve conter uma coluna com os CILs (preferencialmente chamada 'cil')"
            )
            
            if arquivo_xlsx is not None:
                try:
                    df_preview = pd.read_excel(arquivo_xlsx)
                    st.success(f"✅ Arquivo carregado com sucesso! {len(df_preview)} linhas encontradas.")
                    
                    with st.expander("👀 Visualizar primeiras linhas do arquivo"):
                        st.dataframe(df_preview.head(10))
                        
                    cils_do_arquivo = extrair_cils_do_xlsx(arquivo_xlsx)
                    if cils_do_arquivo:
                        st.info(f"📊 {len(cils_do_arquivo)} CIL(s) único(s) identificado(s)")
                        st.write("**Primeiros CILs encontrados:**", ", ".join(cils_do_arquivo[:5]) + ("..." if len(cils_do_arquivo) > 5 else ""))
                except Exception as e:
                    st.error(f"❌ Erro ao processar arquivo: {e}")

        # --- Seleção de Critério ---
        st.markdown("### 🔍 Critério de Seleção")

        criterio_opcoes = ["Criterio", "Anomalia", "DESC_TP_CLI", "EST_CTR", "sit_div", "desv", "est_inspec"]
        criterio_selecionado = st.radio(
            "Selecione o tipo de critério:",
            criterio_opcoes,
            horizontal=True,
            key="criterio_tipo"
        )

        # Obter valores únicos baseados no critério selecionado
        if criterio_selecionado:
            valores_criterio = db_manager.obter_valores_unicos(criterio_selecionado.lower())
            
            if criterio_selecionado == "Criterio":
                if "SUSP" in valores_criterio:
                    valor_criterio_selecionado = "SUSP"
                    st.info(f"🔍 **Critério selecionado:** {criterio_selecionado} = '{valor_criterio_selecionado}'")
                else:
                    st.error("❌ Critério 'SUSP' não encontrado no banco de dados.")
                    valor_criterio_selecionado = None
            else:
                if valores_criterio:
                    valores_criterio.insert(0, "Selecione...")
                    valor_criterio_selecionado = st.selectbox(
                        f"Selecione o valor para **{criterio_selecionado}**:",
                        valores_criterio,
                        key="criterio_valor"
                    )
                    if valor_criterio_selecionado == "Selecione...":
                        valor_criterio_selecionado = None
                else:
                    st.warning(f"ℹ️ Nenhum valor encontrado para {criterio_selecionado}.")
                    valor_criterio_selecionado = None
        else:
            valor_criterio_selecionado = None
                
        # Parâmetros de Geração
        col1, col2 = st.columns(2)
        with col1:
            num_nibs_por_folha = st.number_input("NIBs por Folha:", min_value=1, value=50)
        with col2:
            max_folhas = st.number_input("Máximo de Folhas a Gerar:", min_value=1, value=10)

        if st.button("Gerar e Baixar Folhas de Trabalho", type="primary"):
            if tipo_selecionado != "AVULSO" and not valor_selecionado:
                st.error("Por favor, selecione um valor válido de PT ou Localidade.")
            elif tipo_selecionado == "AVULSO" and not arquivo_xlsx:
                st.error("Por favor, faça upload de um arquivo XLSX com a lista de CILs.")
            elif not criterio_selecionado or not valor_criterio_selecionado:
                st.error("Por favor, selecione um critério de filtro válido.")
            else:
                cils_validos = None
                if tipo_selecionado == "AVULSO":
                    cils_validos = extrair_cils_do_xlsx(arquivo_xlsx)
                    if not cils_validos:
                        st.error("Nenhum CIL válido encontrado no arquivo XLSX. Verifique o formato do arquivo.")
                        return

                with st.spinner("Gerando folhas de trabalho e atualizando estado no banco..."):
                    df_folhas, cils_nao_encontrados = db_manager.gerar_folhas_trabalho(
                        tipo_selecionado, 
                        valor_selecionado, 
                        max_folhas, 
                        num_nibs_por_folha, 
                        cils_validos,
                        criterio_selecionado,
                        valor_criterio_selecionado
                    )
                    
                if df_folhas is not None and not df_folhas.empty:
                    st.success(f"✅ {df_folhas['FOLHA'].max()} Folhas geradas com sucesso.")
                    
                    colunas_exportadas = ['cil', 'prod', 'contador', 'leitura', 'mat_contador', 
                                        'med_fat', 'qtd', 'valor', 'situacao', 'acordo']
                    st.info(f"📋 Cada folha CSV contém as {len(colunas_exportadas)} primeiras colunas: {', '.join(colunas_exportadas)}")
                    
                    zip_data = generate_csv_zip(df_folhas, num_nibs_por_folha, criterio_selecionado, valor_criterio_selecionado)
                    
                    nome_zip = f"Folhas_{criterio_selecionado}_{sanitizar_nome_arquivo(valor_criterio_selecionado)}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                    
                    st.download_button(
                        label="📦 Baixar Arquivo ZIP com Folhas (CSV)",
                        data=zip_data,
                        file_name=nome_zip,
                        mime="application/zip",
                        type="primary"
                    )
                    
                    st.info(f"📝 **Nome das folhas:** Cada folha será nomeada como `{criterio_selecionado}_{sanitizar_nome_arquivo(valor_criterio_selecionado)}_Folha_X.csv`")
                    
                    if tipo_selecionado == "AVULSO":
                        if cils_nao_encontrados:
                            st.warning(f"⚠️ {len(cils_nao_encontrados)} CIL(s) não foram encontrados (ou já estavam em 'prog'/não atendem ao critério):")
                            st.code(", ".join(cils_nao_encontrados[:20]) + ("..." if len(cils_nao_encontrados) > 20 else ""))
                            
                        if cils_validos:
                            cils_encontrados = len(cils_validos) - len(cils_nao_encontrados)
                            st.success(f"📊 **Resultado:** {cils_encontrados} de {len(cils_validos)} CIL(s) processados com sucesso.")
                    else:
                        st.success(f"📊 Folhas geradas para {tipo_selecionado}: {valor_selecionado}")
                        
                elif df_folhas is None:
                    if tipo_selecionado == "AVULSO":
                        st.warning("⚠️ Nenhuma folha gerada. Verifique se os CILs existem no banco e atendem ao critério selecionado.")
                    else:
                        st.warning("⚠️ Nenhuma folha gerada. Verifique se existem registros que atendam ao critério selecionado para o valor escolhido.")

    elif selected_tab == "Gerenciamento de Usuários":
        if user['role'] != 'Administrador':
            st.error("❌ Acesso negado. Apenas Administradores podem gerenciar usuários.")
            return

        st.markdown("### 🧑‍💻 Gerenciamento de Usuários")
        
        # --- Criar Novo Usuário ---
        with st.expander("➕ Criar Novo Usuário"):
            with st.form("new_user_form"):
                new_username = st.text_input("Nome de Usuário (login)")
                new_name = st.text_input("Nome Completo")
                new_password = st.text_input("Senha", type="password")
                new_role = st.selectbox("Função:", ['Administrador', 'Assistente Administrativo', 'Técnico'])
                
                if st.form_submit_button("Criar Usuário", type="primary"):
                    if not new_username or not new_password or not new_name:
                        st.error("Preencha todos os campos obrigatórios.")
                    elif len(new_password) < 6:
                        st.error("A senha deve ter pelo menos 6 caracteres.")
                    else:
                        sucesso, mensagem = db_manager.criar_usuario(new_username, new_password, new_name, new_role)
                        if sucesso:
                            st.success(mensagem)
                            st.rerun()
                        else:
                            st.error(mensagem)
                        
        st.markdown("---")
        
        # --- Visualizar/Editar/Excluir Usuários ---
        st.subheader("Lista de Usuários Existentes")
        usuarios = db_manager.obter_usuarios()
        
        if usuarios:
            # Paginação
            items_per_page = 10
            total_pages = (len(usuarios) + items_per_page - 1) // items_per_page
            page_number = st.number_input('Página', min_value=1, max_value=total_pages, value=1, step=1)
            start_index = (page_number - 1) * items_per_page
            end_index = start_index + items_per_page
            usuarios_page = usuarios[start_index:end_index]

            for u in usuarios_page:
                col_u1, col_u2, col_u3, col_u4 = st.columns([2, 2, 2, 3])
                
                user_id = u[0]
                
                with col_u1:
                    st.text_input("Login", u[1], key=f"user_login_{user_id}", disabled=True)
                with col_u2:
                    nome_edit = st.text_input("Nome", u[2], key=f"user_name_{user_id}")
                with col_u3:
                    roles = ['Administrador', 'Assistente Administrativo', 'Técnico']
                    try:
                        current_index = roles.index(u[3])
                    except ValueError:
                        current_index = 0
                    role_edit = st.selectbox("Função", roles, index=current_index, key=f"user_role_{user_id}")

                with col_u4:
                    action = st.radio(
                        "Ação", 
                        ['Nenhuma', 'Editar', 'Alterar Senha', 'Excluir'], 
                        key=f"user_action_{user_id}", 
                        horizontal=True
                    )
                    
                    # Ações
                    if action == 'Editar' and st.button("Salvar Edição", key=f"save_edit_{user_id}"):
                        sucesso, mensagem = db_manager.editar_usuario(user_id, nome_edit, role_edit)
                        if sucesso: 
                            st.success(mensagem)
                            st.rerun()
                        else: 
                            st.error(mensagem)
                        
                    elif action == 'Alterar Senha':
                        new_pass_edit = st.text_input("Nova Senha", type="password", key=f"new_pass_{user_id}")
                        if st.button("Confirmar Alteração de Senha", key=f"save_pass_{user_id}"):
                            if new_pass_edit:
                                if len(new_pass_edit) < 6:
                                    st.error("A senha deve ter pelo menos 6 caracteres.")
                                else:
                                    sucesso, mensagem = db_manager.alterar_senha(user_id, new_pass_edit)
                                    if sucesso: 
                                        st.success(mensagem)
                                        st.rerun()
                                    else: 
                                        st.error(mensagem)
                            else:
                                st.warning("A senha não pode ser vazia.")
                                
                    elif action == 'Excluir' and st.button("⚠️ Confirmar Exclusão", key=f"confirm_delete_{user_id}"):
                        if user_id == 1 and u[1] == 'Admin':
                            st.error("Não é permitido excluir o usuário Administrador Principal padrão.")
                        else:
                            sucesso, mensagem = db_manager.excluir_usuario(user_id)
                            if sucesso: 
                                st.success(mensagem)
                                st.rerun()
                            else: 
                                st.error(mensagem)

            st.write(f"Página {page_number} de {total_pages} - Total de {len(usuarios)} usuários")
        else:
            st.info("Nenhum usuário encontrado no banco de dados.")

    elif selected_tab == "Reset de Estado":
        if user['role'] != 'Administrador':
            st.error("❌ Acesso negado. Apenas Administradores podem resetar o estado.")
            return

        reset_state_form(db_manager, "main")
