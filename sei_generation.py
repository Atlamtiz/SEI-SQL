import argparse
import transformers
import torch
import json

def load_model():
    """
    Load the language model for generating responses.
    """
    model_id = './SEIGor'

    pipeline = transformers.pipeline(
        "text-generation",
        model=model_id,
        model_kwargs={"torch_dtype": torch.bfloat16},
        device_map="auto",
    )
    return pipeline

def SEIGor(pipeline, prompt):
    """
    Use the provided pipeline to generate a response based on the given prompt.
    """
    messages = [
        {'role': 'system',
         'content': 'You are a helpful assistant.'},
        {'role': 'user',
         'content': prompt}
    ]

    output = pipeline(
        messages,
        max_new_tokens=500,
    )

    return output[0]['generated_text'][-1]['content']

def sei_generation(database, pipeline):
    """
    Main function to generate query intent and SQL skeletons for the given database.
    """
    # Load the prompt list data from JSON
    with open('./dataset/dev_prompt_list.json', 'r') as f:
        all_data_list = json.load(f)

    # Split the data based on the database type
    if database == 'spider':
        data_list = all_data_list[:1034]
    elif database == 'bird':
        data_list = all_data_list[1034:]
    else:
        raise ValueError("Invalid database type. Please use 'spider' or 'bird'.")

    # Prepare prompt lists
    prompt_list_intent = []
    prompt_list_skeleton = []
    for data in data_list:
        prompt_intent = f"""{data['schema_prompt']}
Question: {data['question']}
Please analyze the query intent of this question."""
        prompt_skeleton = f"""{data['schema_prompt']}
Question: {data['question']}
Translate the question into a SQL skeleton."""
        prompt_list_intent.append(prompt_intent)
        prompt_list_skeleton.append(prompt_skeleton)

    # Generate results
    sei_list = []
    for index in range(len(prompt_list_intent)):
        if index <= 3:
            temp = {}
            # Intent generation
            intent = SEIGor(pipeline, prompt_list_intent[index])
            # SQL skeleton generation
            skeleton = SEIGor(pipeline, prompt_list_skeleton[index])
            print(f"============={index}=============")
            print(f"Query intent: {intent}")
            print(f"SQL skeleton: {skeleton}")

            temp['query_intent'] = intent
            temp['sql_skeleton'] = skeleton
            sei_list.append(temp)

    # Save results to JSON file
    save_path = f'./results/sei/{database}_sei.json'
    with open(save_path, 'w') as f:
        json.dump(sei_list, f, indent=4)

    print(f"Results saved to {save_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=str, help="The name of the database to process.")

    args = parser.parse_args()
    try:
        model_pipeline = load_model()
        sei_generation(args.database, model_pipeline)
    except Exception as e:
        print(f"An error occurred: {e}")
