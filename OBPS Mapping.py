import pandas as pd

# Define file paths and sheet names
data_file = "MESSAGE_OBPS_update_(conservative_scenario).csv"
mapping_file = "obps_inputs_clean.xlsx"
data_sheet = "formatted_inputs"
mapping_sheet = "Mapping"
output_file = "data\\New_OBPS.csv"

# Read the main data file
try:
    read_file = pd.read_csv(data_file)
    print(f"Successfully read data from '{data_file}'.")
except FileNotFoundError:
    print(f"Error: The file '{data_file}' was not found.")
    exit()
except KeyError:
    print(f"Error: The sheet '{data_sheet}' was not found in '{data_file}'.")
    exit()
except Exception as e:
    print(f"An error occurred while reading the data file: {e}")
    exit()

# Read the mapping file
try:
    mapping = pd.read_excel(mapping_file, sheet_name=mapping_sheet)
    print(f"Successfully read mapping from '{mapping_file}' sheet '{mapping_sheet}'.")
except FileNotFoundError:
    print(f"Error: The file '{mapping_file}' was not found.")
    exit()
except KeyError:
    print(f"Error: The sheet '{mapping_sheet}' was not found in '{mapping_file}'.")
    exit()
except Exception as e:
    print(f"An error occurred while reading the mapping file: {e}")
    exit()

# Create a mapping dictionary from the 'mapping' dataframe
mapping_dict = mapping.groupby('variable')['technology'].apply(list).to_dict()


def find_technologies(variable, mapping_dict):
    """
    Finds all technologies based on partial matching of the variable.

    Args:
        variable (str): The variable to search for.
        mapping_dict (dict): The dictionary containing the mapping.

    Returns:
        list: A list of technologies if found, otherwise an empty list.
    """
    technologies = []
    for key, values in mapping_dict.items():
        if key in variable:
            technologies.extend(values)  # Extend to add all technologies
    return technologies


# Apply the mapping to create the 'technology' column
read_file['technologies'] = read_file['variable'].apply(
    lambda x: find_technologies(x, mapping_dict))

# Explode the 'technologies' column to create multiple rows
read_file = read_file.explode('technologies')

# Rename 'technologies' column to 'technology'
read_file.rename(columns={'technologies': 'technology'}, inplace=True)

# Filter out rows where technology wasn't found
read_file = read_file[read_file['technology'].notna()]

# Save the updated dataframe to a new CSV file
try:
    read_file.to_csv(output_file, index=False, header=True)
    print(f"Successfully saved the updated data to '{output_file}'.")
except Exception as e:
    print(f"An error occurred while saving the file: {e}")

