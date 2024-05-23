import pandas as pd
from cd03_parse_treatment_change_stop_OI import sheet_parser
from cd01_utils_OI import viedoc_to_df
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from cd02_parse_blood_OI import parse_blood
import streamlit as st
# from streamlit_timeline import timeline
# from streamlit_timeline import st_timeline
import plotly.express as px


CLINCAL_DATA_PATH = '../Input/2024-03-26_V3_clinical_data_full.xlsx'
VIEDOC_EXPORT_PATH = '../Input/OncoHost_20231224_145142.xlsx'
# CLINCAL_DATA_PATH = ".\Patient_Timeline_Creator\Input\\2024-03-26_V3_clinical_data_full.xlsx"
# VIEDOC_EXPORT_PATH = ".\Patient_Timeline_Creator\Input\OncoHost_20231224_145142.xlsx"

color_map = {
    'Treatments': 'tab:orange',
    'Survival': 'tab:blue',
    'Blood Collection': 'tab:green'
}
# color_map2 = {
#     'Treatments': 'orange',
#     'Survival': 'blue',
#     'Blood Collection': 'green'
# }

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
    main_df['EventText'] = main_df['StatusType'] + ' ' + '(' + main_df['ReasonAndTChange'].fillna('') + ')'
    main_df['EventText'] = main_df['EventText'].fillna('')
    main_df['EventText'] = main_df['EventText'].replace(r'\(\)$', '', regex=True)

    # fix df:
    main_df = main_df[main_df['EventText'] != '']
    main_df = main_df[['SubjectId', 'StatusType', 'DateStatus', 'EventText']]
    main_df = main_df.sort_values(['SubjectId', 'DateStatus'])

    # main_df.to_excel("checking_change_Stop.xlsx", index=False)
    return main_df


def parse_orr_assessments(clin_dict):
    orr_df = viedoc_to_df(clin_dict['REC'], remove_retro=False).reset_index()
    orr_df.rename(columns={'Date ORR was completed:': 'ORRAssessmentDate',
                           'Overall Response Rate:': 'Rate'}, inplace=True)
    orr_df = orr_df[(orr_df['Was theOverall Response Rate evaluated?'] != 'No') & orr_df['Rate'].notna()]
    orr_df['ORRAssessmentDate'] = orr_df['ORRAssessmentDate'] + ' 00:00:00'
    # todo: consider what to do with empty rates?
    return orr_df[['SubjectId', 'ORRAssessmentDate', 'Rate']]


