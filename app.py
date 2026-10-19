
import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import fetch_data


st.set_page_config(
    page_title="StrategicERP Analytics",
    page_icon="📊",
    layout="wide",
)

st.title("StrategicERP Analytics")
st.caption("Timesheet performance and Change Request analysis")

# Improve readability of the existing sidebar filters while preserving layout.
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] [data-baseweb="select"] div,
    [data-testid="stSidebar"] [data-testid="stDateInput"] input {
        font-size: 1rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        font-size: 1.02rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------- DATA LOADING --------------------

@st.cache_data(ttl=300)
def load_data():
    df = fetch_data()

    # Standardize column names returned by the API.
    df.columns = [str(col).strip() for col in df.columns]

    required_columns = [
        "TimeSheet_Date",
        "Developer",
        "Team",
        "Total_Efforts",
        "Actual_Efforts",
        "CR_No",
        "Project_Name",
        "Dev_Status",
        "CR_Estimated_Hours",
        "CR_Actual_Hours",
        "Task_Type",
        "CR_Effort",
        "CR_Actual_Effort",
    ]

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"Missing API columns: {missing}")

    # Convert dates and numerical fields.
    df["TimeSheet_Date"] = pd.to_datetime(
        df["TimeSheet_Date"], errors="coerce"
    )

    numeric_columns = [
        "Total_Efforts",
        "Actual_Efforts",
        "CR_Estimated_Hours",
        "CR_Actual_Hours",
        "CR_Effort",
        "CR_Actual_Effort",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Keep raw rows unchanged for the detail table.
    return df


try:
    df = load_data()
except Exception as error:
    st.error("Unable to load dashboard data.")
    st.code(str(error))
    st.stop()


# -------------------- SIDEBAR FILTERS --------------------

st.sidebar.header("Filters")

min_date = df["TimeSheet_Date"].min()
max_date = df["TimeSheet_Date"].max()

if pd.notna(min_date) and pd.notna(max_date):
    selected_dates = st.sidebar.date_input(
        "Timesheet date range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date(),
    )

    if isinstance(selected_dates, (tuple, list)):
        if len(selected_dates) == 2:
            start_date, end_date = selected_dates
        elif len(selected_dates) == 1:
            start_date = end_date = selected_dates[0]
        else:
            start_date, end_date = min_date.date(), max_date.date()
    else:
        start_date = end_date = selected_dates
else:
    start_date = None
    end_date = None


def get_options(column):
    values = df[column].dropna().astype(str).str.strip()
    values = values[values != ""].unique().tolist()
    return sorted(values)


developers = st.sidebar.multiselect(
    "Developer",
    get_options("Developer"),
)

teams = st.sidebar.multiselect(
    "Team",
    get_options("Team"),
)

projects = st.sidebar.multiselect(
    "Project",
    get_options("Project_Name"),
)

# -------------------- APPLY FILTERS --------------------

filtered = df.copy()

if start_date is not None and end_date is not None:
    filtered = filtered[
        filtered["TimeSheet_Date"].dt.date.between(
            start_date, end_date
        )
    ]

if developers:
    filtered = filtered[filtered["Developer"].isin(developers)]

if teams:
    filtered = filtered[filtered["Team"].isin(teams)]

if projects:
    filtered = filtered[filtered["Project_Name"].isin(projects)]

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()


# -------------------- KPI CARDS --------------------

# Master-level totals repeat across task rows. Count each
# timesheet master once using the date, developer, team,
# and repeated total fields as a practical grouping.
master_key = [
    "TimeSheet_Date",
    "Developer",
    "Team",
    "Total_Efforts",
    "Actual_Efforts",
]

master_totals = filtered.drop_duplicates(subset=master_key)

total_actual = master_totals["Actual_Efforts"].sum()
total_effort = master_totals["Total_Efforts"].sum()

unique_crs = filtered.loc[
    filtered["CR_No"].notna()
    & ~filtered["CR_No"].astype(str).str.strip().str.lower().isin(
        ["", "scrum call", "timesheet filling", "liquibase deployment"]
    ),
    "CR_No",
].nunique()

unique_developers = filtered["Developer"].nunique()

k1, k2, k3, k4 = st.columns(4)

k1.metric("Total Effort", f"{total_effort:,.2f} hrs")
k2.metric("Actual Effort", f"{total_actual:,.2f} hrs")
k3.metric("Unique CR Identifiers", f"{unique_crs:,}")
k4.metric("Developers", f"{unique_developers:,}")


st.divider()


# -------------------- CHARTS --------------------

left, right = st.columns(2)

with left:
    st.subheader("Actual Effort by Developer")

    developer_effort = (
        master_totals.groupby("Developer", as_index=False)
        ["Actual_Efforts"]
        .sum()
        .sort_values("Actual_Efforts", ascending=False)
    )

    fig = px.bar(
        developer_effort,
        x="Developer",
        y="Actual_Efforts",
        labels={
            "Developer": "Developer",
            "Actual_Efforts": "Actual effort (hours)",
        },
    )

    fig.update_layout(
        xaxis_tickangle=-35,
        margin=dict(l=10, r=10, t=20, b=10),
    )

    st.plotly_chart(fig, use_container_width=True)


with right:
    st.subheader("Actual Effort by Team")

    team_effort = (
        master_totals.groupby("Team", as_index=False)
        ["Actual_Efforts"]
        .sum()
        .sort_values("Actual_Efforts", ascending=False)
    )

    fig = px.bar(
        team_effort,
        x="Team",
        y="Actual_Efforts",
        labels={
            "Team": "Team",
            "Actual_Efforts": "Actual effort (hours)",
        },
    )

    fig.update_layout(
        xaxis_tickangle=-35,
        margin=dict(l=10, r=10, t=20, b=10),
    )

    st.plotly_chart(fig, use_container_width=True)


st.subheader("Daily Actual Effort")

daily_effort = (
    master_totals.groupby("TimeSheet_Date", as_index=False)
    ["Actual_Efforts"]
    .sum()
    .sort_values("TimeSheet_Date")
)

fig = px.line(
    daily_effort,
    x="TimeSheet_Date",
    y="Actual_Efforts",
    markers=True,
    labels={
        "TimeSheet_Date": "Date",
        "Actual_Efforts": "Actual effort (hours)",
    },
)

st.plotly_chart(fig, use_container_width=True)


# -------------------- DEVELOPER ACTIVITY HEATMAP --------------------

st.divider()
st.subheader("Developer Activity Heatmap")
st.caption(
    "Daily actual effort by developer. Darker cells indicate higher recorded effort."
)

activity_data = master_totals.dropna(
    subset=["TimeSheet_Date", "Developer", "Actual_Efforts"]
).copy()

if activity_data.empty:
    st.info("No developer activity is available for the selected filters.")
else:
    # Aggregate first so each developer/date cell represents total actual effort.
    activity_data = (
        activity_data.groupby(
            ["TimeSheet_Date", "Developer"], as_index=False
        )["Actual_Efforts"]
        .sum()
    )

    activity_matrix = activity_data.pivot(
        index="Developer",
        columns="TimeSheet_Date",
        values="Actual_Efforts",
    ).fillna(0)

    # Sort dates chronologically and developers by total recorded effort.
    activity_matrix = activity_matrix.reindex(
        sorted(activity_matrix.columns), axis=1
    )
    activity_matrix = activity_matrix.loc[
        activity_matrix.sum(axis=1).sort_values(ascending=False).index
    ]
    activity_matrix.columns = [
        pd.Timestamp(date).strftime("%d/%m") for date in activity_matrix.columns
    ]

    heatmap_fig = px.imshow(
        activity_matrix,
        aspect="auto",
        color_continuous_scale="Blues",
        labels={
            "x": "Timesheet date",
            "y": "Developer",
            "color": "Actual effort (hours)",
        },
    )
    heatmap_fig.update_layout(
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_tickangle=-45,
    )
    st.plotly_chart(heatmap_fig, use_container_width=True)


# -------------------- TASK-TYPE EFFORT BREAKDOWN --------------------

st.divider()
st.subheader("Task-Type Effort Trend by Developer")
st.caption(
    "View daily task-level hours for one selected developer. Choose whether "
    "to display recorded effort or actual effort."
)

task_type_data = filtered[
    filtered["TimeSheet_Date"].notna()
    & filtered["Developer"].notna()
    & filtered["Task_Type"].notna()
].copy()

task_type_data["Task_Type"] = (
    task_type_data["Task_Type"].astype(str).str.strip()
)
task_type_data["Developer"] = (
    task_type_data["Developer"].astype(str).str.strip()
)
task_type_data = task_type_data[
    (task_type_data["Task_Type"] != "")
    & (task_type_data["Developer"] != "")
]

if task_type_data.empty:
    st.info("No task-type records are available for the selected filters.")
else:
    chart_developers = sorted(task_type_data["Developer"].unique().tolist())

    selected_task_developer = st.selectbox(
        "Select developer for this chart",
        options=["Select a developer..."] + chart_developers,
        index=0,
        key="task_type_trend_developer_filter_v2",
    )

    if selected_task_developer == "Select a developer...":
        st.info("Select a developer to display the daily stacked effort chart.")
    else:
        developer_task_data = task_type_data[
            task_type_data["Developer"] == selected_task_developer
        ].copy()

        effort_column = "CR_Actual_Effort"

        developer_task_data[effort_column] = pd.to_numeric(
            developer_task_data[effort_column], errors="coerce"
        )
        developer_task_data = developer_task_data.dropna(
            subset=[effort_column]
        )

        if developer_task_data.empty:
            st.info(
                f"No actual effort records are available for {selected_task_developer}."
            )
        else:
            daily_task_type_effort = (
                developer_task_data.groupby(
                    ["TimeSheet_Date", "Task_Type"], as_index=False
                )[effort_column]
                .sum()
                .sort_values("TimeSheet_Date")
            )
            daily_task_type_effort = daily_task_type_effort.rename(
                columns={effort_column: "Hours"}
            )

            task_type_fig = px.bar(
                daily_task_type_effort,
                x="TimeSheet_Date",
                y="Hours",
                color="Task_Type",
                barmode="stack",
                labels={
                    "TimeSheet_Date": "Date",
                    "Hours": "Hours",
                    "Task_Type": "Task type",
                },
                hover_data={"Hours": ":.2f"},
                title=f"Daily Actual effort by Task Type — {selected_task_developer}",
            )
            task_type_fig.update_layout(
                barmode="stack",
                xaxis_title="Date",
                yaxis_title="Hours",
                legend_title_text="Task type",
                margin=dict(l=10, r=10, t=60, b=10),
            )
            st.plotly_chart(task_type_fig, use_container_width=True)

            task_type_summary = (
                developer_task_data.groupby("Task_Type", as_index=False)
                .agg(
                    Recorded_Effort=("CR_Effort", "sum"),
                    Actual_Effort=("CR_Actual_Effort", "sum"),
                )
                .sort_values("Actual_Effort", ascending=False)
            )

            st.caption(f"Task-type totals for {selected_task_developer}")
            st.dataframe(
                task_type_summary.rename(columns={
                    "Task_Type": "Task Type",
                    "Recorded_Effort": "Recorded Effort (hours)",
                    "Actual_Effort": "Actual Effort (hours)",
                }),
                use_container_width=True,
                hide_index=True,
            )



# -------------------- ESTIMATED VS ACTUAL CR HOURS --------------------

st.divider()
st.subheader("Estimated vs. Actual CR Hours")

st.caption(
    "Compare estimated and actual CR hours by Change Request and developer."
)

cr_hours = filtered[
    filtered["CR_No"].notna()
    & filtered["CR_Estimated_Hours"].notna()
    & filtered["CR_Actual_Hours"].notna()
].copy()

cr_hours["CR_No"] = cr_hours["CR_No"].astype(str).str.strip()
cr_hours["Developer"] = (
    cr_hours["Developer"].fillna("").astype(str).str.strip()
)

cr_hours = cr_hours[
    (cr_hours["CR_No"] != "")
    & (cr_hours["CR_Estimated_Hours"] >= 0)
    & (cr_hours["CR_Actual_Hours"] >= 0)
]

# Avoid counting identical CR/developer/hour combinations more than once.
cr_hours = cr_hours.drop_duplicates(
    subset=[
        "CR_No",
        "Developer",
        "CR_Estimated_Hours",
        "CR_Actual_Hours",
    ]
)

if cr_hours.empty:
    st.info(
        "No CR records with both estimated and actual hours are available."
    )

else:
    cr_options = sorted(cr_hours["CR_No"].unique().tolist())

    f1, f2, f3 = st.columns(3)

    # -------------------- CR FILTER --------------------

    with f1:
        selected_crs = st.multiselect(
            "Filter by CR No",
            options=cr_options,
            key="cr_hours_cr_filter",
        )

    # -------------------- DEPENDENT DEVELOPER FILTER --------------------

    # Restrict developer options to developers associated with
    # the selected CRs. With no CR selected, show all developers.
    if selected_crs:
        related_developers = sorted(
            cr_hours.loc[
                cr_hours["CR_No"].isin(selected_crs)
                & (cr_hours["Developer"] != ""),
                "Developer",
            ].unique().tolist()
        )
    else:
        related_developers = sorted(
            d for d in cr_hours["Developer"].unique().tolist() if d
        )

    # Keep the existing selection only if it is still valid.
    # On the first CR selection, automatically select all related
    # developers. On subsequent reruns, preserve manual selections
    # that remain valid for the current CR selection.
    developer_key = "cr_hours_developer_filter"
    previous_crs_key = "cr_hours_previous_cr_filter"

    previous_crs = st.session_state.get(previous_crs_key, [])
    previous_developers = st.session_state.get(developer_key, [])

    if selected_crs != previous_crs:
        # CR selection changed: select all developers related to it.
        st.session_state[developer_key] = related_developers
        st.session_state[previous_crs_key] = selected_crs.copy()
    else:
        # Keep manual selections, removing any invalid options.
        st.session_state[developer_key] = [
            d for d in previous_developers if d in related_developers
        ]

    with f2:
        selected_developers = st.multiselect(
            "Filter by Developer",
            options=related_developers,
            key=developer_key,
        )

    # -------------------- TOP CR FILTER --------------------

    with f3:
        top_n = st.selectbox(
            "Show top CRs by actual hours",
            options=[10, 20, 50, "All"],
            index=0,
            key="cr_hours_top_n",
        )

    # -------------------- FILTER CHART DATA --------------------

    chart_filtered = cr_hours.copy()

    if selected_crs:
        chart_filtered = chart_filtered[
            chart_filtered["CR_No"].isin(selected_crs)
        ]

    if selected_developers:
        chart_filtered = chart_filtered[
            chart_filtered["Developer"].isin(selected_developers)
        ]
    elif related_developers:
        # If all developers are manually deselected, show no results.
        chart_filtered = chart_filtered.iloc[0:0]

    if chart_filtered.empty:
        st.info("No CRs match the selected chart filters.")

    else:
        # Aggregate hours per CR after applying the developer filter.
        cr_summary = (
            chart_filtered.groupby("CR_No", as_index=False)
            .agg(
                Estimated_Hours=("CR_Estimated_Hours", "sum"),
                Actual_Hours=("CR_Actual_Hours", "sum"),
            )
        )

        cr_summary["Variance_Hours"] = (
            cr_summary["Actual_Hours"]
            - cr_summary["Estimated_Hours"]
        )

        cr_summary = cr_summary.sort_values(
            "Actual_Hours",
            ascending=False,
        )

        if top_n != "All" and not selected_crs:
            cr_summary = cr_summary.head(top_n)

        # -------------------- COMPARISON CHART --------------------

        chart_data = cr_summary.melt(
            id_vars=["CR_No"],
            value_vars=["Estimated_Hours", "Actual_Hours"],
            var_name="Effort_Type",
            value_name="Hours",
        )

        chart_data["Effort_Type"] = chart_data["Effort_Type"].map({
            "Estimated_Hours": "Estimated",
            "Actual_Hours": "Actual",
        })

        fig = px.bar(
            chart_data,
            x="CR_No",
            y="Hours",
            color="Effort_Type",
            barmode="group",
            title="Estimated vs. Actual Hours by CR",
            labels={
                "CR_No": "Change Request",
                "Hours": "Hours",
                "Effort_Type": "Effort Type",
            },
            hover_data={"Hours": ":.2f"},
        )

        fig.update_layout(
            xaxis_tickangle=-45,
            legend_title_text="",
            margin=dict(l=10, r=10, t=60, b=10),
        )

        st.plotly_chart(fig, use_container_width=True)

        # -------------------- COMPARISON TABLE --------------------

        st.subheader("CR Effort Comparison")

        st.dataframe(
            cr_summary.rename(columns={
                "CR_No": "CR No",
                "Estimated_Hours": "Estimated Hours",
                "Actual_Hours": "Actual Hours",
                "Variance_Hours": "Variance (Actual - Estimated)",
            }),
            use_container_width=True,
            hide_index=True,
        )



# -------------------- DETAIL TABLE --------------------

st.divider()
st.subheader("Timesheet and CR Details")

st.caption(
    "CR metadata can be blank on repeated task rows because of the SQL "
    "query's ROW_NUMBER() logic."
)

display_columns = [
    "TimeSheet_Date",
    "Developer",
    "Team",
    "Total_Efforts",
    "Actual_Efforts",
    "Sr",
    "CR_No",
    "CR_Date",
    "Project_Name",
    "Dev_Status",
    "Responsible_Developer",
    "CR_Estimated_Hours",
    "CR_Actual_Hours",
    "Task_Type",
    "Start_Time",
    "End_Time",
    "CR_Effort",
    "CR_Actual_Effort",
]

display_columns = [
    col for col in display_columns if col in filtered.columns
]

table = filtered[display_columns].copy()

table["TimeSheet_Date"] = table["TimeSheet_Date"].dt.strftime(
    "%d/%m/%Y"
)

if "CR_Date" in table.columns:
    table["CR_Date"] = pd.to_datetime(
        table["CR_Date"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    height=500,
)

csv_data = table.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "Download filtered data as CSV",
    data=csv_data,
    file_name="strategicerp_timesheet_report.csv",
    mime="text/csv",
)


