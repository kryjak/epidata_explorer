import streamlit as st
import pandas as pd
from available_signals import names_to_sources
from geo_codes import (
    geotypes_to_display,
    display_to_geotypes,
    nation_to_display,
    display_to_nation,
    state_abbrvs_to_display,
    display_to_state_abbrvs,
    county_by_state,
    display_to_county_fips,
    display_to_hrr,
    hrr_by_state,
    hss_region_to_display,
    display_to_hss_region,
    msa_by_state,
    display_to_msa,
)
from utils import (
    get_shared_geotypes,
    get_shared_dates,
    to_epidate_range,
    to_epiweek_range,
)

from analysis_tools import (
    fetch_covidcast_data,
    get_lags_and_correlations,
)

from plotting_utils import (
    update_plot_with_lag,
    plot_correlation_vs_lag,
    plot_correlation_distribution,
)

from helper_texts import get_correlation_method_info

covidcast_metadata = pd.read_csv("covidcast_metadata.csv")

st.title("COVID-19 Signal Correlation and Forecast Analysis")
st.write("This app allows you to explore the correlation between two COVID-19 signals.")

signals_display = list(names_to_sources.keys())

col1, col2 = st.columns(2)
with col1:
    signal_display1 = st.selectbox("Choose signal 1:", signals_display)
    source1, signal1 = names_to_sources[signal_display1]
with col2:
    signal_display2 = st.selectbox(
        "Choose signal 2:",
        [signal for signal in signals_display if signal != signal_display1],
    )
    source2, signal2 = names_to_sources[signal_display2]

shared_geo_types = get_shared_geotypes(
    covidcast_metadata, signal_display1, signal_display2
)
shared_geo_types_display = [
    geotypes_to_display[geo_type] for geo_type in shared_geo_types
]

col1, col2 = st.columns(2)
with col1:
    geo_type_display = st.selectbox("Browse by:", shared_geo_types_display)
    geo_type = display_to_geotypes[geo_type_display]
with col2:
    if geo_type == "nation":
        region_display = st.selectbox("Choose a nation:", nation_to_display.values())
        region = display_to_nation[region_display]
    elif geo_type == "state":
        region_display = st.selectbox(
            "Choose a state:", state_abbrvs_to_display.values()
        )
        region = display_to_state_abbrvs[region_display]
    elif geo_type == "county":
        state_display = st.selectbox(
            "Choose a state:", state_abbrvs_to_display.values()
        )
        region_display = st.selectbox(
            "Choose a county:", county_by_state[state_display]
        )
        region = display_to_county_fips[region_display]
    elif geo_type == "hrr":
        state_display = st.selectbox(
            "Choose a state:", state_abbrvs_to_display.values()
        )
        region_display = st.selectbox(
            "Choose an Hospital Referral Region:", hrr_by_state[state_display]
        )
        region = display_to_hrr[region_display]
    elif geo_type == "hhs":
        region_display = st.selectbox(
            "Choose an HHS Region:", hss_region_to_display.values()
        )
        region = display_to_hss_region[region_display]
    elif geo_type == "msa":
        state_display = st.selectbox(
            "Choose a state:", state_abbrvs_to_display.values()
        )
        region_display = st.selectbox(
            "Choose a Metropolitan Statistical Area:", msa_by_state[state_display]
        )
        region = display_to_msa[region_display]
    elif geo_type == "dma":
        st.error(
            "Designated Market Areas (DMAs) are proprietary information released by Nielsen. The subscription to this data costs $8000. Sorry.",
            icon="🚨",
        )
    else:
        st.error(f"Invalid geo_type: {geo_type}", icon="🚨")
        st.stop()

try:
    shared_init_date, shared_final_date, time_type = get_shared_dates(
        covidcast_metadata, signal_display1, signal_display2, geo_type
    )
except ValueError:
    st.error(
        "Signals must have the same reporting frequency ('time_type') to be compared. Try changing the signal or at least one of the regions.",
        icon="🚨",
    )
    st.stop()

init_date, final_date = st.slider(
    "Date range:",
    min_value=shared_init_date,
    max_value=shared_final_date,
    value=(shared_init_date, shared_final_date),
)

if time_type == "day":
    date_range = to_epidate_range(init_date, final_date)
    max_lag = (final_date - init_date).days // 2
elif time_type == "week":
    date_range = to_epiweek_range(init_date, final_date)
    max_lag = ((final_date - init_date).days // 7) // 2
else:
    st.error(f"Invalid time_type: {time_type}", icon="🚨")
    st.stop()

button_enabled = signal1 != signal2 and geo_type != "dma" and "region" in locals()

if st.button(
    "Fetch Data",
    type="primary",
    disabled=not button_enabled,
    help="Click to fetch and analyze the selected signals",
):
    with st.spinner("Fetching data..."):
        # Store the fetched data in session state
        st.session_state.df1 = fetch_covidcast_data(
            geo_type, region, source1, signal1, date_range[0], date_range[-1], time_type
        )
        st.session_state.df2 = fetch_covidcast_data(
            geo_type, region, source2, signal2, date_range[0], date_range[-1], time_type
        )

    st.divider()

# Only show the lag slider and plot if we have data
if "df1" in st.session_state and "df2" in st.session_state:
    plot_container = st.empty()

    selected_lag = st.slider(
        f"Time lag ({time_type}s)",
        min_value=-max_lag,
        max_value=max_lag,
        value=0,
        help=f"Shift signal 1 ({signal_display1}) forwards or backwards in time",
    )

    # Add the correlation method selection here
    correlation_method = st.radio(
        "Select correlation method:",
        ["Pearson", "Kendall", "Spearman"],
        help="Choose the statistical method for calculating correlation between signals.",
        key="correlation_method"
    ).lower()

    # Show the help text for the selected method
    st.info(get_correlation_method_info(correlation_method))

    # Update plot based on current lag and selected correlation method
    new_fig, new_correlation = update_plot_with_lag(
        st.session_state.df1,
        st.session_state.df2,
        signal_display1,
        signal_display2,
        geo_type,
        region_display,
        selected_lag,
        time_type,
        correlation_method  # Pass the selected method
    )

    with plot_container:
        st.plotly_chart(new_fig, use_container_width=True)

    st.write(
        f"Signal correlation at lag {selected_lag} {time_type}s: **{new_correlation}**"
    )

    st.divider()

    if st.button(
        "Calculate best time lag",
        type="primary",
        help="Calculate the time lag that maximises the correlation between the two signals",
    ):
        with st.spinner(
            "This might take a while (up to ~2mins for the full data range)..."
        ):
            lags_and_correlations = get_lags_and_correlations(
                st.session_state.df1,
                st.session_state.df2,
                cor_by="geo_value",
                max_lag=max_lag,
                method=correlation_method  # Pass the selected method
            )
        best_lag = max(lags_and_correlations, key=lags_and_correlations.get)
        best_correlation = lags_and_correlations[best_lag]
        st.write(f"Best time lag: **{best_lag} {time_type}s**")
        st.write(f"Best correlation: **{best_correlation:.3f}**")

        col1, col2 = st.columns(2, gap="large")
        with col1:
            fig1 = plot_correlation_vs_lag(lags_and_correlations, time_type)
            st.plotly_chart(fig1, use_container_width=True)
            
        with col2:
            fig2 = plot_correlation_distribution(lags_and_correlations)
            st.plotly_chart(fig2, use_container_width=True)
