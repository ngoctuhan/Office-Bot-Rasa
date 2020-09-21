import json

file_out = open("action.csv", "w")
ff = open("temp.txt","w")
with open("../../../config/config_template_action.json", "r") as temp_file:
    json_parse = json.load(temp_file)
    for action_name in json_parse:
        action = json_parse[action_name]
        text = action[0]["text"]
        if isinstance(text, dict):
            text = text["OTHER"]
        ff.write(f"{text}\n")
        text_tts = action[0]["text_tts"]
        # file_out.write(f"- {action_name}\t{text}\t{text_tts}\n")
