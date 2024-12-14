from core.utils import LLMs, spider_extract_sql_samples, bird_extract_sql_samples, schema_prompt_with_examples
import json
import argparse

# prompt construction
def prompt_construction(data_list_path, sei_path, database):

    with open(data_list_path, 'r')as f:
        data_list = json.load(f)

    with open(sei_path, 'r')as f:
        sei_list = json.load(f) 

    prompt_list = []
    for index, data in enumerate(data_list):
        db_id = data['db_id']
        if database == 'spider':
            db_path = f'./dataset/spider/database/{db_id}/{db_id}.sqlite'
        elif database == 'bird':
            db_path = f'./dataset/bird/dev/dev_databases/dev_databases/{db_id}/{db_id}.sqlite'
        schema_prompt = schema_prompt_with_examples(db_path, 3, 20)
        
        if data['evidence']:
            prompt_sei = f"""{schema_prompt}
    Question: "{data['question']}"
    External Knowledge: "{data['evidence']}"
    Query Intent: {sei_list[index]['query_intent']}
    SQL Skeleton: {sei_list[index]['sql_skeleton']}

    Using the provided External knowledge, Query Intent and SQL Skeleton to write a valid SQLite query to answer the questions based on the tables provided above.

    Please output the SQL in the following format, no need explanation:
    ```sql
    ...
    ```"""
        else:
            prompt_sei = f"""{schema_prompt}
    Question: "{data['question']}"
    Query Intent: {sei_list[index]['query_intent']}
    SQL Skeleton: {sei_list[index]['sql_skeleton']}

    Using the provided Query Intent and SQL Skeleton to write a valid SQLite query to answer the questions based on the tables provided above.

    Please output the SQL in the following format, no need explanation:
    ```sql
    ...
    ```"""
        prompt_list.append(prompt_sei)
    print(len(prompt_list))

    return prompt_list

# sql_generation
def sql_generation(prompt_list, url, key, model_name):
    sql_ori_save_path = './results/sql/sql_ori.txt'
    with open(sql_ori_save_path, 'w')as f:
        for index, prompt in enumerate(prompt_list):
            if index >= 0:
                output = LLMs(prompt, url, key, model_name)
                f.write(f'-------------------------{str(index)} sample_num\n')
                f.write(output + '\n')
                print(output)

# data_clean
def data_clean(database):
    sql_ori_path = './results/sql/sql_ori.txt'

    if database == 'spider':
        spider_extract_sql_samples(sql_ori_path, './results/sql/sql_pre.txt')
    elif database == 'bird':
        bird_extract_sql_samples(sql_ori_path, './results/sql/sql_pre.json', './dataset/bird/dev/dev.json')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_list_path', type=str, required=True, help='Path to the data list JSON file.')
    parser.add_argument('--sei_path', type=str, required=True, help='Path to the SEI JSON file.')
    parser.add_argument('--url', type=str, required=True, help='URL of the LLM service.')
    parser.add_argument('--key', type=str, required=True, help='API key for the LLM service.')
    parser.add_argument('--model_name', type=str, required=True, help='Name of the model to use.')
    parser.add_argument('--database', type=str, choices=['spider', 'bird'], required=True, help='Database type for data cleaning.')

    args = parser.parse_args()

    # Step 1: Construct prompts
    prompt_list = prompt_construction(args.data_list_path, args.sei_path, args.database)

    # Step 2: Generate SQL queries
    sql_generation(prompt_list, args.url, args.key, args.model_name)

    # Step 3: Clean the generated SQL data
    data_clean(args.database)