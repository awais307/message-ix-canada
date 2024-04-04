import pandas as pd
import requests
import os
import math

class CODERS_compare:
    def __init__(self):
        self.root = os.getcwd()
        self.results = {}

    def compare_capacity(self, year):
        c_cap = pd.read_excel(f'{self.root}\\CODERS_data\\historical_capacity_raw_CODERS.xlsx')
        c_cap = c_cap[c_cap['year'] == year].drop(['year'], axis=1)
        c_cap['region-tech'] = c_cap['region'] + '-' + c_cap['technology']
        c_cap = c_cap.set_index(c_cap['region-tech'], drop=True)

        m_cap = pd.read_excel(f'{self.root}\\provincial_sources\\historical_capacity_raw.xlsx', sheet_name='powerplants')
        m_cap = m_cap[m_cap['year'] == year].drop(['year'], axis=1)
        m_cap['region-tech'] = m_cap['region'] + '-' + m_cap['technology']
        m_cap = m_cap.set_index(m_cap['region-tech'], drop=True)

        reg_techs = []
        for reg in c_cap.region.unique():
            for tech in set(list(c_cap.technology.unique()) + list(m_cap.technology.unique())):
                reg_techs.append(f'{reg}-{tech}')

        capacity = pd.DataFrame(index=reg_techs)
        capacity = pd.merge(capacity, c_cap, left_index=True, right_index=True, how='left')
        capacity = pd.merge(capacity, m_cap, right_index=True, left_index=True, suffixes=[None, '_MESSAGE'], how='left')
        capacity = capacity.reset_index()
        capacity[['region', 'technology']] = capacity['index'].str.split('-', expand=True)
        capacity = capacity[['region', 'technology', 'value', 'value_MESSAGE']].fillna(0)
        
        total_cap_dif = {}
        # Calculate total capacity differences in regions
        for reg in capacity.region.unique():
            reg_capacity = capacity[capacity.region == reg]
            reg_capacity = reg_capacity.sum()
            CODERS_cap = reg_capacity.value
            MESSAGE_cap = reg_capacity.value_MESSAGE

            # total capacity difference
            total_cap_dif[reg] = round(abs(CODERS_cap - MESSAGE_cap) / (CODERS_cap + MESSAGE_cap / 2) * 100, 2)
        
        tech_cap = capacity.groupby('technology').sum()
        tech_cap_diff = {}

        for tech in capacity.technology.unique():
            CODERS_cap = tech_cap.value.loc[tech]
            MESSAGE_cap = tech_cap.value_MESSAGE.loc[tech]
            tech_cap_diff[tech] = round(abs(CODERS_cap - MESSAGE_cap) / (CODERS_cap + MESSAGE_cap / 2) * 100, 2)
        
        self.results['Regional Capacity Difference'] = total_cap_dif
        self.results['Technology Capacity Difference'] = tech_cap_diff

        pd.DataFrame().from_dict(self.results).to_csv(f'{self.root}\\CODERS_data\\capacity_compare.csv')
        





if __name__ == '__main__':
    compare = CODERS_compare()
    compare.compare_capacity()