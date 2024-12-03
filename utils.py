import pandas as pd
from available_signals import names_to_sources

covidcast_metadata = pd.read_csv("covidcast_metadata.csv")


def load_data(source, signal):
    df = pd.read_csv(f"{source}_{signal}.csv")
    return df


def get_signal_geotypes(metadata, displayed_name):
    source, signal = names_to_sources[displayed_name]
    df = metadata[metadata["data_source"] == source]
    df = df[df["signal"] == signal]

    geo_types = list(df["geo_type"])

    return geo_types


def get_shared_geotypes(metadata, displayed_name1, displayed_name2):
    geo_types1 = get_signal_geotypes(metadata, displayed_name1)
    geo_types2 = get_signal_geotypes(metadata, displayed_name2)

    return list(set(geo_types1) & set(geo_types2))


def get_signal_dates(metadata, displayed_name, geo_type, return_time_type=False):
    source, signal = names_to_sources[displayed_name]
    df = metadata[metadata["data_source"] == source]
    df = df[df["signal"] == signal]
    df = df[df["geo_type"] == geo_type]

    init_date = pd.to_datetime(df["min_time"]).item().date()
    final_date = pd.to_datetime(df["max_time"]).item().date()

    if not return_time_type:
        return init_date, final_date

    try:
        time_type = df["time_type"].item()
    except Exception as e:
        print(
            "Currently, the code assumes that each signal has only one reporting frequency ('time_type')."
        )
        raise e

    return init_date, final_date, time_type


def get_shared_dates(metadata, displayed_name1, displayed_name2, geo_type):
    init_date1, final_date1, time_type1 = get_signal_dates(
        metadata, displayed_name1, geo_type, return_time_type=True
    )
    init_date2, final_date2, time_type2 = get_signal_dates(
        metadata, displayed_name2, geo_type, return_time_type=True
    )

    if time_type1 != time_type2:
        raise ValueError

    return max(init_date1, init_date2), min(final_date1, final_date2), time_type1


# init_date, final_date = get_shared_dates(covidcast_metadata, "Confirmed Covid-19 Hospitalizations (7-day avg., per 100k)", "Cases (7-day avg., per 100k)", "state")
# print(init_date, final_date)