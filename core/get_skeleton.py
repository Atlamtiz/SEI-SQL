import re
import sqlglot
from sqlglot import exp

def replace_identifiers_and_literals(expression):
    if isinstance(expression, exp.Identifier):

        parent = expression.parent
        if isinstance(parent, (exp.Table, exp.From)):  
            expression.set("this", "<table>")
        elif isinstance(parent, exp.Column):  
            expression.set("this", "<column>")
    elif isinstance(expression, exp.Literal): 
        expression.set("this", "<value>")
    
    for child in expression.args.values():
        if isinstance(child, list):
            for subchild in child:
                replace_identifiers_and_literals(subchild)
        elif isinstance(child, exp.Expression):
            replace_identifiers_and_literals(child)

def remove_placeholders(query):
    query = re.sub(r"[\"']", " ", query)

    query = query.replace('NULLIF(_, 0)', '_').replace('NULLIF(COUNT(_), 0)', '_').replace('NULLIF(', '').replace(', 0)', '')
    query = query.replace('AS T1', '').replace('AS T2', '').replace('AS T3', '').replace('AS T4', '').replace('AS T5', '').replace('AS T6', '').replace('AS T7', '').replace('AS T8', '').replace('AS T9', '').replace('AS T10', '')
    query = query.replace('AS t1', '').replace('AS t2', '').replace('AS t3', '').replace('AS t4', '').replace('AS t5', '').replace('AS t6', '').replace('AS t7', '').replace('AS t8', '').replace('AS t9', '').replace('AS t10', '')
    query = query.replace('. ','.').replace('<column>.<column>', '<column>')
    query = query.replace(' INNER JOIN ', ' JOIN ')
    query = query.replace('<column>', '_').replace('<table>', '_').replace('<value>', '_')

    query = query.replace('(*)', '(_)')
    query = query.replace('COUNT(_)', '_').replace('AVG(_)', '_').replace('MAX(_)', '_').replace('MIN(_)', '_').replace('SUM(_)', '_').replace('COUNT(DISTINCT _)', '_').replace('COUNT(_ )', '_')
    query = re.sub(r"\s+", " ", query)

    # BIRD 清理
    query = query.replace('CURRENT_TIMESTAMP()', 'CURRENT_TIMESTAMP')
    query = re.sub(r'STRFTIME\([^()]*\)', '_', query)
    query = re.sub(r'COUNT\([^()]*\)', '_', query)
    query = re.sub(r'SUM\([^()]*\)', '_', query)
    query = re.sub(r'CAST\([^()]*\)', '_', query)
    query = query.replace(' )', ')')
    query = re.sub(r'RANK\(\)\s+OVER\s*\(.*?\)\s+AS\s+\w+', '_', query)

    query = re.sub( r'(_\s*[\+\-\*/%\^]\s*)+_', '_', query)
    query = query.replace(' ,', ',')

    query = re.sub(r"\s+", " ", query)

    return query

def get_sql_skeleton(query):

    parsed = sqlglot.parse_one(query, read='mysql')
    

    replace_identifiers_and_literals(parsed)
    

    skeleton_ori = parsed.sql()
    skeleton = remove_placeholders(skeleton_ori)
    
    return skeleton


def get_schema_aligned_skeleton(sql_list):
    skeleton_list = []
    for sql in sql_list:
        try:
            skeleton = get_sql_skeleton(sql)
        except Exception as e:
            print(f"Error processing SQL: {sql}")
            print(f"Exception: {e}")
            skeleton = 'None'
        skeleton_list.append(str(skeleton))
    return skeleton_list