# -*- coding: utf-8 -*-
"""
Created on Thu Aug 24 18:26:04 2023

@author: BenYellin
"""

import pandas as pd
import cdr_utils_OI as ut


### TBD: extract from parse_blood
def parse_first_treatment(df_dict, blood_sheet='BLOOD'):
    '''


    Parameters
    ----------
    df_dict : TYPE
        DESCRIPTION.
    blood_sheet : TYPE, optional
        DESCRIPTION. The default is 'BLOOD'.

    Returns
    -------
    None.

    '''
    print('TBD')


def parse_blood(df_dict, blood_sheet='BLOOD', second_treatment_range=(20, 60)):
    '''
    TBD: 
    1. Add Assay data (available mesurments)
    2. Add lab data (available blood for measurments)
    3. Check treatment hour vs blood collection hour
    
    Parse blood collection data
    Parse first and second treatments

    Parameters
    ----------
    df_dict : TYPE
        DESCRIPTION.
    blood_sheet : TYPE, optional
        DESCRIPTION. The default is 'BLOOD'.
    eos_sheet : TYPE, optional
        DESCRIPTION. The default is 'EOS'.

    Returns
    -------
    blood_df: pd.DataFrame
        include additinal stat about blood collection time
    
    treatment_df: pd.DataFrame
        data about treatments
    
    blood_summary: pd.Dataframe
        remarks about curation
        

    '''

    visit_dict = {'PRE': 'T0', 'POST': 'T1'}
    trt_dict = {'PRE': 'First', 'POST': 'Second'}

    ###### Prepeocessing for blood df
    blood_df = ut.viedoc_to_df(df_dict[blood_sheet], remove_retro=False)
    blood_df = blood_df.rename(columns={'Event Id': 'Visit',
                                        'Event date': 'EventDate',
                                        'Treatment Date:': 'TreatmentDate',
                                        'Treatment Time:': 'TreatmentTime',
                                        'Blood Collection Date:': 'BloodCollectionDate',
                                        'Blood Collection Time:': 'BloodCollectionTime',
                                        'End Timefor Plasma Preparation Procedure:': 'EndPrepTime',
                                        'Provide reason for Plasma Preparationexceeding 4 hours:': 'BloodCollectionTimeNotes'})
    blood_df['AutoParsingNotes'] = ''

    blood_df.EventDate = ut.convert_to_date(blood_df.EventDate)
    blood_df.BloodCollectionDate = ut.convert_to_date(blood_df.BloodCollectionDate)
    blood_df.TreatmentDate = ut.convert_to_date(blood_df.TreatmentDate)

    blood_df_for_treatment = blood_df.copy(deep=True)

    blood_df.loc[blood_df['Not Done'] == 'Not Done', 'BloodCollectionDate'] = 'Not Done'
    blood_df = blood_df[blood_df.BloodCollectionDate.notna()]
    blood_df_for_treatment = blood_df_for_treatment[blood_df_for_treatment.BloodCollectionDate.notna()]

    blood_df['TimeOnBench'] = ((pd.to_datetime(blood_df.EndPrepTime) - pd.to_datetime(
        blood_df.BloodCollectionTime)).dt.total_seconds() / 60)
    blood_df['TimeOnBench'] = blood_df['TimeOnBench'].fillna(0).astype(int).replace(0, None)
    blood_df_for_treatment['TimeOnBench'] = ((pd.to_datetime(blood_df_for_treatment.EndPrepTime) - pd.to_datetime(
        blood_df_for_treatment.BloodCollectionTime)).dt.total_seconds() / 60)
    blood_df_for_treatment['TimeOnBench'] = blood_df_for_treatment['TimeOnBench'].fillna(0).astype(int).replace(0, None)

    ###### Create treatment_df
    ## parse first and second treatment  
    blood_df = blood_df.reset_index()
    blood_df_for_treatment = blood_df_for_treatment.reset_index()

    remarks_df = {}
    treatment_df = {}
    for sub_id, sub_df in blood_df_for_treatment.groupby('SubjectId'):
        sub_df = sub_df.sort_values('BloodCollectionDate')

        if sub_id.split('-')[-1] != 'HEALTHY':
            remarks_df[sub_id] = ''
            ## Only one sample
            if len(sub_df) == 1:
                # if sub_df['BloodCollectionDate'].notna().sum() == 0:
                #     remarks_df[sub_id] += 'Treatment date missing, '
                if sub_df['Visit'].iloc[0] == 'PRE':
                    treatment_df[sub_id] = {
                        'T0BloodCollectionDate': sub_df['BloodCollectionDate'].iloc[0],
                        'T0TimeOnBench': sub_df['TimeOnBench'].iloc[0],
                        'FirstImmunoTreatmentDate': sub_df['TreatmentDate'].iloc[0],
                        'FirstImmunoTreatmentTime': sub_df['TreatmentTime'].iloc[0],
                        'NumberOfBloodSamples': 1}
                    # print(treatment_df[sub_id])
                else:
                    remarks_df[sub_id] += 'No T0 sample'

            ## Two samples
            elif len(sub_df) == 2:
                for visit in ['PRE', 'POST']:
                    if visit in list(sub_df.Visit):
                        treatment_df[sub_id] = {
                            f'{visit_dict[visit]}BloodCollectionDate':
                                sub_df.loc[sub_df.Visit == visit, 'BloodCollectionDate'].iloc[0],
                            f'{visit_dict[visit]}TimeOnBench': sub_df.loc[sub_df.Visit == visit, 'TimeOnBench'].iloc[0],
                            f'{trt_dict[visit]}ImmunoTreatmentDate':
                                sub_df.loc[sub_df.Visit == visit, 'TreatmentDate'].iloc[0],
                            f'{trt_dict[visit]}ImmunoTreatmentTime':
                                sub_df.loc[sub_df.Visit == visit, 'TreatmentTime'].iloc[0],
                            'NumberOfBloodSamples': 2}
                    else:
                        remarks_df[sub_id] += 'Two blood samples'
                        if ((visit == 'POST') & (sub_id in treatment_df.keys())):
                            remarks_df[sub_id] += ' no T1, '
                        else:
                            remarks_df[sub_id] += f'{visit} Missing, '

            ## More then two samples
            else:
                ## Regular patients with T0, T1
                if list(sub_df.Visit[:2]) == ['PRE', 'POST']:
                    treatment_df[sub_id] = {
                        'T0BloodCollectionDate': sub_df['BloodCollectionDate'].iloc[0],
                        'T0TimeOnBench': sub_df['TimeOnBench'].iloc[0],
                        'FirstImmunoTreatmentDate': sub_df['TreatmentDate'].iloc[0],
                        'FirstImmunoTreatmentTime': sub_df['TreatmentTime'].iloc[0],
                        'T1BloodCollectionDate': sub_df['BloodCollectionDate'].iloc[1],
                        'T1TimeOnBench': sub_df['TimeOnBench'].iloc[1],
                        'SecondImmunoTreatmentDate': sub_df['TreatmentDate'].iloc[1],
                        'NumberOfBloodSamples': len(sub_df)}
                ## T0a patients
                elif list(sub_df.Visit[:3]) == ['PRE', 'UNS', 'POST']:
                    treatment_df[sub_id] = {
                        'T0BloodCollectionDate': sub_df['BloodCollectionDate'].iloc[1],
                        'T0TimeOnBench': sub_df['TimeOnBench'].iloc[1],
                        'FirstImmunoTreatmentDate': sub_df['TreatmentDate'].iloc[1],
                        'FirstImmunoTreatmentTime': sub_df['TreatmentTime'].iloc[0],
                        'T1BloodCollectionDate': sub_df['BloodCollectionDate'].iloc[2],
                        'T1TimeOnBench': sub_df['TimeOnBench'].iloc[2],
                        'SecondImmunoTreatmentDate': sub_df['TreatmentDate'].iloc[2],
                        'NumberOfBloodSamples': len(sub_df)}
                    remarks_df[sub_id] += 'T0a Sample?'
                ## patients with only T0
                elif 'PRE' in list(sub_df.Visit):
                    pre_df = sub_df[sub_df.Visit == 'PRE']
                    treatment_df[sub_id] = {
                        'T0BloodCollectionDate': pre_df['BloodCollectionDate'].iloc[0],
                        'T0TimeOnBench': pre_df['TimeOnBench'].iloc[0],
                        'FirstImmunoTreatmentDate': pre_df['TreatmentDate'].iloc[0],
                        'FirstImmunoTreatmentTime': sub_df['TreatmentTime'].iloc[0],
                        'NumberOfBloodSamples': len(sub_df)}

                else:
                    treatment_df[sub_id] = {
                        'NumberOfSamples': len(sub_df)}
                    remarks_df[sub_id] += 'More than two blood samples, dont know how to register'

    ## create dataframe
    remarks_df = pd.Series(remarks_df)
    remarks_df.name = 'AutoParsingNotes'
    remarks_df = remarks_df.str.strip(', ')
    treatment_df = pd.DataFrame(treatment_df).T
    treatment_df = pd.concat([treatment_df, remarks_df], axis=1)
    treatment_df.index.name = 'SubjectId'

    ## add columns
    treatment_df['T0BloodCollectionDuration'] = (
                treatment_df.T0BloodCollectionDate - treatment_df.FirstImmunoTreatmentDate).dt.days
    treatment_df['SecondImmunoTreatmetDuration'] = (
                treatment_df.SecondImmunoTreatmentDate - treatment_df.FirstImmunoTreatmentDate).dt.days
    treatment_df['T1BloodCollectionDuration'] = (
                treatment_df.T1BloodCollectionDate - treatment_df.FirstImmunoTreatmentDate).dt.days

    ## organise dataframe
    trt_cols = ['FirstImmunoTreatmentDate', 'FirstImmunoTreatmentTime',
                'T0BloodCollectionDate', 'T0BloodCollectionDuration', 'T0TimeOnBench',
                'SecondImmunoTreatmentDate', 'SecondImmunoTreatmetDuration',
                'T1BloodCollectionDate', 'T1BloodCollectionDuration', 'T1TimeOnBench',
                'NumberOfBloodSamples', 'AutoParsingNotes']
    treatment_df = treatment_df[trt_cols]

    #### curation remarks
    ## blood collection date
    # ix = treatment_df.T0BloodCollectionDuration > 0
    # msg = 'BloodCollectionDate does not match EventDate,'
    # blood_df['AutoParsingNotes'] += ix.map({True: msg, False: ''})

    ## TBD: blood collection hour vs treatment hour

    ####### parse full blood data
    #### curation remarks
    ## Blood collection date and event date dont match
    # ix = blood_df.BloodCollectionDate != blood_df.EventDate
    # msg = 'BloodCollectionDate does not match EventDate,'
    # blood_df['AutoParsingNotes'] += ix.map({True: msg, False: ''})

    ## negative time on bench
    ix = blood_df.TimeOnBench < 0
    msg = 'NegativeTimeOnBench,'
    blood_df['AutoParsingNotes'] += ix.map({True: msg, False: ''})

    #### sort blood_df
    ## organise time points
    # return blood_df,1
    # blood_df = blood_df.sort_values('BloodCollectionDate')
    # blood_df['BloodCollectionCounter'] = blood_df.groupby('SubjectId').cumcount() + 1

    ## Organise Notes
    blood_df.loc[blood_df['Not Done'] == 'Not Done', 'BloodCollectionNotes'] = 'Not Done'
    blood_df.loc[blood_df.BloodCollectionTimeNotes.notna(), 'BloodCollectionNotes'] = \
        'Preperation time exceed 4 hours - ' + blood_df.loc[
            blood_df.BloodCollectionTimeNotes.notna(), 'BloodCollectionTimeNotes']

    blood_df.AutoParsingNotes = blood_df.AutoParsingNotes.str.strip(', ')

    ## columns
    blood_cols = ['SubjectId', 'Site', 'Indication',
                  'Visit', 'EventDate',
                  'BloodCollectionDate',
                  'BloodCollectionTime', 'EndPrepTime', 'TimeOnBench',
                  'BloodCollectionNotes',
                  'TreatmentDate', 'TreatmentTime', 'AutoParsingNotes']
    blood_df = blood_df[blood_cols]

    ## add: patient does not have T0 treatment

    ## Time on bench is to long

    ## Missing treatment date

    ##### TBD

    ### identify first treatment

    ### prepare blood withdrawl data frame (for all withdrawl)

    ### merge with assay data (from AG)

    return blood_df, treatment_df


if __name__ == "__main__":
    clin_dict = pd.read_excel('../Input/OncoHost_20231224_145142.xlsx', sheet_name=None)

    blood_df, treatment_df = parse_blood(clin_dict)

    # writer = pd.ExcelWriter("Reports/230108_response_report.xlsx", engine="xlsxwriter")
    # for sheet_name, aux_df in df_dict.items():
    #     aux_df.to_excel(writer, sheet_name=sheet_name)
    # writer.close()
