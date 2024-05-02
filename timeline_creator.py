import pandas as pd
from cd03_parse_treatment_change_stop_OI import sheet_parser
from cd01_utils_OI import viedoc_to_df
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def fix_dates(date_str):
    if pd.notna(date_str) and 'NK' in date_str:
        parts = date_str.split('-')
        if parts[1].endswith('NK') and parts[2].endswith('NK'):  # Format: YYYY-NK-NK
            return f"{parts[0]}-01-15"
        if parts[2].endswith('NK'):  # Format: YYYY-MM-NK
            return f"{parts[0]}-{parts[1]}-15"
        if parts[1].endswith('NK'):  # Format: YYYY-NK-DD
            return f"{parts[0]}-01-{parts[2]}"
    elif date_str == 'NaT' or date_str == pd.NaT:  # Handle 'NaT' string
        return np.nan
    return date_str


def get_treatment_change_and_stop(clin_dict):
    # parse sheets and concat to main df:
    main_df = pd.DataFrame()
    for sheet in ['STAT', 'EOS', 'CMRX']:
        sheet_df = viedoc_to_df(clin_dict[sheet], remove_retro=False).reset_index()
        sheet_df = sheet_parser(sheet, sheet_df)
        main_df = pd.concat([main_df, sheet_df], axis=0, ignore_index=True)
    # remove almost duplicate rows (except dates and event id):
    columns_to_check = ['SubjectId', 'StatusType', 'ReasonsText', 'ChangeOfTreatment']
    main_df = main_df[~main_df.duplicated(subset=columns_to_check, keep='first')]
    # remove rows with no reported change or stop:
    main_df = main_df[~main_df['StatusType'].isin(['Continuing', 'Completed', '', np.nan])]
    # fix dates:
    main_df['DateStatus'] = main_df['DateStatus'].fillna(main_df['DateEvent'])
    main_df['DateStatus'] = main_df['DateStatus'].astype(str).apply(fix_dates)
    main_df['DateStatus'] = pd.to_datetime(main_df['DateStatus'])
    # create new columns:
    main_df['ReasonAndTChange'] = np.where(
        (main_df['ReasonsText'].notna() & main_df['ChangeOfTreatment'].notna()),
        main_df['ChangeOfTreatment'] + ',' + main_df['ReasonsText'],
        main_df['ReasonsText'].fillna('') + main_df['ChangeOfTreatment'].fillna(''))
    main_df['ReasonAndTChange'] = main_df['ReasonAndTChange'].str.strip('.,')
    main_df['ReasonAndTChange'] = main_df['ReasonAndTChange'].str.lower()

    # concat each event to a string:
    main_df['EventText'] = main_df['StatusType'].str.replace(' ', '') + ' ' + '(' + main_df['ReasonAndTChange'].fillna(
        '') + ')'
    main_df['EventText'] = main_df['EventText'].fillna('')
    main_df['EventText'] = main_df['EventText'].replace(r'\(\)$', '', regex=True)

    # fix df:
    main_df = main_df[main_df['EventText'] != '']
    main_df = main_df[['SubjectId', 'StatusType', 'DateStatus', 'EventText']]
    main_df = main_df.sort_values(['SubjectId', 'DateStatus'])

    # main_df.to_excel("checking_change_Stop.xlsx", index=False)
    return main_df


