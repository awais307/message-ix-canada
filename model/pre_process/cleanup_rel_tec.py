import pandas as pd
import ixmp as ix
import message_ix

def cleanup_rel_tec(msgSC, nodes='all', glb=None, remove_accounting=False, relation_remove=[]):
    """ This function will remove any unused relations and technologies.
    Relations will be removed if:
        1. They have no upper and lower bound and no costs - therefore
           non-binding and have been used for accounting purposes
        2. They have no entries from any technologies
        2./3. NOTE: Only applied if this is the case in all regions.
        3. Specifically defined to be excluded.
            - some are manually removed because technologies using these
              are deleted in the next step.
            - all relations for historic calibration are removed
    Technologies will be removed if:
        1. They have a bound on activity of 0 for the entire
           optimization period
        2. Specifically defined to be excluded.
    """
    if nodes == 'all':
        reg = [x for x in msgSC.set('node') if x not in ['World', glb]]
    else:
        reg = nodes

    # Ensure DataFrame operations use 'reg' correctly
    exclusion = []
    relations = msgSC.set('relation').tolist()

    if remove_accounting:
        rel_par = pd.DataFrame()
        for par in ['relation_upper', 'relation_lower', 'relation_cost']:
            # Ensure that DataFrame filtering here is correct
            df = msgSC.par(par)
            df = df[df['node_rel'].isin(reg)][['node_rel', 'relation']]
            rel_par = pd.concat([rel_par, df], ignore_index=True)

        rel_par = rel_par.drop_duplicates()

        rel_act = pd.DataFrame()
        for par in ['relation_new_capacity', 'relation_total_capacity', 'relation_activity']:
            df = msgSC.par(par)
            df = df[df['node_rel'].isin(reg)][['node_rel', 'relation']]
            rel_act = pd.concat([rel_act, df], ignore_index=True)

        rel_act = rel_act.drop_duplicates()

        exclusion = pd.concat([rel_act, rel_par]).drop_duplicates(keep=False)['relation'].tolist()
        exclusion += [r for r in relations if r not in rel_act['relation'].tolist() and r not in rel_par['relation'].tolist()]

    # Add manual exclusions and process them
    exclusion += ['PE_domestic_total', 'PE_import_total', 'PE_import_share', 'PE_export_total',
                  'demb_limit', 'demF_limit', 'demI_limit', 'demp_limit', 'demR_limit', 'demt_limit',
                  'elec_coal', 'elec_gas', 'elec_hydro', 'elec_nuclear', 'ele_nuc', 'foil_prod',
                  'oil_based_elec_gen', 'gas_export', 'SO2_red_ref', 'SO2_red_synf', 'SO2_ind',
                  'SO2_elec', 'SO2_import', 'SO2_r_c'] + [x for x in relation_remove if x in msgSC.set("relation")]

    msgSC.check_out()
    for rel in set(exclusion):
        if rel in msgSC.set('relation'):
            msgSC.remove_set('relation', rel)
            print('Relation: {} - deleted'.format(rel))

    msgSC.commit('Remove unused elements')

# Example Usage
if __name__ == '__main__':
    mp = ix.Platform()
    model = 'MESSAGEix_KR'
