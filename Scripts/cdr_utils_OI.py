# -*- coding: utf-8 -*-
"""
Created on Wed Jul 12 10:00:57 2023

@author: BenYellinOncohost
"""


import warnings 
import pandas as pd
from pandas.tseries.offsets import MonthEnd


def viedoc_to_df(v_df, cols=None, parse_name=True, remove_retro=True,
                 fix_id = True):
    df = v_df[1:]
    df = df.set_index('Subject Id')  
    df.index.name ='SubjectId'
    
    #df = df[df.index.str.split('-').str[-1]=='NSCLC']
    
    if fix_id:
        df.index = df.index.str.replace(' ','', regex = False)    
    if parse_name:
        warnings.simplefilter('ignore', pd.errors.PerformanceWarning)
        df.insert(0,'Indication',df.index.str.split('-').str[-1])
        df.insert(0,'Site',df.index.str[:6])
        warnings.simplefilter('default', pd.errors.PerformanceWarning)
    if  cols is not None:
        if parse_name:
            cols = ['Site','Indication'] + cols
        df = df[cols]   
    if remove_retro:
        df = df[~df.index.str[:8].isin(['IL-006-5','IL-006-9'])]       
    return df
        
def convert_to_date(s, nk_month='01',nk_day = '15') : 
    s = s.str.replace('-NK-', f'-{nk_month}-' ,regex=False)
    if nk_day == 'max':
        s1 = s.str[:-3]
        s1 = pd.to_datetime(s1, format="%Y-%m") + MonthEnd(0)
        nk_ix = s.str.contains('NK').fillna(False)
        s[nk_ix] =s1[nk_ix]
    else:
        s = s.str.replace('-NK', f'-{nk_day}' ,regex=False)
    s = pd.to_datetime(s)
    return s

def fillna(df, col_list, warn = True):
    if (df[col_list].notna().sum(axis=1).max()>1)&warn:
        print('WARNING: fillna rows contain more than one value while trying to merge. Merge cols:')   
        print(', '.join(col_list))
    s = df[col_list[0]]
    for col in col_list:
        s=s.fillna(df[col])
    return s


def read_lists_dict(path, tbl_format='short', key_col='Drug', list_col='Synonyms'): 
    dict_df = pd.read_csv(path)
    if tbl_format == 'short':
        dict_df = dict_df.set_index(key_col)
        dict_df.Synonyms = dict_df[list_col].str.split(',')
        dict_var = dict_df.Synonyms.to_dict()
    elif tbl_format == 'long':
        dict_df[list_col] = dict_df[list_col].astype(str)
        dict_var = dict_df.groupby(key_col)[list_col].apply(list)
    else:
        raise(ValueError,f"Unknow table format '{tbl_format}'")
    return dict_var, dict_df
    

## Write a simple dict to file
# dict_df = pd.DataFrame({'TypeText':dict_var.keys(),'ParseDetsils':dict_var.values()})
# dict_df.to_csv('230716_treatment_history_details_dict.csv')


# ## Write a dict of lists to csv, short format
# drug_dict_df = pd.DataFrame({'Drug':dict_var.keys(),'Synonyms':dict_var.values()})
# drug_dict_df.Synonyms = drug_dict_df.Synonyms.apply(lambda x: ','.join(x))
# drug_dict_df.to_csv('230716_treatment_history_deteails_dict.csv')



## Write a dict of lists to csv, long format
# dict_df = []
# for key, val in dict_var.items():
#     aux_df = pd.DataFrame(val, columns = ['Synonyms'])
#     aux_df.Synonyms = aux_df.Synonyms.str.lower()
#     aux_df['Line'] = key
#     dict_df.append(aux_df)
# dict_df = pd.concat(dict_df).reset_index(drop=True)
# dict_df.to_csv('230715_treatment_history_types_dict2.csv')




