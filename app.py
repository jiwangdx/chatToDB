import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv

from database import parse_connection_string, execute_query, get_tables, get_table_schema, get_table_row_count
from ai_services import translate_to_sql, explain_results, DEFAULT_MODEL, build_db_schema

load_dotenv()

st.set_page_config(
    page_title="Chat to DB", layout="wide", page_icon="assets/logo.jpg"
)

st.markdown("""
<style>
    /* 全局样式 */
    .main {
        background-color: #f8f9fa;
    }
    
    /* 隐藏右上角所有元素 */
    .stApp > div:first-child > div > div > div > header {
        display: none !important;
    }
    
    /* 尝试更精确隐藏 */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* 隐藏 deploy 按钮 */
    .stDeployButton {
        display: none !important;
    }
    
    /* 隐藏菜单按钮 */
    button[data-testid="stMenuButton"] {
        display: none !important;
    }
    
    /* 标题样式 */
    h1, h2, h3 {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 600;
    }
    
    /* 侧边栏样式 */
    .css-1d391kg {
        background-color: #ffffff;
    }
    
    /* 连接卡片样式 */
    .connection-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .connection-card.active {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    
    /* 按钮样式优化 */
    .stButton > button {
        border-radius: 8px;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* 主要按钮样式 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* 输入框样式 */
    .stTextInput > div > div > input, 
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
    }
    
    /* Tab 样式优化 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        background-color: #f0f0f0;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #667eea;
        color: white;
    }
    
    /* 成功信息样式 */
    .stSuccess {
        background-color: #d4edda;
        border-radius: 8px;
        border-left: 4px solid #28a745;
    }
    
    /* 错误信息样式 */
    .stError {
        background-color: #f8d7da;
        border-radius: 8px;
        border-left: 4px solid #dc3545;
    }
    
    /* 信息提示样式 */
    .stInfo {
        background-color: #d1ecf1;
        border-radius: 8px;
        border-left: 4px solid #17a2b8;
    }
    
    /* 数据表格样式 */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* 分割线样式 */
    hr {
        margin: 20px 0;
    }
    
    /* 容器卡片样式 */
    .card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    /* 表头样式 */
    .table-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 12px 12px 0 0;
    }
    
    /* 连接状态徽章 */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
    }
    
    .badge-success {
        background-color: #28a745;
        color: white;
    }
    
    .badge-primary {
        background-color: #667eea;
        color: white;
    }
    
    /* 表格展开样式 */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 10px 15px;
    }
    
    .streamlit-expanderHeader:hover {
        background-color: #e9ecef;
    }
    
    /* SQL 代码块样式 */
    .stCodeBlock {
        border-radius: 8px;
    }
    
    /* 隐藏默认的 Streamlit 元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 滚动条样式 */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #667eea;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

if "connections" not in st.session_state:
    st.session_state.connections = {}

if "active_connection" not in st.session_state:
    st.session_state.active_connection = None

if "selected_model" not in st.session_state:
    st.session_state.selected_model = os.getenv("DASHSCOPE_MODEL", DEFAULT_MODEL)

if "show_new_connection" not in st.session_state:
    st.session_state.show_new_connection = False

if "selected_table" not in st.session_state:
    st.session_state.selected_table = None


def build_connection_string(db_type, host, port, username, password, database):
    if db_type == "MySQL":
        return f"mysql://{username}:{password}@{host}:{port}/{database}"
    elif db_type == "PostgreSQL":
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    elif db_type == "SQLite":
        return f"sqlite:///{database}"
    elif db_type == "SQL Server":
        return f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}"
    else:
        return f"mysql://{username}:{password}@{host}:{port}/{database}"


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 10px 0;">
            <h2 style="margin: 0; color: #667eea;">Chat to DB</h2>
            <p style="margin: 5px 0; color: #666; font-size: 12px;">AI驱动的数据库客户端</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        with st.expander("📂 连接管理", expanded=True):
            saved_connections = list(st.session_state.connections.keys())
        
            if saved_connections:
                for conn_name in saved_connections:
                    conn = st.session_state.connections[conn_name]
                    is_active = st.session_state.active_connection == conn_name
                    
                    bg_color = "#11998e" if is_active else "#667eea"
                    icon = "✅" if is_active else "🔌"
                    
                    st.markdown(f"""
                    <div class="card" style="padding: 12px; margin-bottom: 10px; border-left: 4px solid {bg_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 600; color: #333;">{icon} {conn_name}</span>
                            <span class="badge badge-success">{conn.get('type', 'MySQL')}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("连接", key=f"conn_{conn_name}", use_container_width=True):
                            db_config = parse_connection_string(conn["string"])
                            from database import get_database_connection
                            test_conn = get_database_connection(db_config)
                            if test_conn:
                                st.session_state.active_connection = conn_name
                                st.session_state.selected_table = None
                                test_conn.close()
                                st.rerun()
                            else:
                                st.error("连接失败")
                    with col2:
                        if st.button("删除", key=f"del_{conn_name}", use_container_width=True):
                            del st.session_state.connections[conn_name]
                            if st.session_state.active_connection == conn_name:
                                st.session_state.active_connection = None
                                st.session_state.selected_table = None
                            st.rerun()
            
            if st.button("➕ 新建连接", key="toggle_new_conn", use_container_width=True):
                st.session_state.show_new_connection = not st.session_state.show_new_connection
            
            if st.session_state.show_new_connection:
                with st.container():
                    st.markdown("### ✨ 新建连接")
                
                conn_name = st.text_input(
                    "连接名称",
                    placeholder="例如：本地MySQL",
                    key="new_conn_name"
                )
                
                db_type = st.selectbox(
                    "数据库类型",
                    ["MySQL", "PostgreSQL", "SQLite", "SQL Server"],
                    key="new_db_type"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    host = st.text_input(
                        "主机地址",
                        value=os.getenv("DB_HOST", "192.168.10.100"),
                        key="new_host"
                    )
                with col2:
                    port = st.text_input(
                        "端口",
                        value=os.getenv("DB_PORT", "3306"),
                        key="new_port"
                    )
                
                username = st.text_input(
                    "用户名",
                    value=os.getenv("DB_USERNAME", "test"),
                    key="new_username"
                )
                
                password = st.text_input(
                    "密码",
                    type="password",
                    value=os.getenv("DB_PASSWORD", "test123"),
                    key="new_password"
                )
                
                database = st.text_input(
                    "数据库名",
                    value=os.getenv("DB_NAME", "youxiang"),
                    key="new_database"
                )
                
                col_save, col_test = st.columns(2)
                with col_save:
                    if st.button("保存连接", key="save_conn", type="primary", use_container_width=True):
                        if not conn_name:
                            st.warning("请输入连接名称")
                        else:
                            conn_str = build_connection_string(db_type, host, port, username, password, database)
                            st.session_state.connections[conn_name] = {
                                "type": db_type,
                                "string": conn_str,
                                "host": host,
                                "port": port,
                                "username": username,
                                "password": password,
                                "database": database
                            }
                            st.session_state.active_connection = conn_name
                            st.session_state.show_new_connection = False
                            st.session_state.selected_table = None
                            st.success(f"连接 [{conn_name}] 已保存并激活")
                            st.rerun()
                
                with col_test:
                    if st.button("测试连接", key="test_conn", use_container_width=True):
                        conn_str = build_connection_string(db_type, host, port, username, password, database)
                        db_config = parse_connection_string(conn_str)
                        if db_config:
                            from database import get_database_connection
                            test_conn = get_database_connection(db_config)
                            if test_conn:
                                st.success("连接成功")
                                test_conn.close()
                            else:
                                st.error("连接失败")
                        else:
                            st.error("连接字符串格式错误")
        
        if st.session_state.active_connection:
            st.markdown("---")
            with st.expander("📋 数据库表", expanded=True):
                conn = st.session_state.connections[st.session_state.active_connection]
                db_config = parse_connection_string(conn["string"])
                st.session_state.db_config = db_config
                
                tables = get_tables()
                if tables:
                    for table in tables:
                        row_count = get_table_row_count(table)
                        col_btn, col_name = st.columns([1, 4])
                        with col_btn:
                            if st.button("查看", key=f"btn_{table}", help="查看数据", use_container_width=True):
                                st.session_state.selected_table = table
                        with col_name:
                            st.markdown(f"**{table}** <span style='color:#888;'>({row_count} 行)</span>", unsafe_allow_html=True)
        
        st.markdown("---")
        with st.expander("🤖 阿里云百炼AI配置", expanded=False):
            default_key = os.getenv("DASHSCOPE_API_KEY", "")
            dashscope_key = st.text_input(
                "API 密钥",
                type="password",
                value=default_key,
                key="api_key_input",
                placeholder="输入你的 API 密钥"
            )
            
            if dashscope_key:
                os.environ["DASHSCOPE_API_KEY"] = dashscope_key

            default_model = os.getenv("DASHSCOPE_MODEL", DEFAULT_MODEL)
            model_name = st.text_input(
                "模型名称",
                value=st.session_state.selected_model if st.session_state.selected_model else default_model,
                key="model_input"
            )
            
            if model_name:
                st.session_state.selected_model = model_name


def render_table_data(table_name):
    st.markdown(f"""
    <div class="card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 12px;">
        <h3 style="margin: 0;">📊 表数据：{table_name}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        limit = st.number_input("显示行数", min_value=10, max_value=1000, value=100, key=f"limit_{table_name}")
    with col2:
        pass
    
    with st.spinner("加载数据中..."):
        results, error = execute_query(f"SELECT * FROM `{table_name}` LIMIT {limit}")
        
        if error:
            st.error(error)
        else:
            if results:
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.markdown(f"**共 {len(df)} 条记录**")
                
                st.markdown("#### ⚡ 数据操作")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 刷新数据", key=f"refresh_{table_name}", use_container_width=True):
                        st.rerun()
                with col2:
                    if st.button("📋 复制 SQL", key=f"copy_{table_name}", use_container_width=True):
                        sql = f"SELECT * FROM `{table_name}` LIMIT {limit}"
                        st.code(sql, language="sql")
            else:
                st.info("表中无数据")


def render_nlq_tab():
    if not st.session_state.active_connection:
        st.info("👈 请先在左侧选择一个数据库连接")
        return
    
    st.markdown("""
    <div class="card">
        <h3 style="margin: 0; color: #667eea;">💬 自然语言查询</h3>
    </div>
    """, unsafe_allow_html=True)
    
    tables = get_tables()
    if tables:
        st.markdown("**可用表：** " + " | ".join([f"`{t}`" for t in tables]))
    
    question = st.text_area(
        "请描述你的问题：",
        height=100,
        placeholder="例如：查询 users 表中所有年龄大于 20 的用户",
        key="nlq_question"
    )
    
    if st.button("✨ 生成 SQL", type="primary", key="nlq_generate", use_container_width=True):
        if not question.strip():
            st.warning("请输入问题")
            return
        
        if not os.getenv("DASHSCOPE_API_KEY"):
            st.error("请输入 API 密钥")
            return
        
        with st.spinner("🤔 AI 正在生成 SQL..."):
            tables_info = {}
            for table in get_tables():
                tables_info[table] = get_table_schema(table)
            
            db_schema = build_db_schema(tables_info)
            sql = translate_to_sql(question, st.session_state.selected_model, db_schema)
            
            if sql and not sql.startswith("Error"):
                st.session_state.nlq_sql = sql
                st.success("SQL 生成成功！")
            else:
                st.error(f"生成失败：{sql}")
    
    if "nlq_sql" in st.session_state:
        st.markdown("---")
        st.markdown("#### 生成的 SQL")
        
        st.code(st.session_state.nlq_sql, language="sql")
        
        if "nlq_edited_sql" not in st.session_state:
            st.session_state.nlq_edited_sql = st.session_state.nlq_sql
        
        sql_lines = st.session_state.nlq_edited_sql.count('\n') + 1
        editor_height = max(150, min(sql_lines * 25, 500))
        
        edited_sql = st.text_area(
            "（可编辑）",
            value=st.session_state.nlq_edited_sql,
            height=editor_height,
            key="nlq_sql_editor"
        )
        
        if edited_sql != st.session_state.nlq_edited_sql:
            st.session_state.nlq_edited_sql = edited_sql

        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ 执行查询", key="nlq_execute", use_container_width=True):
                with st.spinner("执行中..."):
                    results, error = execute_query(st.session_state.nlq_edited_sql)

                    if error:
                        st.error(error)
                    else:
                        st.session_state.nlq_results = results
                        st.success("查询成功！")
        with col2:
            if st.button("重新生成", key="nlq_regenerate", use_container_width=True):
                current_question = st.session_state.get("nlq_question", "")
                if not current_question.strip():
                    st.warning("请先输入问题")
                    return
                with st.spinner("重新生成中..."):
                    tables_info = {}
                    for table in get_tables():
                        tables_info[table] = get_table_schema(table)
                    
                    db_schema = build_db_schema(tables_info)
                    new_sql = translate_to_sql(current_question, st.session_state.selected_model, db_schema)
                    
                    if new_sql and not new_sql.startswith("Error"):
                        st.session_state.nlq_sql = new_sql
                        st.session_state.nlq_edited_sql = new_sql
                        st.rerun()

    if "nlq_results" in st.session_state and st.session_state.nlq_results is not None:
        st.markdown("---")
        st.markdown("#### 📊 查询结果")

        df = pd.DataFrame(st.session_state.nlq_results)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.info(f"共 {len(df)} 条记录")

        if st.button("解释结果", key="nlq_explain"):
            current_question = st.session_state.get("nlq_question", "")
            with st.spinner("生成解释..."):
                explanation = explain_results(
                    st.session_state.nlq_results, current_question, st.session_state.selected_model
                )
                st.markdown("##### 解释")
                st.write(explanation)


def render_sql_tab():
    if not st.session_state.active_connection:
        st.info("👈 请先在左侧选择一个数据库连接")
        return
    
    st.markdown("""
    <div class="card">
        <h3 style="margin: 0; color: #667eea;">📝 SQL 编辑器</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if "sql_editor_content" not in st.session_state:
        st.session_state.sql_editor_content = ""
    
    if "sql_selected_text" not in st.session_state:
        st.session_state.sql_selected_text = ""
    
    sql_content = st.text_area(
        "SQL 语句：",
        value=st.session_state.sql_editor_content,
        height=250,
        key="sql_editor_v2",
        placeholder="SELECT * FROM table_name\nWHERE condition\n..."
    )
    
    if sql_content != st.session_state.sql_editor_content:
        st.session_state.sql_editor_content = sql_content
    
    selected_sql = st.text_input(
        "选中的SQL（留空则执行全部）",
        value=st.session_state.sql_selected_text,
        key="selected_sql_input",
        placeholder="输入要执行的SQL语句（可选）"
    )
    
    if selected_sql != st.session_state.sql_selected_text:
        st.session_state.sql_selected_text = selected_sql
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ 执行选中", type="primary", key="sql_execute_selected", use_container_width=True):
            if not selected_sql.strip():
                st.warning("请输入要执行的SQL")
                return
            
            with st.spinner("执行中..."):
                results, error = execute_query(selected_sql)
                
                if error:
                    st.error(error)
                else:
                    st.session_state.sql_results = results
                    st.success("执行成功！")

    with col2:
        if st.button("▶️ 执行全部", key="sql_execute_all", use_container_width=True):
            if not sql_content.strip():
                st.warning("请输入SQL")
                return
            
            with st.spinner("执行中..."):
                results, error = execute_query(sql_content)
                
                if error:
                    st.error(error)
                else:
                    st.session_state.sql_results = results
                    st.success("执行成功！")

    if "sql_results" in st.session_state and st.session_state.sql_results is not None:
        st.markdown("---")
        st.markdown("#### 📊 查询结果")

        df = pd.DataFrame(st.session_state.sql_results)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.info(f"共 {len(df)} 条记录")


def render_main_area():
    st.markdown("""
    <div style="text-align: center; padding: 20px 0; margin-bottom: 20px;">
        <h1 style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;">
            Chat to DB
        </h1>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.active_connection:
        st.markdown(f"""
        <div class="card" style="border-left: 4px solid #28a745;">
            <span style="color: #28a745;">✅</span> 已连接：<strong>{st.session_state.active_connection}</strong>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("👈 请在侧边栏创建并选择数据库连接")
    
    if st.session_state.selected_table and st.session_state.active_connection:
        render_table_data(st.session_state.selected_table)
        st.markdown("---")
    
    tab1, tab2 = st.tabs(["💬 自然语言查询", "📝 SQL 编辑器"])
    
    with tab1:
        render_nlq_tab()
    
    with tab2:
        render_sql_tab()


def main():
    render_sidebar()
    render_main_area()


if __name__ == "__main__":
    main()
