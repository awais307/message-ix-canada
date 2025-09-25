import pandas as pd
from pathlib import Path
from typing import Union

def add_hydrogen_shares(model_obj, path: Union[str, Path]):
		"""
		Add hydrogen shares to a MESSAGEix scenario.

		This function modifies the provided MESSAGEix scenario to include hydrogen shares.
		The specific implementation details, such as the hydrogen share percentages and the affected sectors,
		should be added within this function.

		Args:
						path (str or Path): Path to the Excel file containing hydrogen share data.

		Returns:
						None

		Logic: adds hydrogen shares to the MESSAGEix scenario
		"""
		# Checkout the scenario for editing
		model_obj.ctx.source_scenario['scenario'].check_out()

		# Resolve the path to the hydrogen shares Excel file
		path = Path(path)
		# if not path.endswith(".xlsx"):
		# 	raise Exception("File provided for hydrogen shares is not in Excel format.")
		# else:
		data = pd.ExcelFile(path / "hydrogen_shares.xlsx")

		# Loop through each sheet in the Excel file
		for sheet_name in data.sheet_names:
			# Read the current sheet into a DataFrame
			df = pd.read_excel(path / "hydrogen_shares.xlsx", sheet_name=sheet_name)
			print(f"Sheet name: {sheet_name}")

			# Check if the sheet name corresponds to a set in the scenario
			if sheet_name in model_obj.ctx.source_scenario['scenario'].set_list():
				# Skip 'cat_tec' as it should not be modified
				if sheet_name == "cat_tec":
					continue
				print("sets", sheet_name)

				# Add data to the set; handle 'type_tec' and 'shares' specifically
				if sheet_name in ["type_tec", "shares"]:
					model_obj.ctx.source_scenario['scenario'].add_set(sheet_name, df[sheet_name])
				else:
					model_obj.ctx.source_scenario['scenario'].add_set(sheet_name, df)

			# Check if the sheet name corresponds to a parameter in the scenario
			elif sheet_name in model_obj.ctx.source_scenario['scenario'].par_list():
				model_obj.ctx.source_scenario['scenario'].add_par(sheet_name, df)
				print("par", sheet_name)

		# Commit the changes to the scenario with a descriptive message
		model_obj.ctx.source_scenario['scenario'].commit("Updated scenario to include hydrogen shares")

		# Print the unique values of the 'shares' column in the 'share_commodity_lo' parameter
		print(model_obj.ctx.source_scenario['scenario'].par("share_commodity_lo")["shares"].unique())

		# Optional: Uncomment the line below to print the unique 'shares' values again
		# print(scenario.par("share_commodity_lo")['shares'].unique())