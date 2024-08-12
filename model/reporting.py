#TODO Turn into a function located in postprocess or utils
## This code is bascially what we need to convert th emodel output to the csv and then this csv can b
# read in in IDEA.
unit_correct = True  # unit s must be corrected to run this script
from_excel = False
min_year = 2015
max_year = 2060
from_excel = False
#%% Generating reporter
rep = Reporter.from_scenario(msg, units={"apply": {"var_cost": "","inv_cost": "", "fix_cost": ""}})
report = rep.get('message::default') # in fact, only in = input x ACT, out = output x ACT is needed

if from_excel:
    # Read default report
    report_df = pd.read_csv('MESSAGE_NO_example_default_report.csv')
else:
# Or if trying another country model, execute the next 4:
    report_df = report.timeseries()
    report_df.reset_index(inplace=True)
    report_df.columns = report_df.columns.astype(str)
    report_df.columns = report_df.columns.str.title()
    
report_df = report.timeseries()
report_df.reset_index(inplace=True)
report_df.columns = report_df.columns.astype(str)
report_df.columns = report_df.columns.str.title()
# Plotted years
years = msg.set('year').tolist()
years = [str(x) for x in years if x >= min_year and x <= max_year]

# Create data for Sankey diagrams and plot it using plotly
report_df.fillna(0, inplace = True)

# Convert from GWa to TWh (*8.76)
# c = report_df.select_dtypes(include=[np.number]) * 8.76
# report_df[c.columns] = c

# Drop not necessary years
report_df.columns = report_df.columns.astype(str)
report_df = report_df.drop(report_df.columns.to_series()['2020': str(min_year)],
                           axis=1)

# Identify input and output variables and its flows (provided within the Reporter: in = input x ACT, out = output x ACT)
in_flows = report_df[report_df['Variable'].str.startswith("in|")]
out_flows = report_df[report_df['Variable'].str.startswith("out|")]
all_flows = pd.concat([out_flows , in_flows])
report_df['Model'] = 'MESSAGEix-Canada'
report_df['Scenario'] = 'Reference'
report_df["Variable"] = report_df["Variable"].str.replace('emis', 'Emissions', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|final|', 'Final Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|final|', 'Final Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|primary|', 'Primary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|primary|', 'Primary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|secondary|', 'Secondary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|secondary|', 'Secondary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|renewable|', 'Primary Energy|renewable|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|renewable|', 'Primary Energy|renewable|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('total om cost|', 'Total Costs|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|useful|', 'Useful Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|useful|', 'Useful Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP_NEW|new capacity|', 'Capacity Addition|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP|capacity|', 'Capacity|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP|capacity|', 'Capacity|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('inv cost|', 'Capital Cost|', regex = False)
report_df['Region'] = report_df['Region'].apply(lambda x: x.split('|')[0])
import pyam
import matplotlib.pyplot as plt
import pyam
plotyrs = [2020,2025,2030,2035,2040,2045,2050,2055,2060]
pyam_df = pyam.IamDataFrame(report_df)
variable = pyam_df.variable
pyam_df.aggregate_region(variable, append = True)
pyam_df.rename({'region': {'World': 'Canada'}}, inplace=True)
pdf = pyam_df.copy()
pdf.to_csv('MESSAGE_CANADA_provincial_baseline_v1.csv')
