

def add_historical_activity(scenario):

    """ doc string so it automatically moves to readthe docs"""
    ## you are opening a scenario 
    msg.check_out()

    # we fetch historical_Activity parameter froms cenario 

    df = msg.par('historical_activity')

    ##

    df_new df[df['technology'] == 'oil_extr_mpen' & df['node'] ==' BrisithColumbia'] = 0.5

    #
    # Now becaus we have changed a historical value we need to make sure the historical energy balance is correctly updated
    # for this we call Rideley's function which balances import, export values of oil in this case but also overall dataframe 
    df_new = balance_import_export(df)


    msg.remove_par('historical_activity',df)


    msg.add_par('historical_activity',df_new)

    msg.commit('added historical activity')





