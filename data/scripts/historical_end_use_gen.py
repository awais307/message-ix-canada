import pandas as pd

# Conversion factor from Petajoules to Gigawatt-years
PJ_TO_GWA = 277.778 / 8760

# Define the mapping of technologies to data source
TECHNOLOGIES = {
    "coal_fs": ("Industrial", "Coal, Coke & Coke Oven Gas"),
    "foil_fs": ("Industrial", "Still Gas & Petroleum Coke"),
    "foil_trp": ("Transportation", "Heavy Fuel Oil"),
    "loil_fs": ("Industrial", "LPG & Petroleum Feedstocks"),
    "loil_i": ("Industrial", "RPP"),
    "loil_rc": ("Residential and Commercial", "RPP"),
    "loil_trp": ("Transportation", ("Motor Gasoline", "Diesel", "Aviation Fuel")),
    "gas_fs": ("Industrial", "Natural_Gas"),
    "gas_rc": ("Residential and Commercial", "Natural_Gas"),
    "gas_trp": ("Transportation", "Natural_Gas")
}
SECTORS = ["Industrial", "Residential and Commercial","Transportation"]
PROVINCES = ["Alberta", "British Columbia", "Manitoba", "Ontario", "New Brunswick",
             "Newfoundland and Labrador", "Nova Scotia", "Prince Edward Island", "Quebec", "Saskatchewan", "Yukon"]

YEARS = [2015, 2020]

results = []

for province in PROVINCES:
    print(province)
    data = {}

    # Load all sectors into a dictionary for each province
    for sector in SECTORS:
        data[sector] = pd.read_excel(f"../End_Uses/end_use_demand_{province.replace(' ', '')}.xlsx", sheet_name=sector)

    # Extract and process data for each technology and year
    for technology, (sector, rows) in TECHNOLOGIES.items():
        if isinstance(rows, tuple):  # Handle cases with multiple rows
            rows = list(rows)
        elif isinstance(rows, str):
            rows = [rows]  # Make single row a list for uniform processing

        for year in YEARS:
            # We use 'isin' function to filter the DataFrame for the rows we need
            total_value_pj = sum(data[sector][data[sector]['_'].isin(rows)][str(year)])
            total_value_gwa = total_value_pj * PJ_TO_GWA
            results.append({
                "province": province,
                "technology": technology,
                "year": year,
                "value": total_value_gwa,
                "unit": "GWa"
            })

# Convert results to DataFrame and save as CSV
df = pd.DataFrame(results)
df.to_csv("energy_usage_by_technology.csv", index=False)
