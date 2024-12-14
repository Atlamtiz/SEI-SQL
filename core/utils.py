from openai import OpenAI
import json
import re
import sqlite3

def LLMs(prompt, url, key, model):
    client = OpenAI(
    base_url = url,
    api_key = key)

    completion = client.chat.completions.create(
        model= model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return completion.choices[0].message.content

def extract_sql_samples(text):
    lines = text.split('\n')

    samples_dict = {}
    sample_pattern = r'^-+(\d+)\s+sample_num$'
    sample_num = None 
    sample_content = []  

    for line in lines:
        line = line.strip()
        match = re.match(sample_pattern, line)
        if match:
            if sample_num is not None:
                if sample_num not in samples_dict:
                    samples_dict[sample_num] = '\n'.join(sample_content)
                else:
                    print(f"Duplicate sample {sample_num} found. Ignoring subsequent occurrence.")
                sample_content = []

            sample_num = int(match.group(1))
        else:
            if sample_num is not None:
                sample_content.append(line)

    if sample_num is not None and sample_content:
        if sample_num not in samples_dict:
            samples_dict[sample_num] = '\n'.join(sample_content)
        else:
            print(f"Duplicate sample {sample_num} found. Ignoring subsequent occurrence.")

    sample_nums_present = sorted(samples_dict.keys())
    if sample_nums_present:
        min_sample_num = min(sample_nums_present)
        max_sample_num = max(sample_nums_present)
    else:
        min_sample_num = 0
        max_sample_num = 0

    all_sample_nums = list(range(min_sample_num, max_sample_num + 1))

    missing_samples = set(all_sample_nums) - set(sample_nums_present)
    for missing_num in sorted(missing_samples):
        print(f"Sample {missing_num} is missing. Using 'SELECT' as the placeholder SQL.")
        samples_dict[missing_num] = ''

    sql_list = []
    for num in sorted(all_sample_nums):
        content = samples_dict.get(num, '')
        sql_match = re.search(r'```sql\s+([\s\S]*?)\s+```', content, re.IGNORECASE)
        if sql_match:
            sql_statement = sql_match.group(1).strip()
            sql_list.append(sql_statement.replace('\n', ' '))
        else:
            if content.strip() == '':
                sql_list.append('SELECT')
            else:
                print(f"Cannot extract SQL from sample {num}. Using 'SELECT' as placeholder.")
                sql_list.append('SELECT')

    return sql_list


def spider_extract_sql_samples(gen_ori_path, clean_save_path):
    with open(gen_ori_path, 'r')as f:
        sql_gen_ori = f.read()

    sql_list = extract_sql_samples(sql_gen_ori)

    with open(clean_save_path, 'w') as f:
        for sql in sql_list:
            f.write(sql + '\n')

def bird_extract_sql_samples(gen_ori_path, clean_save_path, bench_path):
    with open(gen_ori_path, 'r')as f:
        sql_gen_ori = f.read()

    with open(bench_path, 'r')as f:
        sql_dev = json.load(f)

    sql_list = extract_sql_samples(sql_gen_ori)

    length = len(sql_list)
    for i in range(length):
        bench = 'bird'
        db_id = sql_dev[i]['db_id']
        sql_list[i] = sql_list[i] + f'\t----- {bench} -----\t{db_id}'
    
    sql_dict = {index: query for index, query in enumerate(sql_list)}

    with open(clean_save_path, 'w')as f:
        json.dump(sql_dict, f, indent=4)


def schema_prompt_with_examples(db_path, example_limit=1, max_cell_length=20):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        output_list = []
        
        for table in tables:
            table_name = table[0]

            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            create_table_sql = cursor.fetchone()[0]

            cursor.execute(f"SELECT * FROM '{table_name}' LIMIT {example_limit};")
            example_rows = cursor.fetchall()
            column_names = [description[0] for description in cursor.description]

            if example_limit != 0:
                output = f'{create_table_sql};\n'
                output += f'/* {example_limit} example rows: SELECT * FROM {table_name} LIMIT {example_limit};\n'
                output += ' | '.join(column_names) + '\n'
                
                for row in example_rows:
                    max_cell_length = max_cell_length
                    truncated_row = [str(cell)[:max_cell_length] + ('...' if len(str(cell)) > max_cell_length else '') for cell in row]
                    output += ' | '.join(truncated_row) + '\n'

                output += '*/\n'
                output_list.append(output)
            else:
                output = f'{create_table_sql};'
                output_list.append(output)

        final_output = '\n'.join(output_list)
        return final_output

    finally:
        conn.close()