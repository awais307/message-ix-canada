import yaml
import random


def read_yaml(file_path):
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
    return data


def write_yaml(file_path, data):
    with open(file_path, "w") as file:
        yaml.dump(data, file, default_flow_style=False)


def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def process_yaml(data):
    new_data = {}
    for category, items in data.items():
        group_color = random_color()
        for item in items:
            item_name = item
            new_data[item_name] = {
                "color": random_color(),
                "group": category,
                "group_color": group_color,
                "name": item_name,
            }
    return new_data


def main():
    input_file = "output_mapping.yaml"  # Replace with your input YAML file path
    output_file = "output_mapping_idea.yaml"  # Output file path
    data = read_yaml(input_file)
    processed_data = process_yaml(data)
    write_yaml(output_file, processed_data)


if __name__ == "__main__":
    main()
