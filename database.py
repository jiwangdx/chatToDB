import streamlit as st
import pymysql
from urllib.parse import urlparse


def parse_connection_string(connection_string):
    """Parse MySQL connection string and return database config"""
    try:
        parsed = urlparse(connection_string)

        username = parsed.username
        password = parsed.password
        host = parsed.hostname
        port = parsed.port or 3306
        database = parsed.path.lstrip("/")

        return {
            "host": host,
            "user": username,
            "password": password,
            "database": database,
            "port": port,
        }
    except Exception as e:
        st.error(f"解析连接字符串时出错：{str(e)}")
        return None


def get_database_config():
    """Get database configuration from session state or default"""
    if "db_config" in st.session_state:
        return st.session_state.db_config
    return None


def get_database_connection(db_config=None):
    """Create and return a database connection"""
    if db_config is None:
        db_config = get_database_config()
    if not db_config:
        return None
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            port=db_config['port'],
            charset='utf8mb4'
        )
        return connection
    except Exception as e:
        st.error(f"数据库连接失败：{str(e)}")
        return None


def execute_query(sql_query):
    """Execute SQL query and return results"""
    try:
        connection = get_database_connection()
        if not connection:
            return None, "数据库连接失败"

        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql_query)
            results = cursor.fetchall()

        connection.close()
        return results, None

    except Exception as e:
        return None, f"查询执行错误：{str(e)}"


def get_tables():
    """Get all table names from the database"""
    try:
        connection = get_database_connection()
        if not connection:
            return []
        
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
        
        connection.close()
        return tables
    except Exception as e:
        return []


def get_table_schema(table_name):
    """Get table structure (columns)"""
    try:
        connection = get_database_connection()
        if not connection:
            return []
        
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(f"DESC `{table_name}`")
            columns = cursor.fetchall()
        
        connection.close()
        return columns
    except Exception as e:
        return []


def get_table_row_count(table_name):
    """Get row count of a table"""
    try:
        connection = get_database_connection()
        if not connection:
            return 0
        
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            count = cursor.fetchone()[0]
        
        connection.close()
        return count
    except Exception as e:
        return 0
