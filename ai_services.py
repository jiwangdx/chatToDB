import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

DEFAULT_MODEL = "qwen3.5-flash"

DEFAULT_DB_SCHEMA = """
Database: MySQL 数据库
Tables: 根据实际连接的数据库自动识别

重要提示：
- 使用 SHOW TABLES 可以查看所有表
- 使用 DESC table_name 可以查看表结构
- 使用 SELECT * FROM table_name LIMIT 10 查询数据
"""


def get_llm(model_name: str = None):
    if not model_name:
        model_name = os.getenv("DASHSCOPE_MODEL", DEFAULT_MODEL)
    
    return ChatOpenAI(
        model=model_name,
        temperature=0.1,
        top_p=0.95,
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


def clean_response(response):
    response = response.strip()
    response = re.sub(r'<[^>]+>', '', response)
    return response


def build_db_schema(tables_info):
    """Build database schema description from tables info"""
    schema = "数据库表结构：\n\n"
    
    for table_name, columns in tables_info.items():
        schema += f"表名：{table_name}\n"
        schema += "字段：\n"
        for col in columns:
            col_name = col.get('Field', '')
            col_type = col.get('Type', '')
            col_key = col.get('Key', '')
            col_extra = col.get('Extra', '')
            nullable = col.get('Null', '')
            
            schema += f"  - {col_name} ({col_type})"
            if col_key == 'PRI':
                schema += " PRIMARY KEY"
            if col_key == 'MUL':
                schema += " INDEX"
            if col_extra == 'auto_increment':
                schema += " AUTO_INCREMENT"
            if nullable == 'NO':
                schema += " NOT NULL"
            schema += "\n"
        schema += "\n"
    
    return schema


def translate_to_sql(natural_question, model_name: str = None, db_schema: str = None):
    try:
        llm = get_llm(model_name)
        
        if db_schema is None:
            db_schema = DEFAULT_DB_SCHEMA

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一个 MySQL SQL 专家。将自然语言问题转换为 MySQL 查询。

数据库结构：
{db_schema}

规则：
1. 根据实际表结构生成 SQL，使用正确的表名和字段名
2. 对于 SELECT 查询：必要时使用适当的 JOIN，使用有意义的列别名，大结果集包含 LIMIT
3. 使用正确的 MySQL 语法
4. 只返回 SQL 查询，不要解释，不要 "SQL:" 前缀
5. 不要在响应中包含任何思考、推理过程

常用查询示例：
- "显示所有表" -> SHOW TABLES;
- "查看表结构" -> DESC table_name;
- "查询前10条数据" -> SELECT * FROM table_name LIMIT 10;
- "统计记录数" -> SELECT COUNT(*) FROM table_name;

重要提示：只返回 SQL 查询，不要有任何前缀或解释。
""",
                ),
                ("human", "问题：{question}\n\n生成 SQL 查询："),
            ]
        )

        chain = prompt | llm | StrOutputParser()

        sql_query = chain.invoke(
            {
                "db_schema": db_schema,
                "question": natural_question,
            }
        )

        sql_query = clean_response(sql_query)

        if sql_query.upper().startswith("SQL:"):
            sql_query = sql_query[4:].strip()

        return sql_query

    except Exception as e:
        return f"转换为 SQL 时出错：{str(e)}"


def explain_results(results, original_question, model_name: str = None):
    try:
        llm = get_llm(model_name)

        if results:
            results_text = json.dumps(results, indent=2, default=str)
        else:
            results_text = "没有找到结果"

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一个友好的数据库助手。用中文解释查询结果。

规则：
1. 对话式且清晰
2. 总结关键发现
3. 如果有很多结果，提供包含关键统计信息的摘要
4. 突出任何有趣的模式或洞察
5. 保持解释简洁但信息丰富
""",
                ),
                (
                    "human",
                    """原始问题：{question}

查询结果：
{results}

请用中文解释这些结果：""",
                ),
            ]
        )

        chain = prompt | llm | StrOutputParser()

        explanation = chain.invoke(
            {"question": original_question, "results": results_text}
        )

        explanation = clean_response(explanation)

        return explanation

    except Exception as e:
        return f"生成解释时出错：{str(e)}"
