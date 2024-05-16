"""
Created on 07.12.23
By Or Itzhaki
"""


def parse_status(sheet_df):
    # choose columns to keep, organize and rename them:
    status_df = sheet_df[
        ['SubjectId', 'Event Id', 'Event date', 'Patient Treatment Status at this visit:', 'Stop date',
         'Please provide reason forsubject is\'Not under treatment\'', 'Changed Treatment, specify',
         'Please provide reason for changingtreatment', 'Date of change',
         'Please provide reason for stopping treatment', 'Date treatment stopped'
         ]]
    status_df.columns = ['SubjectId', 'EventID', 'DateEvent', 'StatusType', 'DateStop',
                         'ReasonNoTreatment', 'ChangedTreatment',
                         'ReasonChangeTreatment', 'DateChangeTreatment',
                         'ReasonStopTreatment', 'DateStopTreatment']

    # add a column for all the merged reasons and drop first row:
    status_df.insert(4, 'DateStatus', '')
    status_df.insert(5, 'ReasonsText', '')
    status_df.insert(6, 'ChangeOfTreatment', '')
    status_df = status_df.drop(status_df.index[0])

    # merge reasons and date values:
    status_df.loc[status_df['StatusType'] == 'Not under treatment', 'ReasonsText'] = status_df['ReasonNoTreatment']
    status_df.loc[status_df['StatusType'] == 'Not under treatment', 'DateStatus'] = status_df['DateStop']

    status_df.loc[status_df['StatusType'] == 'Stopped Treatment', 'ReasonsText'] = status_df['ReasonStopTreatment']
    status_df.loc[status_df['StatusType'] == 'Stopped Treatment', 'DateStatus'] = status_df['DateStopTreatment']

    status_df.loc[status_df['StatusType'] == 'Changed Treatment', 'ReasonsText'] = status_df['ReasonChangeTreatment']
    status_df['DateChangeTreatment'] = status_df['DateChangeTreatment'].fillna(status_df['DateEvent'])
    status_df.loc[status_df['StatusType'] == 'Changed Treatment', 'DateStatus'] = status_df['DateChangeTreatment']
    status_df.loc[status_df['StatusType'] == 'Changed Treatment', 'ChangeOfTreatment'] = status_df['ChangedTreatment']

    # rename types:
    status_df.loc[status_df['StatusType'] == 'Continuing as planned', 'StatusType'] = 'Continuing'
    status_df.loc[status_df['StatusType'] == 'Not under treatment', 'StatusType'] = 'Stopped Treatment'

    # remove irrelevant columns:
    columns_to_remove = ['ReasonNoTreatment', 'DateStop', 'ReasonStopTreatment', 'DateStopTreatment',
                         'ChangedTreatment', 'ReasonChangeTreatment', 'DateChangeTreatment']
    status_df = status_df.drop(columns=columns_to_remove)

    return status_df


def parse_end_of_study(sheet_df):
    # choose columns to keep, organize and rename them:
    eos_df = sheet_df[['SubjectId', 'Event Id', 'Event date', 'Primary reason for Discontinuation',
                       'Date of study completion/discontinuation', 'Other, please specify:', 'Please specify',
                       'Date of Death -Overall survival (OS)', 'Provide primary reason for Death:'
                       ]]
    eos_df.columns = ['SubjectId', 'EventID', 'DateEvent', 'StatusType',
                      'DateStatus', 'OtherStopReasons', 'StopReasons',
                      'DateDeath', 'DeathReason'
                      ]

    # add a column for all the merged reasons and drop first row:
    eos_df.insert(5, 'ReasonsText', '')
    eos_df.insert(6, 'ChangeOfTreatment', '')
    eos_df = eos_df.drop(eos_df.index[0])

    # rename values, merge status reasons and date values:
    eos_df.loc[eos_df['StatusType'].isna(), 'StatusType'] = 'Completed'

    eos_df.loc[eos_df['StatusType'] == 'Death', 'ReasonsText'] = eos_df['DeathReason']
    eos_df.loc[eos_df['StatusType'] == 'Death', 'DateStatus'] = eos_df['DateDeath']

    eos_df.loc[eos_df['StatusType'] == 'Withdrawal by Investigator', 'StatusType'] = 'Changed/Stopped Treatment'
    eos_df.loc[eos_df['StatusType'] == 'Withdrawal of consent', 'StatusType'] = 'Changed/Stopped Treatment'
    eos_df.loc[eos_df['StatusType'] == 'Patient refused / unable to continue', 'StatusType'] = 'Changed/Stopped Treatment'
    eos_df.loc[eos_df['StatusType'] == 'Patient lost to follow-up', 'StatusType'] = 'Changed/Stopped Treatment'
    eos_df.loc[eos_df['StatusType'] == 'Sponsor Early Termination', 'StatusType'] = 'Changed/Stopped Treatment'
    eos_df.loc[eos_df['StatusType'] == 'Changed/Stopped Treatment', 'ReasonsText'] = eos_df['StopReasons']

    eos_df.loc[eos_df['StatusType'] == 'Other reason', 'ReasonsText'] = eos_df['OtherStopReasons']
    eos_df.loc[eos_df['StatusType'] == 'Other reason', 'StatusType'] = 'Changed/Stopped Treatment'

    # remove irrelevant columns:
    columns_to_remove = ['DeathReason', 'DateDeath', 'StopReasons', 'OtherStopReasons']
    eos_df = eos_df.drop(columns=columns_to_remove)

    return eos_df


def parse_cmrx(sheet_df):
    # choose columns to keep, organize and rename them:
    cmrx_df = sheet_df[['SubjectId', 'Event Id', 'Event date', 'End Date', 'Treatment changes/Stop reason', 'Treatment drug']]
    cmrx_df.columns = ['SubjectId', 'EventID', 'DateEvent', 'DateStatus', 'ReasonsText', 'ChangeOfTreatment']

    # add a column for all the merged reasons and drop first row:
    cmrx_df.insert(3, 'StatusType', 'Changed/Stopped Treatment')
    # PLEASE NOTICE: some of these patients have stopped treatment d/t death, and therefor exist in the EOS (varified)
    cmrx_df = cmrx_df.drop(cmrx_df.index[0])
    return cmrx_df


# Function to parse a sheet using the dictionary
def sheet_parser(sheet_name, sheet_df):
    if sheet_name == 'STAT':
        parsed_sheet_df = parse_status(sheet_df)
        parsed_sheet_df['Stop/ChangeOrigin'] = 'STAT'
    elif sheet_name == 'EOS':
        parsed_sheet_df = parse_end_of_study(sheet_df)
        parsed_sheet_df['Stop/ChangeOrigin'] = 'EOS'
    elif sheet_name == 'CMRX':
        parsed_sheet_df = parse_cmrx(sheet_df)
        parsed_sheet_df['Stop/ChangeOrigin'] = 'CMRX'
    return parsed_sheet_df