if __name__ == '__main__':
    # get input:
    # TODO: currently only some fields include curation - input type may change
    clin_dict = pd.read_excel(VIEDOC_EXPORT_PATH, sheet_name=None)
    clinical_df = pd.read_excel(CLINCAL_DATA_PATH)
    cols_to_keep = ['SubjectId', 'FirstTreatmentDate', 'ORR3MonthsDate', 'ORR3MonthsValue', 'ORR6MonthsDate',
                    'ORR6MonthsValue', 'ORR12MonthsDate', 'ORR12MonthsValue', 'ProgressionDate', 'OSDate',
                    'LastFollowUpVisitDate', 'ProposedTreatment']
    clinical_df = clinical_df[cols_to_keep]

    # get all events of treatment change, stop or eos:
    change_stop_df = get_treatment_change_and_stop(clin_dict)

    # get all blood collection events
    blood_df, treatment_df = parse_blood(clin_dict)
    blood_df.to_excel('checking_blood.xlsx', index=False)

    # get all overall response assessments:
    orr_df = parse_orr_assessments(clin_dict)

    all_timelines = []
    chemo_prog_to_ici_durations = []

    nums = []
    for x, y in zip(range(60, 0, -4), range(-60, 0, 4)):
        nums.append(x)
        nums.append(y)

    # get events for each patient (duplicates) and create timeline:
    # tuple format: [text, date, category]
    # categories: survival, blood collections, treatments
    for index, subject_row in clinical_df.iterrows():
        events = []
        sub_id = subject_row['SubjectId']

        # if sub_id not in ['IL-014-1903-NSCLC']:
        #     continue

        # 'FirstTreatmentDate', 'ProgressionDate', 'OSDate', 'LastFollowUpVisitDate'
        prp_trt = subject_row['ProposedTreatment']
        tup1 = (f'1st Treatment ({prp_trt})', clinical_df.loc[clinical_df['SubjectId'] == sub_id, 'FirstTreatmentDate'].iloc[0], 'Treatments')
        tup2 = ('Progression', clinical_df.loc[clinical_df['SubjectId'] == sub_id, 'ProgressionDate'].iloc[0], 'Survival')
        if pd.isna(clinical_df.loc[clinical_df['SubjectId'] == sub_id, 'OSDate'].iloc[0]):
            # add last follow up only if there is not death
            tup3 = ('Last FU', clinical_df.loc[clinical_df['SubjectId'] == sub_id, 'LastFollowUpVisitDate'].iloc[0], 'Survival')
        else:
            tup3 = ('Death', clinical_df.loc[clinical_df['SubjectId'] == sub_id, 'OSDate'].iloc[0], 'Survival')
        events.extend([tup1, tup2, tup3])

        # get treatment events:
        trt1_df = change_stop_df[(change_stop_df['SubjectId'] == sub_id)]
        for trt_i, trt_row in trt1_df.iterrows():
            if trt_row['StatusType'] != 'Death':
                tup = (trt_row['EventText'], trt_row['DateStatus'], 'Treatments')
                events.append(tup)

        # get blood collection and treatment events:
        blood1_df = blood_df[(blood_df['SubjectId'] == sub_id)]
        for blood_i, blood_row in blood1_df.iterrows():
            if blood_row['TreatmentDate'] is not None:
                tup = ('Treatment Given', blood_row['TreatmentDate'], 'Treatments')
                events.append(tup)
            if blood_row['BloodCollectionDate'] == 'Not Done':
                continue
            tup = ('Blood Collection', blood_row['BloodCollectionDate'], 'Blood Collection')
            events.append(tup)

        # get all ORR's:
        orr1_df = orr_df[orr_df['SubjectId'] == sub_id]
        for orr_i, orr_row in orr1_df.iterrows():
            text = 'Response Measured: ' + orr_row['Rate']
            tup = (text, orr_row['ORRAssessmentDate'], 'Survival')
            events.append(tup)

        events_df = pd.DataFrame(events, columns=['Event', 'Date', 'Type'])
        events_df = events_df.drop_duplicates()

        # remove empty dates and sort by dates
        events_df = events_df[events_df['Date'].notna()]
        events_df['Date'] = events_df['Date'].astype(str).apply(fix_dates)
        events_df['Date'] = pd.to_datetime(events_df['Date'])
        events_df.sort_values(by='Date', inplace=True)
        # print(sub_id)
        # print(events_df[['Date', 'Type']])

        # remove duplicate first treatment report
        first_treatment_date = events_df.loc[events_df['Event'].str.startswith('1st Treatment'), 'Date'].iloc[0]
        events_df = events_df[~((events_df['Date'] == first_treatment_date) & (events_df['Event'] == 'Treatment Given'))]

        # # plot timeline save as png
        # # todo: implement new version
        #
        # # items = []
        # # for index, row in events_df.iterrows():
        # #     item = {
        # #         "id": index + 1,
        # #         "content": row['Event'],
        # #         "start": row['Date'].strftime('%Y-%m-%d')
        # #     }
        # #     items.append(item)
        # # timeline = st_timeline(items, groups=[], options={}, height="300px")
        # # st.subheader("Selected item")
        # # st.write(timeline)
        #
        # # fig = px.timeline(events_df, x_start="Date", x_end="Date", y="Event", color="Type", title="Event Timeline")
        # fig = px.scatter(events_df, x='Date', y='Type', color='Type', title='Event Timeline', color_discrete_map=color_map2, hover_data={'Event': True})
        #
        # # Update the layout for better appearance and to prevent overlap
        # fig.update_layout(
        #     xaxis_title="Date",
        #     yaxis_title="Type",
        #     showlegend=True,
        #     xaxis=dict(tickformat="%b %Y", dtick="M1"),
        #     yaxis=dict(tickvals=events_df['Type']),
        #     margin=dict(l=150, r=50, b=100, t=100),  # Adjust margins to prevent overlap
        #     height=800  # Adjust plot height to be smaller
        # )
        #
        # fig.update_yaxes(autorange="reversed")  # Ensure events are listed top-down
        #
        # fig.show()
        # exit()

        levels = np.tile(nums, int(np.ceil(len(events_df) / 6)))[:len(events_df)]
        fig, ax = plt.subplots(figsize=(15, 6), constrained_layout=True)
        ax.set(title=f"Timeline of Events ({sub_id})")

        for date, level, event_type in zip(events_df['Date'], levels, events_df['Type']):
            color = color_map[event_type]
            ax.vlines(date, 0, level, color=color, alpha=0.7)  # The vertical stems.

        ax.plot(events_df['Date'], np.zeros_like(events_df['Date']), "-o", color="k", markerfacecolor="w")
        for date, level, event in zip(events_df['Date'], levels, events_df['Event']):
            xytext = (3, -5 if np.sign(level) > 0 else 1)
            ax.annotate(event, xy=(date, level),
                        xytext=xytext, textcoords="offset points",
                        fontsize=6,  # Adjust font size
                        horizontalalignment="left",
                        verticalalignment="center")

        # Set x-axis to display ticks every month
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        ax.yaxis.set_visible(False)
        ax.tick_params(axis='x', labelsize=5)
        ax.spines[["left", "top", "right"]].set_visible(False)
        ax.grid(True, which='both', linestyle='--', linewidth=0.3)
        ax.margins(y=0.1)

        plt.savefig(f'../Plots/{sub_id}_timeline.png')
        plt.close()

        subject_summary_row = '. '.join([f"{row['Date']}-{row['Event']}" for _, row in events_df.iterrows()])
        all_timelines.append({'SubjectId': sub_id,
                              'Timeline': subject_summary_row})

    # Reset index
    main_summary_df = pd.DataFrame(all_timelines)
    main_summary_df.to_csv('all_timelines.csv', index=False)

    # todo: combine dublicated patients?