if __name__ == '__main__':
    # get input:
    clin_dict = pd.read_excel('Input/OncoHost_20231224_145142.xlsx', sheet_name=None)
    dup_id_df = pd.read_excel('Input/Duplicate_chemo_immuno_patients.xlsx')
    clinical_df = pd.read_excel('Input/duplicate patients cohort data.xlsx')
    cols_to_keep = ['SubjectId', 'FirstTreatmentDate', 'ProgressionDate', 'OSDate', 'LastFollowUpVisitDate']  # add orr's?
    clinical_df = clinical_df[cols_to_keep]

    # get all events of treatment change, stop or eos:
    change_stop_df = get_treatment_change_and_stop(clin_dict)

    all_timelines = []
    chemo_prog_to_ici_durations = []

    # get events for each patient (duplicates) and create timeline:
    for i, row in dup_id_df.iterrows():
        events = []
        chemo_sub_id = row['SubjectId_Chemo']
        ici_sub_id = row['SubjectId_Immuno']

        # these dates should be equal in both dubs:
        for col in ['OSDate', 'LastFollowUpVisitDate']:
            date1 = clinical_df.loc[clinical_df['SubjectId'] == ici_sub_id, col].iloc[0]
            date2 = clinical_df.loc[clinical_df['SubjectId'] == chemo_sub_id, col].iloc[0]
            if pd.notna(date1) and pd.notna(date2) and (date1 != date2):
                print(f"descriptancy between duplicates {chemo_sub_id} and {ici_sub_id} on {col}")

        # 'FirstTreatmentDate', 'ProgressionDate', 'OSDate', 'LastFollowUpVisitDate'
        tup1 = ('1st Chemo', clinical_df.loc[clinical_df['SubjectId'] == chemo_sub_id, 'FirstTreatmentDate'].iloc[0], 'C')
        tup2 = ('1st Immuno', clinical_df.loc[clinical_df['SubjectId'] == ici_sub_id, 'FirstTreatmentDate'].iloc[0], 'I')
        tup3 = ('Progression Chemo', clinical_df.loc[clinical_df['SubjectId'] == chemo_sub_id, 'ProgressionDate'].iloc[0], 'C')
        tup4 = ('Progression Immuno', clinical_df.loc[clinical_df['SubjectId'] == ici_sub_id, 'ProgressionDate'].iloc[0], 'I')
        if pd.isna(clinical_df.loc[clinical_df['SubjectId'] == ici_sub_id, 'OSDate'].iloc[0]):
            # add last follow up only if there is not death
            tup5 = ('Last FU', clinical_df.loc[clinical_df['SubjectId'] == ici_sub_id, 'LastFollowUpVisitDate'].iloc[0], 'I')
        else:
            tup5 = ('Death', clinical_df.loc[clinical_df['SubjectId'] == ici_sub_id, 'OSDate'].iloc[0], 'I')
        events.extend([tup1, tup2, tup3, tup4, tup5])

        # get treatment events:
        trt1_df = change_stop_df[(change_stop_df['SubjectId'] == chemo_sub_id)]
        for i, row in trt1_df.iterrows():
            if row['StatusType'] != 'Death':
                tup = (row['EventText'], row['DateStatus'], 'C')
                events.append(tup)
        trt2_df = change_stop_df[(change_stop_df['SubjectId'] == ici_sub_id)]
        for i, row in trt2_df.iterrows():
            if row['StatusType'] != 'Death':
                tup = (row['EventText'], row['DateStatus'], 'I')
                events.append(tup)

        events_df = pd.DataFrame(events, columns=['Event', 'Date', 'Type'])
        events_df = events_df.drop_duplicates()

        # remove empty dates and sort by dates
        events_df = events_df[events_df['Date'].notna()]
        events_df['Date'] = pd.to_datetime(events_df['Date'])
        events_df.sort_values(by='Date', inplace=True)

        # get chemo progression to start ici duration for histogram:
        if ('1st Immuno' in events_df['Event'].values) and ('Progression Chemo' in events_df['Event'].values):
            date1 = events_df.loc[events_df['Event'] == '1st Immuno', 'Date'].iloc[0]
            date2 = events_df.loc[events_df['Event'] == 'Progression Chemo', 'Date'].iloc[0]
            durr = (date1 - date2).days
            chemo_prog_to_ici_durations.append(durr)

        # plot timeline save as png
        color_map = {'C': 'tab:blue', 'I': 'tab:orange'}
        nums = [(-1) ** i * (i + 1) for i in range(20, 0, -1)]
        levels = np.tile(nums, int(np.ceil(len(events_df) / 6)))[:len(events_df)]
        fig, ax = plt.subplots(figsize=(10, 4), constrained_layout=True)
        ax.set(title=f"Timeline of Events ({chemo_sub_id}/{ici_sub_id})")
        for date, level, event_type in zip(events_df['Date'], levels, events_df['Type']):
            color = color_map.get(event_type, 'black')
            ax.vlines(date, 0, level, color=color, alpha=0.7)  # The vertical stems.
        ax.plot(events_df['Date'], np.zeros_like(events_df['Date']), "-o",
                color="k", markerfacecolor="w")  # Baseline and markers on it.
        for date, level, event in zip(events_df['Date'], levels, events_df['Event']):
            xytext = (3, -5 if np.sign(level) > 0 else 1)
            ax.annotate(event, xy=(date, level),
                        xytext=xytext, textcoords="offset points",
                        fontsize=6,  # Adjust font size
                        horizontalalignment="left",
                        verticalalignment="center")
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        ax.yaxis.set_visible(False)
        ax.tick_params(axis='x', labelsize=5)
        ax.spines[["left", "top", "right"]].set_visible(False)
        ax.grid(True, which='both', linestyle='--', linewidth=0.3)
        ax.margins(y=0.1)
        plt.savefig(f'Plots/{chemo_sub_id}_{ici_sub_id}_timeline.png')
        plt.close()

        events_df['Date'] = pd.to_datetime(events_df['Date']).dt.strftime('%Y-%m-%d')
        # check if first treatment date exists, if not add to the begining of the df first treatment with no date
        if '1st Chemo' not in events_df['Event'].values:
            new_row = {'Event': '1st Chemo', 'Date': 'Unknown date'}
            events_df = pd.concat([pd.DataFrame([new_row]), events_df], ignore_index=True)
        if '1st Immuno' not in events_df['Event'].values:
            new_row = {'Event': '1st Immuno', 'Date': 'Unknown date'}
            events_df = pd.concat([pd.DataFrame([new_row]), events_df], ignore_index=True)

        subject_summary_row = '. '.join([f"{row['Date']}-{row['Event']}" for _, row in events_df.iterrows()])
        all_timelines.append({'SubjectIdChemo': chemo_sub_id,
                              'SubjectIdImmuno': ici_sub_id,
                              'Timeline': subject_summary_row})

# Reset index
main_summary_df = pd.DataFrame(all_timelines)
main_summary_df.to_csv('all_timelines.csv', index=False)