import io
import json
import csv
import hashlib
import re
import pandas as pd
import streamlit as st
from collections import Counter


st.set_page_config(
    page_title="AI Data Analysis Studio",
    page_icon="📊",
    layout="wide"
)

if "combined_result_df" not in st.session_state:
    st.session_state["combined_result_df"] = None
if "combined_result_name" not in st.session_state:
    st.session_state["combined_result_name"] = "combined_dataset.csv"
if "combined_result_label" not in st.session_state:
    st.session_state["combined_result_label"] = "Combined"

st.title("📊 AI Data Analysis Studio")

st.write(
    "Upload a dataset to explore its structure, "
    "identify data quality issues, and generate insights."
)

st.caption(
    "Current version: CSV, TSV, TXT, Excel, and JSON support."
)


def read_csv_safely(uploaded_file, separator=None):
    raw_data = uploaded_file.getvalue()

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin1"
    ]

    last_error = None

    for encoding in encodings:
        try:
            text_data = raw_data.decode(encoding)

            if separator is not None:
                sep = separator
            else:
                try:
                    sep = csv.Sniffer().sniff(
                        text_data[:20000],
                        delimiters=",;\t|"
                    ).delimiter
                except csv.Error:
                    sep = ","

            return pd.read_csv(
                io.StringIO(text_data),
                sep=sep,
                low_memory=False
            )

        except (
            UnicodeDecodeError,
            pd.errors.ParserError,
            ValueError
        ) as error:
            last_error = error

    raise ValueError(
        f"Unable to read this delimited text file: {last_error}"
    )


def load_dataset(uploaded_file):
    filename = uploaded_file.name.lower()

    if filename.endswith(".csv"):
        return read_csv_safely(uploaded_file)

    elif filename.endswith(".tsv"):
        return read_csv_safely(
            uploaded_file,
            separator="\t"
        )

    elif filename.endswith(".txt"):
        return read_csv_safely(uploaded_file)

    elif filename.endswith(".xlsx"):
        return pd.read_excel(
            io.BytesIO(uploaded_file.getvalue()),
            engine="openpyxl"
        )

    elif filename.endswith(".xls"):
        return pd.read_excel(
            io.BytesIO(uploaded_file.getvalue())
        )

    elif filename.endswith(".json"):
        raw_text = uploaded_file.getvalue().decode(
            "utf-8-sig"
        )

        try:
            return pd.read_json(io.StringIO(raw_text))
        except ValueError:
            data = json.loads(raw_text)

            if isinstance(data, list):
                return pd.json_normalize(data)

            if isinstance(data, dict):
                return pd.json_normalize(data)

            raise ValueError(
                "The JSON structure cannot be converted to a table."
            )

    elif filename.endswith(".parquet"):
        raise ValueError(
            "Parquet support is temporarily unavailable "
            "because Windows is blocking a required library. "
            "Please use CSV or Excel for now."
        )

    else:
        raise ValueError("Unsupported file format.")


uploaded_file = st.file_uploader(
    "Upload your dataset",
    type=[
        "csv",
        "tsv",
        "txt",
        "xlsx",
        "xls",
        "json"
    ],
    accept_multiple_files=False,
    help="Upload a supported data file to begin analysis."
)


if uploaded_file is not None:

    try:
        with st.spinner("Reading and analysing your dataset..."):
            df = load_dataset(uploaded_file)

        if df.empty:
            st.warning("The uploaded file contains no data rows.")
            st.stop()

        st.success("Dataset loaded successfully!")

        # One evolving primary dataset: approved transformations, append/merge, cleaning,
        # calculated columns, and promoted DAX results become the source for later tools.
        current_dataset_signature = hashlib.sha256(uploaded_file.getvalue()).hexdigest()
        if st.session_state.get("primary_dataset_source") != current_dataset_signature:
            st.session_state["primary_dataset_source"] = current_dataset_signature
            st.session_state["primary_dataset_df"] = df.copy()
            st.session_state["calculated_columns_df"] = df.copy()
            st.session_state["calculated_columns_source"] = current_dataset_signature
            st.session_state["calculated_columns_history"] = []
            st.session_state["transform_df"] = df.copy()
            st.session_state["cleaned_df"] = df.copy()
            st.session_state["transform_history"] = []
            st.session_state["cleaning_applied"] = False
            st.session_state["combined_result_df"] = None
            st.session_state["saved_measures"] = []
        elif isinstance(st.session_state.get("primary_dataset_df"), pd.DataFrame):
            df = st.session_state["primary_dataset_df"].copy()
        else:
            st.session_state["primary_dataset_df"] = df.copy()

        # Keep legacy state names synchronized for existing app components.
        st.session_state["calculated_columns_df"] = df.copy()

        total_rows, total_columns = df.shape

        missing_count = int(df.isna().sum().sum())
        duplicate_count = int(df.duplicated().sum())

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Rows", f"{total_rows:,}")
        col2.metric("Total Columns", f"{total_columns:,}")
        col3.metric("Missing Values", f"{missing_count:,}")
        col4.metric("Duplicate Rows", f"{duplicate_count:,}")

        # Apply conversational-builder selections before dashboard widgets are created.
        _pending_conv_config = st.session_state.pop("pending_conv_advisor_config", None)
        if isinstance(_pending_conv_config, dict):
            st.session_state["advisor_title"] = _pending_conv_config.get("title", "Data Insights Dashboard")
            st.session_state["advisor_subtitle"] = _pending_conv_config.get("subtitle", "Key metrics, trends, and comparisons from your data")
            st.session_state["advisor_kpi_config"] = _pending_conv_config.get("kpis", [])
            st.session_state["advisor_kpi_count"] = max(1, min(8, len(_pending_conv_config.get("kpis", []))))
            st.session_state["advisor_chart_config"] = _pending_conv_config.get("charts", [])
            st.session_state["advisor_chart_count"] = max(1, min(8, len(_pending_conv_config.get("charts", []))))
            st.session_state["advisor_filter_cols"] = _pending_conv_config.get("filters", [])
            st.session_state["conv_dashboard_recommendation"] = _pending_conv_config

        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "Dataset Preview",
            "Data Quality",
            "Statistics",
            "Cleaning & Export",
            "Measures Engine",
            "✨ AI Dashboard Advisor",
            "💬 Ask Your Data",
            "🗣️ Conversational Builder (Optional)"
        ])

        with tab6:
            st.subheader("✨ AI Dashboard Advisor")
            st.write("Design a dashboard from the current primary dataset, including approved transformations, append/merge results, cleaned data, and calculated columns. Saved measures are available to the analysis workflow.")
            st.info(f"Primary dataset: {st.session_state.get('primary_dataset_name', 'Current working dataset')} · {len(df):,} rows × {len(df.columns):,} columns. Approved transformations and calculated columns are included.")

            dashboard_themes = {
                "Ocean Professional": {"bg":"#EDF6FA","panel":"#FFFFFF","primary":"#075985","secondary":"#0891B2","accent":"#14B8A6","text":"#163247","muted":"#5B7180","series":["#075985","#0891B2","#14B8A6","#F59E0B","#6366F1","#E76F51"]},
                "Indigo Luxe": {"bg":"#F4F1FC","panel":"#FFFFFF","primary":"#3730A3","secondary":"#7C3AED","accent":"#C4B5FD","text":"#25204A","muted":"#6B6487","series":["#4338CA","#7C3AED","#A78BFA","#0D9488","#F59E0B","#EC4899"]},
                "Emerald Finance": {"bg":"#F0F7F0","panel":"#FFFFFF","primary":"#166534","secondary":"#0F766E","accent":"#84CC16","text":"#183B2A","muted":"#617767","series":["#166534","#16A34A","#84CC16","#0F766E","#D97706","#64748B"]},
                "Sunset Fusion": {"bg":"#FFF2F5","panel":"#FFFFFF","primary":"#9D174D","secondary":"#7C3AED","accent":"#FB7185","text":"#45152F","muted":"#80566A","series":["#BE185D","#DB2777","#FB7185","#7C3AED","#F59E0B","#0891B2"]},
                "Arctic Blue": {"bg":"#EFF8FF","panel":"#FFFFFF","primary":"#1D4ED8","secondary":"#0284C7","accent":"#06B6D4","text":"#17324D","muted":"#58728A","series":["#1D4ED8","#0284C7","#06B6D4","#10B981","#F59E0B","#8B5CF6"]},
                "Midnight Neon": {"bg":"#111827","panel":"#1F2937","primary":"#A5B4FC","secondary":"#22D3EE","accent":"#34D399","text":"#F3F4F6","muted":"#CBD5E1","series":["#818CF8","#22D3EE","#34D399","#FBBF24","#F472B6","#A78BFA"]},
                "Ruby & Champagne": {"bg":"#FAF5F2","panel":"#FFFFFF","primary":"#881337","secondary":"#BE123C","accent":"#D4A373","text":"#3F1725","muted":"#75616B","series":["#9F1239","#E11D48","#D4A373","#0F766E","#6366F1","#F59E0B"]},
                "Graphite & Lime": {"bg":"#F3F4F1","panel":"#FFFFFF","primary":"#27272A","secondary":"#52525B","accent":"#84CC16","text":"#27272A","muted":"#66666D","series":["#27272A","#84CC16","#0D9488","#3B82F6","#F97316","#A855F7"]}
            }
            def _pretty_field_name(value):
                """Turn raw dataframe field names into readable display labels."""
                text_value = re.sub(r"[_\-]+", " ", str(value)).strip()
                text_value = re.sub(r"([a-z])([A-Z])", r"\1 \2", text_value)
                text_value = re.sub(r"\s+", " ", text_value)
                return text_value[:1].upper() + text_value[1:] if text_value else "Metric"

            def _suggest_dashboard_title(columns):
                names = [str(c).lower() for c in columns]
                if any("sales" in c or "revenue" in c or "income" in c for c in names):
                    if any("region" in c or "country" in c or "state" in c for c in names):
                        return "Sales & Regional Performance"
                    return "Sales Performance Overview"
                if any("profit" in c or "margin" in c for c in names):
                    return "Profitability Overview"
                if any("customer" in c or "client" in c for c in names):
                    return "Customer Insights Dashboard"
                if any("order" in c or "transaction" in c for c in names):
                    return "Order & Transaction Analysis"
                if any("delivery" in c or "shipping" in c or "ship" in c for c in names):
                    return "Delivery Performance Overview"
                return "Data Insights Dashboard"

            def _suggest_theme(columns):
                names = " ".join(str(c).lower() for c in columns)
                if any(term in names for term in ("profit", "revenue", "income", "cost", "finance", "sales")):
                    return "Emerald Finance"
                if any(term in names for term in ("customer", "product", "retail", "category", "order")):
                    return "Ocean Professional"
                if any(term in names for term in ("health", "patient", "survey", "rating", "feedback")):
                    return "Indigo Luxe"
                if any(term in names for term in ("delivery", "shipping", "logistics", "route", "latitude", "longitude")):
                    return "Arctic Blue"
                return "Graphite & Lime"

            def _suggest_kpi_label(column, aggregation):
                field = _pretty_field_name(column)
                low = str(column).lower()
                if aggregation == "Distinct Count":
                    noun = field
                    for suffix in (" ID", " Id", " Code", " Number"):
                        if noun.endswith(suffix):
                            noun = noun[:-len(suffix)]
                    return "Unique " + noun + ("s" if not noun.lower().endswith("s") else "")
                if aggregation == "Count":
                    return "Record Count" if any(t in low for t in ("id", "code", "number")) else field + " Count"
                if aggregation == "Sum":
                    return "Total " + field
                if aggregation == "Average":
                    return "Average " + field
                if aggregation == "Minimum":
                    return "Minimum " + field
                if aggregation == "Maximum":
                    return "Maximum " + field
                if aggregation == "Median":
                    return "Median " + field
                return field

            def _format_dashboard_value(value, column_name=""):
                if value is None or pd.isna(value):
                    return "—"
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    return str(value)
                name = str(column_name).lower()
                if any(t in name for t in ("percent", "percentage", "rate", "margin")):
                    return f"{number:,.1f}%"
                if any(t in name for t in ("revenue", "income", "sales", "profit", "price", "cost", "amount", "spend")):
                    absolute = abs(number)
                    if absolute >= 100000:
                        return f"₹{number/100000:,.2f}L"
                    if absolute >= 1000:
                        return f"₹{number/1000:,.1f}K"
                    return f"₹{number:,.2f}".rstrip("0").rstrip(".")
                if abs(number) >= 1000000:
                    return f"{number/1000000:,.2f}M"
                if abs(number) >= 1000:
                    return f"{number/1000:,.1f}K"
                return f"{number:,.2f}".rstrip("0").rstrip(".")

            # Give the first dashboard view a dataset-aware title and theme. Users can
            # change either later; no column names or values are invented.
            st.session_state.setdefault("advisor_title", _suggest_dashboard_title(df.columns))
            st.session_state.setdefault("advisor_subtitle", "Key metrics, trends, and comparisons from your data")
            st.session_state.setdefault("advisor_theme_name", _suggest_theme(df.columns))

            # Smart Data Understanding: distinguish measures from IDs/contact numbers,
            # and identify date/time and categorical dimensions before recommending KPIs.
            _raw_numeric_cols = df.select_dtypes(include="number").columns.tolist()
            _date_like_names = ("date", "time", "timestamp", "month", "year", "day")
            _identifier_tokens = ("id", "identifier", "code", "phone", "mobile", "telephone", "postal", "postcode", "zip")

            def _is_identifier_column(column_name, series=None):
                _name = re.sub(r"[^a-z0-9]+", " ", str(column_name).lower()).strip()
                _parts = _name.split()
                if any(token in _name for token in ("phone", "mobile", "telephone", "postal", "postcode", "zip code", "customer id", "product id", "order id")):
                    return True
                if _name in {"id", "identifier", "code", "order number", "customer number", "product number"}:
                    return True
                if _parts and (_parts[-1] in {"id", "code", "identifier"} or (_parts[-1] == "number" and any(t in _name for t in ["order", "customer", "product", "account"]))):
                    return True
                if series is not None and pd.api.types.is_numeric_dtype(series) and len(series.dropna()) > 0:
                    _non_null = series.dropna()
                    _unique_ratio = _non_null.nunique() / max(1, len(_non_null))
                    if _unique_ratio > 0.95 and any(t in _name for t in ["key", "ref", "number"]):
                        return True
                return False

            identifier_cols = [c for c in df.columns if _is_identifier_column(c, df[c])]
            date_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
            for _col in df.columns:
                if _col not in date_cols and any(t in str(_col).lower() for t in _date_like_names):
                    _parsed = pd.to_datetime(df[_col], errors="coerce", dayfirst=True)
                    if _parsed.notna().sum() >= max(3, int(len(df) * .5)):
                        date_cols.append(_col)

            numeric_cols = [c for c in _raw_numeric_cols if c not in identifier_cols]
            # IDs remain usable as dimensions/slicers, but are not offered as numeric KPIs.
            categorical_cols = [c for c in df.columns if c not in numeric_cols and c not in date_cols]

            _column_role_rows = []
            for _col in df.columns:
                _series = df[_col]
                if _col in date_cols:
                    _role, _reason, _use = "Date / time", "Column name or values look like dates/timestamps.", "Trend charts, date filters, delivery-duration analysis"
                elif _col in identifier_cols:
                    _role, _reason, _use = "Identifier / dimension", "IDs and contact numbers identify records; averages or sums are usually misleading.", "Filters, grouping, distinct counts"
                elif _col in numeric_cols:
                    _role, _reason, _use = "Numeric measure", "Numeric values can support meaningful aggregations after validation.", "Sum, average, minimum, maximum, distributions"
                elif _series.nunique(dropna=True) <= max(20, int(len(_series.dropna()) * 0.05)):
                    _role, _reason, _use = "Category", "Repeated labels or a limited number of unique values.", "Breakdowns, comparisons, slicers"
                else:
                    _role, _reason, _use = "Text / dimension", "Values are best treated as labels rather than numeric measures.", "Search, grouping, filters"
                _column_role_rows.append({"Column": str(_col), "Detected role": _role, "Reason": _reason, "Suggested use": _use,
                                          "Missing values": int(_series.isna().sum()), "Unique values": int(_series.nunique(dropna=True))})

            with st.expander("🧠 Smart Data Understanding · column roles and KPI suitability", expanded=True):
                st.write("The app checks column names, data types, date-like values, and uniqueness before recommending dashboard metrics. Identifier columns are kept available for filtering and grouping, but excluded from average/sum KPI suggestions.")
                st.dataframe(pd.DataFrame(_column_role_rows), use_container_width=True, hide_index=True)
                if numeric_cols:
                    st.success("Suggested numeric measures: " + ", ".join(map(str, numeric_cols)))
                else:
                    st.warning("No clear numeric measures were detected. The dashboard can still analyse record counts and categories.")

            # One-click automatic dashboard setup. It configures sensible KPIs and
            # chart panels from the current working dataset, then reruns so the
            # existing editable dashboard builder renders those selections.
            auto_col1, auto_col2 = st.columns([1, 2])
            with auto_col1:
                auto_generate = st.button("✨ Generate dashboard automatically", type="primary", key="advisor_auto_generate")
            with auto_col2:
                st.caption("Automatically choose KPI calculations, chart types, axes, values, legends, and geographic fields from detected data types. You can edit every choice afterward.")
            if auto_generate:
                if not numeric_cols and not categorical_cols and not date_cols:
                    st.warning("This dataset does not contain usable columns for automatic dashboard creation.")
                else:
                    priority_numeric = sorted(
                        numeric_cols,
                        key=lambda c: (0 if any(term in str(c).lower() for term in ["sales", "revenue", "profit", "amount", "total", "price", "cost", "quantity", "duration"]) else 1, str(c).lower())
                    )
                    chosen_kpis = priority_numeric[:min(4, len(priority_numeric))]
                    _kpi_suggestions = []
                    for c in chosen_kpis:
                        _name = str(c).lower()
                        if any(term in _name for term in ["sales", "revenue", "profit", "amount", "total", "price", "cost", "income", "quantity", "units"]):
                            _agg = "Sum"
                        else:
                            _agg = "Average"
                        _label = _suggest_kpi_label(c, _agg)
                        _kpi_suggestions.append({"column": c, "aggregation": _agg, "label": _label})
                    st.session_state["advisor_kpi_config"] = _kpi_suggestions
                    x_category = categorical_cols[0] if categorical_cols else (date_cols[0] if date_cols else None)
                    second_category = next((c for c in categorical_cols if c != x_category), None)
                    chart_defs = []
                    # Assign fields by chart purpose: dimensions for categories, measures for values.
                    if x_category and numeric_cols:
                        chart_defs.append({"type": "Bar comparison", "title": f"{numeric_cols[0]} by {x_category}", "position": 1, "x": x_category, "y": numeric_cols[0], "aggregation": "Sum", "legend": None})
                    elif x_category:
                        chart_defs.append({"type": "Bar comparison", "title": f"Records by {x_category}", "position": 1, "x": x_category, "y": "(Count rows)", "aggregation": "Count", "legend": None})
                    if date_cols and numeric_cols:
                        chart_defs.append({"type": "Line trend", "title": f"{numeric_cols[0]} over time", "position": len(chart_defs) + 1, "x": date_cols[0], "y": numeric_cols[0], "aggregation": "Sum", "legend": None})
                    if second_category and numeric_cols:
                        chart_defs.append({"type": "Donut share", "title": f"Distribution by {second_category}", "position": len(chart_defs) + 1, "x": second_category, "y": numeric_cols[0], "aggregation": "Sum", "legend": None})
                    if x_category and second_category and numeric_cols:
                        chart_defs.append({"type": "Stacked bar", "title": f"{numeric_cols[0]} by {x_category} and {second_category}", "position": len(chart_defs) + 1, "x": x_category, "y": numeric_cols[0], "aggregation": "Sum", "legend": second_category})
                    if len(numeric_cols) >= 2:
                        chart_defs.append({"type": "Scatter relationship", "title": f"{numeric_cols[0]} vs {numeric_cols[1]}", "position": len(chart_defs) + 1, "x": numeric_cols[0], "y": numeric_cols[1], "aggregation": "Sum", "legend": None})
                    # Include a map only when recognizable coordinate fields exist.
                    _geo_lower = {str(c).lower().strip(): c for c in df.columns}
                    _auto_lat = next((c for k,c in _geo_lower.items() if k in {"lat", "latitude"} or "latitude" in k), None)
                    _auto_lon = next((c for k,c in _geo_lower.items() if k in {"lon", "lng", "long", "longitude"} or "longitude" in k), None)
                    if _auto_lat and _auto_lon:
                        chart_defs.append({"type": "Map", "title": "Geographic distribution", "position": len(chart_defs) + 1, "x": x_category, "y": numeric_cols[0] if numeric_cols else "(Count rows)", "aggregation": "Sum", "legend": None, "latitude": _auto_lat, "longitude": _auto_lon})
                    chart_defs.append({"type": "Data table", "title": "Dataset overview", "position": len(chart_defs) + 1, "x": x_category, "y": numeric_cols[0] if numeric_cols else "(Count rows)", "aggregation": "Sum", "legend": None})
                    chart_defs = chart_defs[:6]
                    for idx, chart in enumerate(chart_defs, 1):
                        chart["position"] = idx
                    st.session_state["advisor_chart_config"] = chart_defs
                    st.session_state["advisor_chart_count"] = len(chart_defs)
                    st.session_state["advisor_kpi_count"] = max(1, len(chosen_kpis))
                    _col_names_lower = [str(c).lower() for c in df.columns]
                    if any("order" in c for c in _col_names_lower) and any("region" in c for c in _col_names_lower):
                        _auto_title = "Order Analysis by Region"
                    elif any("delivery" in c or "ship" in c for c in _col_names_lower) and any("order" in c for c in _col_names_lower):
                        _auto_title = "Order & Delivery Analysis"
                    elif any("sales" in c or "revenue" in c for c in _col_names_lower):
                        _auto_title = "Sales Performance Analysis"
                    elif any("customer" in c for c in _col_names_lower):
                        _auto_title = "Customer Analysis Dashboard"
                    else:
                        _auto_title = "Dataset Analysis Dashboard"
                    st.session_state["advisor_title"] = _auto_title
                    st.session_state["advisor_subtitle"] = "Key metrics, trends, and comparisons from your data"
                    st.session_state["advisor_theme_name"] = _suggest_theme(df.columns)
                    if categorical_cols:
                        st.session_state["advisor_filter_cols"] = categorical_cols[:min(2, len(categorical_cols))]
                    st.success("Dashboard setup generated. Review and edit the KPIs, charts, and slicers below.")
                    st.rerun()
            try:
                import plotly.express as px
                import plotly.graph_objects as go
                _plotly_ok = True
            except Exception:
                _plotly_ok = False

            st.markdown("### 1 · Dashboard design")
            design_left, design_mid, design_right = st.columns([1.4, 1, 1])
            with design_left:
                dash_title = st.text_input("Dashboard title", value=st.session_state.get("advisor_title", _suggest_dashboard_title(df.columns)), key="advisor_title")
                dash_subtitle = st.text_input("Subtitle", value=st.session_state.get("advisor_subtitle", "Key metrics, trends, and comparisons from your data"), key="advisor_subtitle")
            with design_mid:
                theme_name = st.selectbox("Colour theme", list(dashboard_themes), key="advisor_theme_name")
                layout_name = st.selectbox("Dashboard layout", ["Executive · 2 columns", "Analytics · 3 columns", "Wide · one chart per row"], key="advisor_layout")
            with design_right:
                _kpi_candidates = list(dict.fromkeys(numeric_cols + identifier_cols))
                kpi_count = st.slider("KPI cards", 1, min(8, max(1, len(_kpi_candidates))), min(4, max(1, len(_kpi_candidates))), key="advisor_kpi_count")
                chart_count = st.slider("Visualization panels", 1, 8, int(st.session_state.get("advisor_chart_count", 4)), key="advisor_chart_count")
                show_insights = st.checkbox("Show automatic insights", value=True, key="advisor_show_insights")
            theme = dict(dashboard_themes[theme_name])
            with st.expander("🎨 Customize dashboard appearance", expanded=False):
                _custom_bg = st.color_picker("Dashboard background", theme["bg"], key="advisor_custom_bg")
                _custom_panel = st.color_picker("Card and chart background", theme["panel"], key="advisor_custom_panel")
                _custom_primary = st.color_picker("Primary accent", theme["primary"], key="advisor_custom_primary")
                _custom_accent = st.color_picker("Secondary accent", theme["accent"], key="advisor_custom_accent")
                _dark_custom = sum(int(_custom_bg[i:i+2], 16) for i in (1,3,5)) / 3 < 120
                _custom_text = "#F3F4F6" if _dark_custom else "#1F2937"
                theme.update({"bg":_custom_bg,"panel":_custom_panel,"primary":_custom_primary,"accent":_custom_accent,"text":_custom_text})
            palette = theme["series"]
            # High-contrast metric styling. Explicitly style nested Streamlit label/value
            # elements because Streamlit's theme CSS can otherwise make labels nearly invisible.
            st.markdown(
                "<style>"
                "div[data-testid='stAppViewContainer'],div[data-testid='stMain']{background-color:#0e1117 !important;}"
                "div[data-testid='stMetric']{background:" + theme["panel"] + ";"
                "border:1px solid " + theme["accent"] + ";border-top:4px solid " + theme["primary"] + ";"
                "padding:14px 16px;border-radius:13px;min-height:104px;}"
                "div[data-testid='stMetric'] label,div[data-testid='stMetricLabel'],"
                "div[data-testid='stMetricLabel'] p,div[data-testid='stMetricLabel'] div{"
                "color:" + theme["text"] + " !important;opacity:1 !important;font-weight:700 !important;}"
                "div[data-testid='stMetricValue'],div[data-testid='stMetricValue'] div,"
                "div[data-testid='stMetricValue'] > div{color:" + theme["primary"] + " !important;"
                "opacity:1 !important;font-weight:800 !important;}"
                "div[data-testid='stPlotlyChart']{background:" + theme["panel"] + ";"
                "border:1px solid " + theme["accent"] + ";border-radius:13px;padding:7px;}"
                "</style>",
                unsafe_allow_html=True
            )
            st.markdown("<div style='background:linear-gradient(115deg,"+theme["primary"]+","+theme["secondary"]+");padding:22px 26px;border-radius:17px;color:white;margin:4px 0 18px'><div style='font-size:11px;letter-spacing:2px;opacity:.85'>AI DATA ANALYSIS STUDIO · INTERACTIVE REPORT</div><div style='font-size:30px;font-weight:800;line-height:1.2;margin:7px 0'>"+str(dash_title).replace("<","&lt;").replace(">","&gt;")+"</div><div style='font-size:14px;opacity:.92'>"+str(dash_subtitle).replace("<","&lt;").replace(">","&gt;")+"</div><div style='font-size:12px;opacity:.8;margin-top:10px'>"+theme_name+" · "+f"{len(df):,}"+" rows · "+str(len(df.columns))+" fields</div></div>", unsafe_allow_html=True)

            st.markdown("### 2 · Dashboard slicers")
            filter_candidates = [c for c in categorical_cols if 1 < df[c].nunique(dropna=True) <= 250]
            filter_cols = st.multiselect("Choose fields to use as slicers", filter_candidates, default=st.session_state.get("advisor_filter_cols", []) if all(c in filter_candidates for c in st.session_state.get("advisor_filter_cols", [])) else [], key="advisor_filter_cols")
            dashboard_df = df.copy()
            if filter_cols:
                fcols = st.columns(min(4, len(filter_cols)))
                for i, col in enumerate(filter_cols):
                    choices = sorted(dashboard_df[col].dropna().astype(str).unique().tolist())
                    chosen = fcols[i % len(fcols)].multiselect(col, choices, default=choices, key="advisor_slicer_"+str(col))
                    dashboard_df = dashboard_df[dashboard_df[col].isna() | dashboard_df[col].astype(str).isin(chosen)]
            if date_cols:
                with st.expander("Optional date range slicer"):
                    date_filter = st.selectbox("Date field", ["(None)"] + date_cols, key="advisor_date_filter")
                    if date_filter != "(None)":
                        parsed_dates = pd.to_datetime(dashboard_df[date_filter], errors="coerce", dayfirst=True).dropna()
                        if not parsed_dates.empty:
                            lo, hi = parsed_dates.min().date(), parsed_dates.max().date()
                            date_range = st.date_input("Date range", value=(lo, hi), min_value=lo, max_value=hi, key="advisor_date_range")
                            if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
                                dts = pd.to_datetime(dashboard_df[date_filter], errors="coerce")
                                dashboard_df = dashboard_df[dts.dt.date.between(date_range[0], date_range[1])]
            st.caption(f"{len(dashboard_df):,} of {len(df):,} rows currently included. Slicers apply to all dashboard panels.")

            st.markdown("### 3 · Configure KPI cards")
            if _kpi_candidates:
                kpi_config = []
                old_kpis = st.session_state.get("advisor_kpi_config", [])
                for i in range(kpi_count):
                    defaults = old_kpis[i] if i < len(old_kpis) else {}
                    with st.expander(f"KPI card {i+1}", expanded=(i < min(4, kpi_count))):
                        kc1, kc2, kc3 = st.columns([1.3, 1, 1.2])
                        metric_col = kc1.selectbox("Column", _kpi_candidates, index=_kpi_candidates.index(defaults.get("column")) if defaults.get("column") in _kpi_candidates else min(i, len(_kpi_candidates)-1), key=f"advisor_kpi_col_{i}")
                        _numeric_metric = metric_col in numeric_cols
                        agg_options = (["Sum", "Average", "Count", "Distinct Count", "Minimum", "Maximum", "Median"] if _numeric_metric else ["Count", "Distinct Count"])
                        _default_agg = defaults.get("aggregation")
                        if _default_agg not in agg_options:
                            _default_agg = "Sum" if _numeric_metric and any(x in str(metric_col).lower() for x in ["sales","revenue","profit","amount","cost","income","total","quantity"]) else ("Average" if _numeric_metric else "Distinct Count")
                        agg = kc2.selectbox("Calculation", agg_options, index=agg_options.index(_default_agg), key=f"advisor_kpi_agg_{i}")
                        label = kc3.text_input("Card label", value=defaults.get("label") or _suggest_kpi_label(metric_col, agg), key=f"advisor_kpi_label_{i}")
                        kpi_config.append({"column":metric_col,"aggregation":agg,"label":label})
                st.session_state["advisor_kpi_config"] = kpi_config
                kcols = st.columns(min(4, len(kpi_config)))
                for i, item in enumerate(kpi_config):
                    _series = dashboard_df[item["column"]]
                    ag = item["aggregation"]
                    if ag == "Distinct Count":
                        value = int(_series.nunique(dropna=True))
                    elif ag == "Count" and item["column"] not in numeric_cols:
                        value = int(_series.count())
                    else:
                        vals = pd.to_numeric(_series, errors="coerce").dropna()
                        value = {"Sum":vals.sum,"Average":vals.mean,"Count":vals.count,"Minimum":vals.min,"Maximum":vals.max,"Median":vals.median}[ag]() if len(vals) and ag in {"Sum", "Average", "Count", "Minimum", "Maximum", "Median"} else float("nan")
                    fmt = _format_dashboard_value(value, item["column"])
                    kcols[i % len(kcols)].metric(item["label"] or _suggest_kpi_label(item["column"], ag), fmt)
                _saved_dashboard_measures = st.session_state.get("saved_measures", [])
                if _saved_dashboard_measures:
                    st.markdown("#### Saved Measures Engine KPIs")
                    st.caption("These saved measure values are included from Measures Engine. Review them after changing the primary dataset.")
                    _measure_cols = st.columns(min(4, len(_saved_dashboard_measures)))
                    for _mi, _measure in enumerate(_saved_dashboard_measures):
                        _mv = _measure.get("value")
                        _mf = f"{_mv:,.2f}" if isinstance(_mv, (int, float)) and pd.notna(_mv) else str(_mv)
                        if _mf.endswith(".00"):
                            _mf = _mf[:-3]
                        _measure_cols[_mi % len(_measure_cols)].metric(str(_measure.get("name", "Saved measure")), _mf)
            else:
                kpi_config = []
                st.warning("No suitable KPI fields were found. The dashboard can still show category counts and data tables.")

            st.markdown("### 4 · Build and arrange visualization panels")
            st.caption("Each panel is independently configurable. Change its chart type, title, fields, and order; turn panels off by reducing the panel count.")
            chart_types = ["Bar comparison", "Column comparison", "Line trend", "Area trend", "Donut share", "Pie share", "Stacked bar", "Stacked column", "Scatter relationship", "Histogram", "Box plot", "Treemap", "Data table", "Map"]
            chart_configs = []
            previous = st.session_state.get("advisor_chart_config", [])
            for i in range(chart_count):
                old = previous[i] if i < len(previous) else {}
                default_type = old.get("type", ["Bar comparison", "Donut share", "Line trend", "Data table"][i % 4])
                with st.expander(f"Panel {i+1} · {old.get('title', default_type)}", expanded=(i < 2)):
                    a,b,c = st.columns([1,1,1])
                    typ = a.selectbox("Visualization", chart_types, index=chart_types.index(default_type) if default_type in chart_types else 0, key=f"advisor_panel_type_{i}")
                    _default_chart_title = old.get("title") or (f"{_pretty_field_name(old.get('y'))} by {_pretty_field_name(old.get('x'))}" if old.get("y") and old.get("x") else {"Line trend":"Trend over time","Area trend":"Trend over time","Donut share":"Category share","Pie share":"Category share","Scatter relationship":"Measure relationship","Histogram":"Value distribution","Box plot":"Distribution and outliers","Treemap":"Category breakdown","Data table":"Dataset details","Map":"Geographic distribution"}.get(typ, f"Category comparison {i+1}"))
                    title = b.text_input("Panel title", value=_default_chart_title, key=f"advisor_panel_title_{i}")
                    order = c.number_input("Position", min_value=1, max_value=chart_count, value=min(chart_count, int(old.get("position", i+1))), key=f"advisor_panel_position_{i}")
                    if typ == "Scatter relationship":
                        x_candidates = numeric_cols
                    elif typ in ["Line trend", "Area trend"]:
                        x_candidates = date_cols + categorical_cols + numeric_cols
                    elif typ == "Map":
                        x_candidates = categorical_cols + date_cols
                    else:
                        x_candidates = categorical_cols + date_cols + numeric_cols
                    preferred_x = date_cols[0] if typ in ["Line trend", "Area trend"] and date_cols else (numeric_cols[0] if typ == "Scatter relationship" and numeric_cols else (categorical_cols[0] if categorical_cols else (date_cols[0] if date_cols else (numeric_cols[0] if numeric_cols else None))))
                    x_default = old.get("x") if old.get("x") in x_candidates else preferred_x
                    val_default = old.get("y") if old.get("y") in numeric_cols else (numeric_cols[min(i, len(numeric_cols)-1)] if numeric_cols else None)
                    xcol = st.selectbox("Category / X-axis field", x_candidates, index=x_candidates.index(x_default) if x_default in x_candidates else 0, key=f"advisor_panel_x_{i}") if x_candidates else None
                    ycol = st.selectbox("Measure / Y-axis / Values", ["(Count rows)"]+numeric_cols, index=(numeric_cols.index(val_default)+1 if val_default in numeric_cols else 0), key=f"advisor_panel_y_{i}") if numeric_cols else "(Count rows)"
                    legend_candidates = [c for c in categorical_cols if c != xcol]
                    legend_default = old.get("legend") if old.get("legend") in legend_candidates else (legend_candidates[0] if typ in ["Stacked bar", "Stacked column"] and legend_candidates else None)
                    legend_col = st.selectbox("Legend / split by (optional)", ["(None)"] + legend_candidates, index=(legend_candidates.index(legend_default)+1 if legend_default in legend_candidates else 0), key=f"advisor_panel_legend_{i}")
                    geo_cols = list(df.columns)
                    _geo_low = {str(c).lower().strip(): c for c in geo_cols}
                    _lat_opts = [c for c in geo_cols if str(c).lower().strip() in {"lat", "latitude"} or "latitude" in str(c).lower()]
                    _lon_opts = [c for c in geo_cols if str(c).lower().strip() in {"lon", "lng", "long", "longitude"} or "longitude" in str(c).lower()]
                    latitude = longitude = None
                    if typ == "Map":
                        gl1, gl2 = st.columns(2)
                        lat_default = old.get("latitude") if old.get("latitude") in _lat_opts else (_lat_opts[0] if _lat_opts else None)
                        lon_default = old.get("longitude") if old.get("longitude") in _lon_opts else (_lon_opts[0] if _lon_opts else None)
                        latitude = gl1.selectbox("Latitude field", ["(None)"] + _lat_opts, index=(_lat_opts.index(lat_default)+1 if lat_default in _lat_opts else 0), key=f"advisor_panel_lat_{i}")
                        longitude = gl2.selectbox("Longitude field", ["(None)"] + _lon_opts, index=(_lon_opts.index(lon_default)+1 if lon_default in _lon_opts else 0), key=f"advisor_panel_lon_{i}")
                        latitude = None if latitude == "(None)" else latitude
                        longitude = None if longitude == "(None)" else longitude
                    location_col = None
                    if typ == "Map":
                        _location_opts = [c for c in categorical_cols if c not in {xcol, legend_col}]
                        _location_default = old.get("location") if old.get("location") in _location_opts else (_location_opts[0] if _location_opts else None)
                        _location_choice = st.selectbox("Location field (optional)", ["(None)"] + _location_opts, index=(_location_opts.index(_location_default)+1 if _location_default in _location_opts else 0), key=f"advisor_panel_location_{i}")
                        location_col = None if _location_choice == "(None)" else _location_choice
                    details_col = None
                    if typ == "Treemap":
                        _details_opts = [c for c in categorical_cols if c != xcol]
                        _details_default = old.get("details") if old.get("details") in _details_opts else None
                        _details_choice = st.selectbox("Details / subcategory (optional)", ["(None)"] + _details_opts, index=(_details_opts.index(_details_default)+1 if _details_default in _details_opts else 0), key=f"advisor_panel_details_{i}")
                        details_col = None if _details_choice == "(None)" else _details_choice
                    agg = st.selectbox("Aggregation", ["Sum", "Average", "Count", "Minimum", "Maximum"], index=["Sum", "Average", "Count", "Minimum", "Maximum"].index(old.get("aggregation", "Sum")) if old.get("aggregation", "Sum") in ["Sum", "Average", "Count", "Minimum", "Maximum"] else 0, key=f"advisor_panel_agg_{i}")
                    chart_configs.append({"type":typ,"title":title,"position":int(order),"x":xcol,"y":ycol,"aggregation":agg,"legend":None if legend_col == "(None)" else legend_col,"latitude":latitude,"longitude":longitude,"location":location_col,"details":details_col})
            st.session_state["advisor_chart_config"] = chart_configs

            st.markdown("### 5 · Your dashboard")
            st.markdown("<div style='border-radius:12px;padding:10px 14px;background:"+theme["panel"]+";border-left:5px solid "+theme["accent"]+";color:"+theme["text"]+";margin-bottom:12px'><b>Live dashboard preview</b> · all panels below respond to the slicers above.</div>", unsafe_allow_html=True)
            sorted_configs = sorted(chart_configs, key=lambda z: z["position"])
            ncols = 1 if layout_name.startswith("Wide") else (3 if layout_name.startswith("Analytics") else 2)
            for row_start in range(0, len(sorted_configs), ncols):
                chart_columns = st.columns(ncols)
                for j, cfg in enumerate(sorted_configs[row_start:row_start+ncols]):
                    with chart_columns[j]:
                        st.markdown("<div style='font-weight:750;color:"+theme["primary"]+";font-size:16px;padding:8px 0 2px'>"+str(cfg["title"]).replace("<","&lt;").replace(">","&gt;")+"</div>", unsafe_allow_html=True)
                        typ, xcol, ycol = cfg["type"], cfg["x"], cfg["y"]
                        valcol = ycol if ycol and ycol != "(Count rows)" else None
                        try:
                            if typ == "Map":
                                low = {str(c).lower():c for c in dashboard_df.columns}
                                lat = cfg.get("latitude") or next((low[k] for k in low if k in ["lat","latitude"] or "latitude" in k), None)
                                lon = cfg.get("longitude") or next((low[k] for k in low if k in ["lon","lng","long","longitude"] or "longitude" in k), None)
                                if lat and lon:
                                    _map_cols = [lat, lon] + ([valcol] if valcol and valcol in dashboard_df.columns else []) + ([cfg.get("legend")] if cfg.get("legend") in dashboard_df.columns else [])
                                    m = dashboard_df[list(dict.fromkeys(_map_cols))].copy()
                                    m[lat]=pd.to_numeric(m[lat],errors="coerce"); m[lon]=pd.to_numeric(m[lon],errors="coerce"); m=m.dropna(subset=[lat,lon]); m=m[m[lat].between(-90,90)&m[lon].between(-180,180)].head(5000)
                                    if not m.empty and _plotly_ok:
                                        _size_col = valcol if valcol in m.columns else None
                                        if _size_col:
                                            m[_size_col]=pd.to_numeric(m[_size_col],errors="coerce").fillna(0).clip(lower=0)
                                        _color_col = cfg.get("legend") if cfg.get("legend") in m.columns else (_size_col if _size_col else None)
                                        fig = px.scatter_geo(m, lat=lat, lon=lon, size=_size_col, color=_color_col, hover_name=cfg.get("location") if cfg.get("location") in m.columns else None, color_discrete_sequence=palette, title=cfg["title"])
                                        fig.update_layout(template="plotly_dark" if theme_name=="Midnight Neon" else "plotly_white",paper_bgcolor=theme["panel"],font_color=theme["text"],margin=dict(l=10,r=10,t=45,b=10),height=330)
                                        st.plotly_chart(fig,use_container_width=True,key=f"advisor_render_{row_start}_{j}")
                                    elif not m.empty:
                                        st.map(m.rename(columns={lat:"latitude",lon:"longitude"}), latitude="latitude", longitude="longitude")
                                    else: st.info("No valid coordinates after filters.")
                                elif cfg.get("location") in dashboard_df.columns and _plotly_ok:
                                    _loc = dashboard_df[cfg["location"]].fillna("(Missing)").astype(str).value_counts().head(50).rename_axis("Location").reset_index(name="Records")
                                    st.bar_chart(_loc.set_index("Location")["Records"])
                                    st.caption("No latitude/longitude fields found; showing records by location instead.")
                                else: st.info("Map needs latitude and longitude columns, or a usable location field.")
                            elif typ == "Data table":
                                st.dataframe(dashboard_df.head(1000), use_container_width=True, height=300)
                            elif typ in ["Histogram", "Box plot"]:
                                target = valcol or (numeric_cols[0] if numeric_cols else None)
                                if target:
                                    d = dashboard_df[[target]].copy(); d[target]=pd.to_numeric(d[target],errors="coerce"); d=d.dropna()
                                    if _plotly_ok:
                                        fig = px.histogram(d,x=target,nbins=30,color_discrete_sequence=[palette[1]],title=cfg["title"]) if typ == "Histogram" else px.box(d,y=target,color_discrete_sequence=[palette[1]],title=cfg["title"])
                                        fig.update_layout(template="plotly_dark" if theme_name=="Midnight Neon" else "plotly_white",paper_bgcolor=theme["panel"],plot_bgcolor=theme["panel"],font_color=theme["text"],xaxis=dict(tickfont=dict(color=theme["text"],size=12),title_font=dict(color=theme["text"]),automargin=True),yaxis=dict(tickfont=dict(color=theme["text"],size=12),title_font=dict(color=theme["text"]),automargin=True,gridcolor=("#374151" if theme_name=="Midnight Neon" else "#D9E1E8")),margin=dict(l=15,r=15,t=45,b=15),height=330); st.plotly_chart(fig,use_container_width=True,key=f"advisor_render_{row_start}_{j}")
                                    else: st.bar_chart(d)
                                else: st.info("This visualization needs a numeric field.")
                            elif typ in ["Donut share", "Pie share", "Treemap"]:
                                if xcol:
                                    temp=dashboard_df.copy(); temp[xcol]=temp[xcol].fillna("(Missing)").astype(str)
                                    _details = cfg.get("details") if cfg.get("details") in temp.columns and cfg.get("details") != xcol else None
                                    _group_cols = [xcol, _details] if typ == "Treemap" and _details else [xcol]
                                    if valcol:
                                        grp=temp.groupby(_group_cols,dropna=False)[valcol].agg(cfg["aggregation"].lower() if cfg["aggregation"]!="Average" else "mean").reset_index(name="Value")
                                    else:
                                        grp=temp.groupby(_group_cols,dropna=False).size().reset_index(name="Value")
                                    grp=grp.sort_values("Value",ascending=False).head(50 if _details else 15)
                                    if _plotly_ok:
                                        if typ=="Treemap": fig=px.treemap(grp,path=[xcol]+([_details] if _details else []),values="Value",color="Value",color_continuous_scale=[palette[0],palette[2],palette[4]],title=cfg["title"])
                                        else: fig=px.pie(grp,names=xcol,values="Value",hole=.52 if typ=="Donut share" else 0,color_discrete_sequence=palette,title=cfg["title"])
                                        fig.update_layout(template="plotly_dark" if theme_name=="Midnight Neon" else "plotly_white",paper_bgcolor=theme["panel"],font_color=theme["text"],xaxis=dict(tickfont=dict(color=theme["text"],size=12),title_font=dict(color=theme["text"]),automargin=True),yaxis=dict(tickfont=dict(color=theme["text"],size=12),title_font=dict(color=theme["text"]),automargin=True,gridcolor=("#374151" if theme_name=="Midnight Neon" else "#D9E1E8")),margin=dict(l=10,r=10,t=45,b=10),height=330); st.plotly_chart(fig,use_container_width=True,key=f"advisor_render_{row_start}_{j}")
                                    else: st.bar_chart(grp.set_index(xcol)["Value"])
                                else: st.info("Choose a category field.")
                            elif typ == "Scatter relationship":
                                if len(numeric_cols)>=2:
                                    sx=xcol if xcol in numeric_cols else numeric_cols[0]; sy=valcol if valcol in numeric_cols and valcol!=sx else next((q for q in numeric_cols if q!=sx),numeric_cols[1]); d=dashboard_df[[sx,sy]].apply(pd.to_numeric,errors="coerce").dropna().head(5000)
                                    if _plotly_ok:
                                        fig=px.scatter(d,x=sx,y=sy,color_discrete_sequence=[palette[2]],title=cfg["title"]); fig.update_layout(template="plotly_dark" if theme_name=="Midnight Neon" else "plotly_white",paper_bgcolor=theme["panel"],plot_bgcolor=theme["panel"],font_color=theme["text"],xaxis=dict(tickfont=dict(color=theme["text"],size=12),title_font=dict(color=theme["text"]),automargin=True),yaxis=dict(tickfont=dict(color=theme["text"],size=12),title_font=dict(color=theme["text"]),automargin=True,gridcolor=("#374151" if theme_name=="Midnight Neon" else "#D9E1E8")),margin=dict(l=15,r=15,t=45,b=15),height=330); st.plotly_chart(fig,use_container_width=True,key=f"advisor_render_{row_start}_{j}")
                                    else: st.scatter_chart(d,x=sx,y=sy)
                                else: st.info("Scatter needs two numeric columns.")
                            elif xcol:
                                temp=dashboard_df.copy(); temp[xcol]=temp[xcol].fillna("(Missing)").astype(str)
                                aggmap={"Sum":"sum","Average":"mean","Count":"count","Minimum":"min","Maximum":"max"}
                                _legend = cfg.get("legend") if cfg.get("legend") in dashboard_df.columns and cfg.get("legend") != xcol else None
                                if typ in ["Stacked bar", "Stacked column"] and _legend and valcol:
                                    temp[_legend]=temp[_legend].fillna("(Missing)").astype(str)
                                    t=temp.groupby([xcol,_legend],dropna=False)[valcol].agg(aggmap[cfg["aggregation"]]).reset_index(name="Value")
                                    t=t.sort_values("Value",ascending=False).head(300)
                                    if _plotly_ok:
                                        if typ=="Stacked bar": fig=px.bar(t,x="Value",y=xcol,color=_legend,orientation="h",barmode="stack",color_discrete_sequence=palette,title=cfg["title"])
                                        else: fig=px.bar(t,x=xcol,y="Value",color=_legend,barmode="stack",color_discrete_sequence=palette,title=cfg["title"])
                                    else:
                                        fig=None
                                else:
                                    if valcol:
                                        grp=temp.groupby(xcol,dropna=False)[valcol].agg(aggmap[cfg["aggregation"]]).reset_index(name="Value")
                                    else: grp=temp[xcol].value_counts(dropna=False).rename_axis(xcol).reset_index(name="Value")
                                    if typ in ["Line trend","Area trend"]:
                                        if xcol in date_cols:
                                            grp[xcol]=pd.to_datetime(grp[xcol],errors="coerce",dayfirst=True)
                                        grp=grp.sort_values(xcol,ascending=True).head(100)
                                    else:
                                        grp=grp.sort_values("Value",ascending=False).head(20)
                                    if _plotly_ok:
                                        if typ=="Line trend": fig=px.line(grp,x=xcol,y="Value",markers=True,color_discrete_sequence=[palette[0]],title=cfg["title"])
                                        elif typ=="Area trend": fig=px.area(grp,x=xcol,y="Value",color_discrete_sequence=[palette[1]],title=cfg["title"])
                                        elif typ=="Bar comparison": fig=px.bar(grp,x="Value",y=xcol,orientation="h",color=xcol,color_discrete_sequence=palette,title=cfg["title"])
                                        elif typ in ["Stacked bar", "Stacked column"]:
                                            if typ=="Stacked bar": fig=px.bar(grp,x="Value",y=xcol,orientation="h",color=xcol,color_discrete_sequence=palette,title=cfg["title"])
                                            else: fig=px.bar(grp,x=xcol,y="Value",color=xcol,color_discrete_sequence=palette,title=cfg["title"])
                                        else: fig=px.bar(grp,x=xcol,y="Value",color=xcol,color_discrete_sequence=palette,title=cfg["title"])
                                    else:
                                        fig=None
                                if _plotly_ok and fig is not None:
                                    fig.update_layout(template="plotly_dark" if theme_name=="Midnight Neon" else "plotly_white",paper_bgcolor=theme["panel"],plot_bgcolor=theme["panel"],font_color=theme["text"],xaxis=dict(tickfont=dict(color=theme["text"],size=12),title_font=dict(color=theme["text"]),automargin=True),yaxis=dict(tickfont=dict(color=theme["text"],size=12),title_font=dict(color=theme["text"]),automargin=True,gridcolor=("#374151" if theme_name=="Midnight Neon" else "#D9E1E8")),showlegend=(typ in ["Stacked bar","Stacked column"] and bool(_legend)),margin=dict(l=15,r=15,t=45,b=20),height=330); st.plotly_chart(fig,use_container_width=True,key=f"advisor_render_{row_start}_{j}")
                                elif not _plotly_ok:
                                    st.bar_chart(grp.set_index(xcol)["Value"] if "grp" in locals() else t)
                            else: st.info("Choose fields for this panel.")
                        except Exception as err:
                            st.warning(f"This panel could not be rendered with the selected fields: {err}")

            st.markdown("### 6 · Insights and export")
            if show_insights:
                insights=[]
                if len(dashboard_df)!=len(df): insights.append(f"Current slicers include {len(dashboard_df):,} rows ({len(dashboard_df)/max(1,len(df)):.1%} of the working dataset).")
                for c in numeric_cols[:3]:
                    v=pd.to_numeric(dashboard_df[c],errors="coerce").dropna()
                    if len(v): insights.append(f"**{c}**: total {v.sum():,.2f}; average {v.mean():,.2f}; {len(v):,} valid numeric values.")
                if date_cols:
                    _date_col = date_cols[0]
                    _parsed_dates = pd.to_datetime(dashboard_df[_date_col], errors="coerce", dayfirst=True).dropna()
                    if len(_parsed_dates):
                        insights.append(f"**Date coverage**: {_parsed_dates.min():%d %b %Y} to {_parsed_dates.max():%d %b %Y} ({len(_parsed_dates):,} valid dates in {_date_col}).")
                for _status_col in [c for c in categorical_cols if any(t in str(c).lower() for t in ["status", "state", "stage", "outcome"])][:1]:
                    _status_counts = dashboard_df[_status_col].fillna("(Missing)").astype(str).value_counts()
                    if len(_status_counts):
                        _status_rate = _status_counts.iloc[0] / max(1, int(_status_counts.sum())) * 100
                        insights.append(f"**{_status_col}**: most common value is {_status_counts.index[0]} ({_status_counts.iloc[0]:,} rows, {_status_rate:.1f}% of the current selection).")
                for c in categorical_cols[:2]:
                    vc=dashboard_df[c].fillna("(Missing)").astype(str).value_counts()
                    if len(vc): insights.append(f"Most frequent **{c}**: {vc.index[0]} ({vc.iloc[0]:,} rows).")
                if insights:
                    for insight in insights: st.markdown("- "+insight)
                else: st.info("Add numeric or category columns to generate more insights.")
            with st.expander("🧪 What-if analysis · explore assumptions without changing your data", expanded=False):
                st.caption("This is a simple proportional scenario, not a forecast: it changes the selected measure for comparison only. Your original dataset remains unchanged.")
                _whatif_candidates = [c for c in numeric_cols if pd.to_numeric(dashboard_df[c], errors="coerce").notna().any()]
                if _whatif_candidates:
                    _wi1, _wi2 = st.columns([1, 1])
                    _wi_col = _wi1.selectbox("Measure to simulate", _whatif_candidates, key="advisor_whatif_column")
                    _wi_change = _wi2.slider("Assumed change", min_value=-50, max_value=100, value=10, step=5, format="%d%%", key="advisor_whatif_change")
                    _wi_values = pd.to_numeric(dashboard_df[_wi_col], errors="coerce").dropna()
                    _wi_base = float(_wi_values.sum())
                    _wi_scenario = _wi_base * (1 + _wi_change / 100.0)
                    _wi_delta = _wi_scenario - _wi_base
                    _wi_cards = st.columns(3)
                    _wi_cards[0].metric("Current total · " + _pretty_field_name(_wi_col), _format_dashboard_value(_wi_base, _wi_col))
                    _wi_cards[1].metric("Scenario total", _format_dashboard_value(_wi_scenario, _wi_col), delta=f"{_wi_change:+d}% assumption")
                    _wi_cards[2].metric("Difference", _format_dashboard_value(_wi_delta, _wi_col))
                    st.caption("Scenario calculation: current total × (1 + assumed change). This does not model interactions between business variables.")
                else:
                    st.info("Add a numeric measure to use what-if analysis.")

            st.markdown("#### 📦 Download complete reports")
            st.caption("Exports use the current slicer selections. Excel is editable; PDF is a static snapshot of the current dashboard selection.")

            # Build reusable KPI and chart-data tables from the current filtered view.
            _export_kpi_rows = []
            for _item in kpi_config:
                _vals = pd.to_numeric(dashboard_df[_item["column"]], errors="coerce").dropna()
                _agg = _item["aggregation"]
                if _agg == "Distinct Count":
                    _value = int(dashboard_df[_item["column"]].nunique(dropna=True))
                elif _agg == "Count" and _item["column"] not in numeric_cols:
                    _value = int(dashboard_df[_item["column"]].count())
                else:
                    _value = {"Sum": _vals.sum, "Average": _vals.mean, "Count": _vals.count,
                              "Minimum": _vals.min, "Maximum": _vals.max, "Median": _vals.median}[_agg]() if len(_vals) and _agg in {"Sum", "Average", "Count", "Minimum", "Maximum", "Median"} else None
                _export_kpi_rows.append({"KPI": _item.get("label") or _item["column"],
                                         "Column": _item["column"], "Calculation": _agg,
                                         "Value": _value})
            _kpi_export_df = pd.DataFrame(_export_kpi_rows, columns=["KPI", "Column", "Calculation", "Value"])

            _chart_data_frames = []
            for _cfg in sorted(chart_configs, key=lambda _z: _z.get("position", 999)):
                _x, _y = _cfg.get("x"), _cfg.get("y")
                if _cfg.get("type") == "Data table":
                    _chart_data_frames.append((_cfg.get("title", "Dataset overview")[:31], dashboard_df.head(10000).copy()))
                elif _x and _x in dashboard_df.columns:
                    _val = _y if _y in numeric_cols else None
                    _temp = dashboard_df.copy()
                    _temp[_x] = _temp[_x].fillna("(Missing)").astype(str)
                    if _val:
                        _aggmap = {"Sum":"sum", "Average":"mean", "Count":"count", "Minimum":"min", "Maximum":"max"}
                        _grp = _temp.groupby(_x, dropna=False)[_val].agg(_aggmap.get(_cfg.get("aggregation"), "sum")).reset_index(name="Value")
                    else:
                        _grp = _temp[_x].value_counts(dropna=False).rename_axis(_x).reset_index(name="Value")
                    if _cfg.get("type") in ("Line trend", "Area trend"):
                        _grp = _grp.sort_values(_x, ascending=True).head(1000)
                    else:
                        _grp = _grp.sort_values("Value", ascending=False).head(1000)
                    _chart_data_frames.append((_cfg.get("title", "Chart data")[:31], _grp))
            _quality_export_df = pd.DataFrame({
                "Column": list(df.columns),
                "Data Type": [str(x) for x in df.dtypes],
                "Missing Values": [int(x) for x in df.isna().sum().tolist()],
                "Missing Percentage": [round(float(x) * 100 / len(df), 2) if len(df) else 0 for x in df.isna().sum().tolist()],
                "Unique Values": [int(df[c].nunique(dropna=True)) for c in df.columns]
            })
            _insights_export = []
            for _c in numeric_cols[:5]:
                _v = pd.to_numeric(dashboard_df[_c], errors="coerce").dropna()
                if len(_v):
                    _insights_export.append({"Insight": f"{_c}: total {_v.sum():,.2f}; average {_v.mean():,.2f}; {len(_v):,} valid values."})
            for _c in categorical_cols[:3]:
                _vc = dashboard_df[_c].fillna("(Missing)").astype(str).value_counts()
                if len(_vc):
                    _insights_export.append({"Insight": f"Most frequent {_c}: {_vc.index[0]} ({_vc.iloc[0]:,} rows)."})
            _insights_export_df = pd.DataFrame(_insights_export, columns=["Insight"])

            # Keep export controls visible on every rerun, including after slicer changes.
            _export_col1, _export_col2 = st.columns(2)
            _selected_filter_text = "; ".join(
                [f"{c}: {', '.join(map(str, st.session_state.get('advisor_slicer_' + str(c), [])))}"
                 for c in filter_cols]
            ) or "All records"

            with _export_col1:
                _excel_buffer = io.BytesIO()
                try:
                    with pd.ExcelWriter(_excel_buffer, engine="openpyxl") as _writer:
                        pd.DataFrame([{
                            "Dashboard": dash_title, "Subtitle": dash_subtitle,
                            "Theme": theme_name, "Layout": layout_name,
                            "Rows in current selection": len(dashboard_df),
                            "Rows in full working dataset": len(df),
                            "Selected filters": _selected_filter_text
                        }]).to_excel(_writer, sheet_name="Dashboard Summary", index=False)
                        _kpi_export_df.to_excel(_writer, sheet_name="KPI Summary", index=False)
                        df.to_excel(_writer, sheet_name="Working Data", index=False)
                        dashboard_df.to_excel(_writer, sheet_name="Filtered Data", index=False)
                        _quality_export_df.to_excel(_writer, sheet_name="Data Quality", index=False)
                        _insights_export_df.to_excel(_writer, sheet_name="Insights", index=False)

                        _chart_sheet_names = []
                        for _idx, (_sheet, _data) in enumerate(_chart_data_frames):
                            _safe = re.sub(r'[\[\]\:\*\?\/\\]', '-', str(_sheet))[:31] or f"Chart {_idx+1}"
                            _base, _n = _safe, 2
                            while _safe in _writer.book.sheetnames:
                                suffix = f"_{_n}"
                                _safe = _base[:31-len(suffix)] + suffix
                                _n += 1
                            _data.to_excel(_writer, sheet_name=_safe, index=False)
                            _chart_sheet_names.append((_safe, _sheet, _data))

                        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                        from openpyxl.utils import get_column_letter
                        from openpyxl.chart import BarChart, LineChart, PieChart, Reference
                        from openpyxl.chart.label import DataLabelList

                        # Put the dashboard first so the workbook opens on the visual result.
                        _book = _writer.book
                        _dash_ws = _book.create_sheet("Dashboard", 0)
                        _dash_ws.sheet_view.showGridLines = False
                        _dash_ws.merge_cells("A1:N1")
                        _dash_ws["A1"] = str(dash_title)
                        _dash_ws["A1"].font = Font(name="Aptos Display", size=22, bold=True, color="FFFFFF")
                        _dash_ws["A1"].fill = PatternFill("solid", fgColor=str(theme.get("primary", "#176B87")).replace("#", "").upper())
                        _dash_ws["A1"].alignment = Alignment(vertical="center")
                        _dash_ws.row_dimensions[1].height = 38
                        _dash_ws.merge_cells("A2:N2")
                        _dash_ws["A2"] = f"{dash_subtitle} | {len(dashboard_df):,} of {len(df):,} rows | Filters: {_selected_filter_text}"
                        _dash_ws["A2"].font = Font(size=10, italic=True, color="526171")
                        _dash_ws["A2"].alignment = Alignment(wrap_text=True, vertical="center")
                        _dash_ws.row_dimensions[2].height = 30

                        # KPI cards are formatted cell groups, not a text dump.
                        _card_starts = [1, 4, 7, 10, 13, 16, 19, 22]
                        _card_width = 3
                        for _ki, _kr in enumerate(_export_kpi_rows[:8]):
                            _col = _card_starts[_ki]
                            _label_cell = _dash_ws.cell(row=4, column=_col, value=str(_kr["KPI"])[:45])
                            _value = _kr.get("Value")
                            if _value is not None and pd.notna(_value):
                                _value = float(_value) if isinstance(_value, (int, float)) else _value
                            _value_cell = _dash_ws.cell(row=5, column=_col, value=_value)
                            _dash_ws.merge_cells(start_row=4, start_column=_col, end_row=4, end_column=_col+_card_width-1)
                            _dash_ws.merge_cells(start_row=5, start_column=_col, end_row=6, end_column=_col+_card_width-1)
                            _label_cell.font = Font(size=10, bold=True, color="FFFFFF")
                            _label_cell.fill = PatternFill("solid", fgColor=str(theme.get("secondary", "#3B82A0")).replace("#", "").upper())
                            _label_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                            _value_cell.font = Font(size=18, bold=True, color=str(theme.get("primary", "#176B87")).replace("#", "").upper())
                            _value_cell.fill = PatternFill("solid", fgColor="F1F6FA")
                            _value_cell.alignment = Alignment(horizontal="center", vertical="center")
                            _value_cell.number_format = '#,##0.00;[Red]-#,##0.00;0'
                        _dash_ws.row_dimensions[4].height = 28
                        _dash_ws.row_dimensions[5].height = 25
                        _dash_ws.row_dimensions[6].height = 22

                        # Add editable Excel-native charts directly to the Dashboard sheet.
                        _chart_anchor_slots = ["A8", "H8", "A24", "H24", "A40", "H40"]
                        _added_dashboard_charts = 0
                        for _idx, (_safe_sheet, _chart_title, _chart_frame) in enumerate(_chart_sheet_names):
                            if _chart_frame is None or _chart_frame.empty or _chart_frame.shape[1] < 2:
                                continue
                            if str(_chart_title).lower().startswith("dataset"):
                                continue
                            _cfg_match = next((x for x in chart_configs if str(x.get("title", ""))[:31] == str(_chart_title)[:31]), {})
                            _typ = str(_cfg_match.get("type", "Bar comparison"))
                            _chart_ws = _book[_safe_sheet]
                            _last = min(_chart_ws.max_row, 16)
                            if _last < 2:
                                continue
                            if _typ in ("Donut share", "Pie share"):
                                _native_chart = PieChart()
                                _native_chart.varyColors = True
                                _native_chart.dataLabels = DataLabelList()
                                _native_chart.dataLabels.showPercent = True
                            elif _typ in ("Line trend", "Area trend"):
                                _native_chart = LineChart()
                            else:
                                _native_chart = BarChart()
                            _native_chart.title = str(_chart_title)[:55]
                            _native_chart.style = 10
                            _native_chart.height = 8.2
                            _native_chart.width = 15.5
                            _native_data = Reference(_chart_ws, min_col=2, min_row=1, max_row=_last)
                            _native_cats = Reference(_chart_ws, min_col=1, min_row=2, max_row=_last)
                            _native_chart.add_data(_native_data, titles_from_data=True)
                            _native_chart.set_categories(_native_cats)
                            if isinstance(_native_chart, BarChart):
                                _native_chart.type = "col"
                                _native_chart.legend = None
                            _dash_ws.add_chart(_native_chart, _chart_anchor_slots[_added_dashboard_charts % len(_chart_anchor_slots)])
                            _added_dashboard_charts += 1

                        # Keep supporting data sheets usable and filterable.
                        for _ws in _book.worksheets:
                            _ws.freeze_panes = "A2" if _ws.title != "Dashboard" else "A4"
                            if _ws.title != "Dashboard" and _ws.max_row > 1 and _ws.max_column > 0:
                                _ws.auto_filter.ref = _ws.dimensions
                            # Use the numeric column index rather than the first cell's
                            # column_letter: merged ranges contain MergedCell objects,
                            # which do not expose column_letter in some openpyxl versions.
                            for _col_idx, _cells in enumerate(_ws.iter_cols(), start=1):
                                _max_len = max(
                                    (len(str(_cell.value)) if _cell.value is not None else 0
                                     for _cell in list(_cells)[:200]),
                                    default=10,
                                )
                                _ws.column_dimensions[get_column_letter(_col_idx)].width = min(max(_max_len + 2, 12), 38)
                        for _col_letter in "ABCDEFGHIJKLMNOPQRSTUVWX":
                            _dash_ws.column_dimensions[_col_letter].width = 14
                        _dash_ws.sheet_properties.pageSetUpPr.fitToPage = True
                        _dash_ws.page_setup.orientation = "landscape"
                        _dash_ws.page_setup.paperSize = _dash_ws.PAPERSIZE_A4
                        _dash_ws.page_setup.fitToWidth = 1
                        _dash_ws.page_setup.fitToHeight = 1

                    st.download_button(
                        "⬇️ Download Excel Dashboard & Analysis (.xlsx)",
                        data=_excel_buffer.getvalue(),
                        file_name="AI_Data_Analysis_Studio_Dashboard.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="advisor_download_excel_report"
                    )
                    st.caption("Excel opens on the Dashboard sheet with formatted KPI cards and editable charts. Data and analysis are kept on separate sheets. Worksheet filters are included; Excel-native slicer controls are not generated by this exporter.")
                except Exception as _excel_err:
                    st.error(f"Could not create Excel report: {_excel_err}")

            with _export_col2:
                try:
                    from reportlab.lib import colors as _pdf_colors
                    from reportlab.lib.pagesizes import A4, landscape
                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                    from reportlab.lib.units import mm
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as _PDFImage, PageBreak, KeepTogether

                    _pdf_buffer = io.BytesIO()
                    _page_w, _page_h = landscape(A4)
                    _doc = SimpleDocTemplate(
                        _pdf_buffer, pagesize=landscape(A4),
                        rightMargin=8*mm, leftMargin=8*mm,
                        topMargin=7*mm, bottomMargin=7*mm
                    )
                    _styles = getSampleStyleSheet()
                    _styles.add(ParagraphStyle(name="VisualTitle", parent=_styles["Title"], fontName="Helvetica-Bold",
                                               fontSize=17, leading=19, textColor=_pdf_colors.HexColor(theme["primary"]),
                                               alignment=0, spaceAfter=2))
                    _styles.add(ParagraphStyle(name="VisualSub", parent=_styles["BodyText"], fontSize=7, leading=8,
                                               textColor=_pdf_colors.HexColor("#526171"), spaceAfter=2))
                    _styles.add(ParagraphStyle(name="VisualKpiLabel", parent=_styles["BodyText"], fontSize=7, leading=8,
                                               textColor=_pdf_colors.white, alignment=1))
                    _styles.add(ParagraphStyle(name="VisualKpiValue", parent=_styles["BodyText"], fontName="Helvetica-Bold",
                                               fontSize=14, leading=16, textColor=_pdf_colors.HexColor(theme["primary"]), alignment=1))
                    _styles.add(ParagraphStyle(name="VisualSmall", parent=_styles["BodyText"], fontSize=8, leading=10))
                    _story = [
                        Paragraph(str(dash_title).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), _styles["VisualTitle"]),
                        Paragraph(f"{dash_subtitle} | {len(dashboard_df):,} of {len(df):,} rows | {theme_name}", _styles["VisualSub"]),
                        Spacer(1, 2*mm)
                    ]

                    # Render KPI cards as a visual row.
                    _kpi_cells = []
                    for _kr in _export_kpi_rows[:6]:
                        _val = _kr.get("Value")
                        _val_text = f"{_val:,.2f}" if isinstance(_val, (int, float)) and pd.notna(_val) else (str(_val) if _val is not None else "—")
                        if _val_text.endswith(".00"):
                            _val_text = _val_text[:-3]
                        _card_label = Paragraph(str(_kr["KPI"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), _styles["VisualKpiLabel"])
                        _card_value = Paragraph(_val_text, _styles["VisualKpiValue"])
                        _card = Table([[_card_label], [_card_value]], colWidths=[(_page_w-16*mm)/max(1, min(6, len(_export_kpi_rows)))], rowHeights=[8*mm, 12*mm])
                        _card.setStyle(TableStyle([
                            ("BACKGROUND", (0,0), (-1,0), _pdf_colors.HexColor(theme["primary"])),
                            ("BACKGROUND", (0,1), (-1,1), _pdf_colors.HexColor(theme["panel"])),
                            ("TEXTCOLOR", (0,0), (-1,0), _pdf_colors.white),
                            ("BOX", (0,0), (-1,-1), 0.7, _pdf_colors.HexColor(theme["accent"])),
                            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                            ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
                            ("TOPPADDING", (0,0), (-1,-1), 2), ("BOTTOMPADDING", (0,0), (-1,-1), 2),
                        ]))
                        _kpi_cells.append(_card)
                    if _kpi_cells:
                        _kpi_table = Table([_kpi_cells], colWidths=[(_page_w-16*mm)/len(_kpi_cells)]*len(_kpi_cells),
                                           rowHeights=[20*mm])
                        _kpi_style = [
                            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                            ("LEFTPADDING", (0,0), (-1,-1), 2),
                            ("RIGHTPADDING", (0,0), (-1,-1), 2),
                            ("TOPPADDING", (0,0), (-1,-1), 1),
                            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
                        ]
                        _kpi_table.setStyle(TableStyle(_kpi_style))
                        _story += [_kpi_table, Spacer(1, 3*mm)]

                    # One-page dashboard: chart panels only, no insights/text blocks mixed into it.
                    _pdf_chart_cells = []
                    _pdf_image_buffers = []
                    try:
                        import matplotlib
                        matplotlib.use("Agg")
                        import matplotlib.pyplot as _plt
                        for _idx, (_sheet, _data) in enumerate(_chart_data_frames):
                            if len(_pdf_chart_cells) >= 4:
                                break
                            if _data is None or _data.empty or _data.shape[1] < 2 or str(_sheet).lower().startswith("dataset"):
                                continue
                            _cfg_match = next((x for x in chart_configs if str(x.get("title", ""))[:31] == str(_sheet)[:31]), {})
                            _typ = str(_cfg_match.get("type", "Bar comparison"))
                            _plot_data = _data.iloc[:10, :2].copy()
                            _plot_data.iloc[:, 1] = pd.to_numeric(_plot_data.iloc[:, 1], errors="coerce")
                            _plot_data = _plot_data.dropna(subset=[_plot_data.columns[1]])
                            if _plot_data.empty:
                                continue
                            _fig, _ax = _plt.subplots(figsize=(5.0, 1.65), dpi=125)
                            _labels = _plot_data.iloc[:, 0].astype(str).tolist()
                            _values = _plot_data.iloc[:, 1].astype(float).tolist()
                            _primary = theme.get("primary", "#176B87")
                            _series = theme.get("series", [_primary, "#3B82A0", "#74B49B"])
                            if _typ in ("Line trend", "Area trend"):
                                _ax.plot(range(len(_values)), _values, marker="o", linewidth=2, markersize=3, color=_primary)
                                if _typ == "Area trend":
                                    _ax.fill_between(range(len(_values)), _values, alpha=.16, color=_primary)
                            elif _typ in ("Donut share", "Pie share"):
                                _ax.pie(_values, labels=None, startangle=90, colors=list(_series)[:max(1, len(_values))],
                                        wedgeprops={"width": .42} if _typ == "Donut share" else {})
                                _ax.legend(_labels, loc="center left", bbox_to_anchor=(1.0, .5), fontsize=5, frameon=False)
                            elif _typ == "Scatter relationship":
                                _ax.scatter(range(len(_values)), _values, color=_primary, s=14)
                            else:
                                _ax.bar(range(len(_values)), _values, color=_primary, width=.72)
                            if _typ not in ("Donut share", "Pie share"):
                                _ax.set_xticks(range(len(_labels)))
                                _ax.set_xticklabels(_labels, rotation=28, ha="right", fontsize=5.5)
                                _ax.tick_params(axis="y", labelsize=6)
                                _ax.grid(axis="y", alpha=.2)
                                _ax.set_axisbelow(True)
                            _ax.set_title(str(_cfg_match.get("title", _sheet))[:48], fontsize=8.5, loc="left", pad=5, fontweight="bold")
                            for _sp in ("top", "right"):
                                _ax.spines[_sp].set_visible(False)
                            _fig.tight_layout(pad=.8)
                            _img_buf = io.BytesIO()
                            _fig.savefig(_img_buf, format="png", bbox_inches="tight", facecolor="white", dpi=125)
                            _plt.close(_fig)
                            _img_buf.seek(0)
                            _pdf_image_buffers.append(_img_buf)
                            _pdf_chart_cells.append(_PDFImage(_img_buf, width=128*mm, height=43*mm, kind="proportional"))
                    except Exception:
                        _pdf_chart_cells = []

                    if _pdf_chart_cells:
                        while len(_pdf_chart_cells) < 4:
                            _pdf_chart_cells.append(Paragraph("", _styles["VisualSmall"]))
                        _visual_grid = Table(
                            [_pdf_chart_cells[:2], _pdf_chart_cells[2:4]],
                            colWidths=[( _page_w-18*mm)/2]*2,
                            rowHeights=[45*mm, 45*mm]
                        )
                        _visual_grid.setStyle(TableStyle([
                            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                            ("LEFTPADDING", (0,0), (-1,-1), 2),
                            ("RIGHTPADDING", (0,0), (-1,-1), 2),
                            ("TOPPADDING", (0,0), (-1,-1), 1),
                            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
                        ]))
                        _story.append(_visual_grid)
                    else:
                        _story.append(Paragraph("No chart data was available to render. Add at least one chart panel with a category/date field.", _styles["VisualSmall"]))

                    # Page 2 is deliberately separate: filters, insights, and notes do not crowd the dashboard.
                    _story.append(PageBreak())
                    _story.append(Paragraph("Dashboard Summary & Insights", _styles["VisualTitle"]))
                    _story.append(Paragraph(f"Dashboard: {str(dash_title)} | Selection: {len(dashboard_df):,} of {len(df):,} rows", _styles["VisualSub"]))
                    _story.append(Spacer(1, 3*mm))
                    _story.append(Paragraph("Applied filters", _styles["Heading2"]))
                    _story.append(Paragraph(str(_selected_filter_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:1500], _styles["VisualSmall"]))
                    _story.append(Spacer(1, 3*mm))
                    _story.append(Paragraph("Key insights", _styles["Heading2"]))
                    for _, _r in _insights_export_df.head(12).iterrows():
                        _story.append(Paragraph("• " + str(_r["Insight"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), _styles["VisualSmall"]))
                        _story.append(Spacer(1, 1.5*mm))
                    _story.append(Spacer(1, 3*mm))
                    _story.append(Paragraph("Data quality overview", _styles["Heading2"]))
                    _qdata = [["Column", "Type", "Missing", "Unique"]] + [
                        [str(r["Column"])[:36], str(r["Data Type"])[:20], str(r["Missing Values"]), str(r["Unique Values"])]
                        for _, r in _quality_export_df.head(25).iterrows()
                    ]
                    _qt = Table(_qdata, repeatRows=1, colWidths=[65*mm, 42*mm, 25*mm, 25*mm])
                    _qt.setStyle(TableStyle([
                        ("BACKGROUND", (0,0), (-1,0), _pdf_colors.HexColor(theme["primary"])),
                        ("TEXTCOLOR", (0,0), (-1,0), _pdf_colors.white),
                        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                        ("FONTSIZE", (0,0), (-1,-1), 8),
                        ("GRID", (0,0), (-1,-1), .3, _pdf_colors.HexColor("#CBD5E1")),
                        ("ROWBACKGROUNDS", (0,1), (-1,-1), [_pdf_colors.white, _pdf_colors.HexColor("#F1F5F9")]),
                        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                    ]))
                    _story.append(_qt)
                    _doc.build(_story)
                    st.download_button(
                        "⬇️ Download Visual Dashboard PDF",
                        data=_pdf_buffer.getvalue(),
                        file_name="AI_Data_Analysis_Studio_Dashboard.pdf",
                        mime="application/pdf",
                        key="advisor_download_pdf_report"
                    )
                    st.caption("PDF page 1 is a visual dashboard. Page 2 contains filters, insights, and data-quality notes. PDF exports are static snapshots.")
                except Exception as _pdf_err:
                    st.warning(f"PDF export unavailable in this environment: {_pdf_err}")

            dashboard_config={"title":dash_title,"subtitle":dash_subtitle,"theme":theme_name,"custom_theme":{"background":theme.get("bg"),"panel":theme.get("panel"),"primary":theme.get("primary"),"accent":theme.get("accent")},"layout":layout_name,"filters":filter_cols,"kpis":kpi_config,"charts":chart_configs,"show_insights":show_insights}
            st.download_button("Download dashboard configuration (JSON)",data=json.dumps(dashboard_config,indent=2,default=str).encode("utf-8"),file_name="dashboard_configuration.json",mime="application/json",key="advisor_download_config")
            st.download_button("Export current filtered data (CSV)",data=dashboard_df.to_csv(index=False).encode("utf-8-sig"),file_name="dashboard_filtered_data.csv",mime="text/csv",key="advisor_download_filtered")
            config_upload=st.file_uploader("Reopen a saved dashboard configuration (JSON)",type=["json"],key="advisor_config_upload")
            if config_upload is not None:
                try:
                    loaded_config=json.loads(config_upload.getvalue().decode("utf-8-sig"))
                    st.session_state["advisor_saved_config_preview"]=loaded_config
                    st.success("Configuration loaded for review. Click Apply to use its settings.")
                    if st.button("Apply saved dashboard configuration",key="advisor_apply_config"):
                        st.session_state["advisor_title"]=loaded_config.get("title","Business Performance Dashboard")
                        st.session_state["advisor_subtitle"]=loaded_config.get("subtitle","Interactive overview of your data")
                        st.session_state["advisor_theme_name"]=loaded_config.get("theme", "Ocean Professional")
                        st.session_state["advisor_layout"]=loaded_config.get("layout","Executive · 2 columns")
                        st.session_state["advisor_filter_cols"]=loaded_config.get("filters",[])
                        st.session_state["advisor_kpi_config"]=loaded_config.get("kpis",[])
                        st.session_state["advisor_chart_config"]=loaded_config.get("charts",[])
                        st.session_state["advisor_chart_count"]=len(loaded_config.get("charts",[])) or 4
                        st.session_state["advisor_show_insights"]=loaded_config.get("show_insights",True)
                        st.rerun()
                except Exception as e:
                    st.error(f"Could not read dashboard configuration: {e}")

        with tab5:
            st.subheader("📐 Measures Engine")
            st.caption(
                "Create reusable calculations from the current primary working dataset. "
                "Measures recalculate automatically when the uploaded data changes."
            )

            numeric_measure_columns = df.select_dtypes(include="number").columns.tolist()
            all_measure_columns = df.columns.tolist()

            if "saved_measures" not in st.session_state:
                st.session_state["saved_measures"] = []

            # Reset saved measures when a different source dataset is uploaded.
            current_measure_signature = hashlib.sha256(
                uploaded_file.getvalue()
            ).hexdigest()
            if st.session_state.get("measures_source") != current_measure_signature:
                st.session_state["measures_source"] = current_measure_signature
                st.session_state["saved_measures"] = []

            st.markdown("### 1. Quick Measures")
            if numeric_measure_columns:
                quick_column = st.selectbox(
                    "Choose a numeric column",
                    numeric_measure_columns,
                    key="quick_measure_column"
                )
                quick_aggregation = st.selectbox(
                    "Calculation",
                    ["SUM", "AVERAGE", "COUNT", "DISTINCT COUNT", "MIN", "MAX"],
                    key="quick_measure_aggregation"
                )

                series = df[quick_column]
                if quick_aggregation == "SUM":
                    quick_value = series.sum()
                elif quick_aggregation == "AVERAGE":
                    quick_value = series.mean()
                elif quick_aggregation == "COUNT":
                    quick_value = int(series.count())
                elif quick_aggregation == "DISTINCT COUNT":
                    quick_value = int(series.nunique(dropna=True))
                elif quick_aggregation == "MIN":
                    quick_value = series.min()
                else:
                    quick_value = series.max()

                if pd.isna(quick_value):
                    st.metric(f"{quick_aggregation} of {quick_column}", "N/A")
                elif isinstance(quick_value, (int, float)) or hasattr(quick_value, "item"):
                    st.metric(
                        f"{quick_aggregation} of {quick_column}",
                        f"{quick_value:,.2f}" if isinstance(quick_value, float) else f"{quick_value:,.2f}"
                    )
                else:
                    st.metric(f"{quick_aggregation} of {quick_column}", str(quick_value))
            else:
                st.info("No numeric columns found. Quick numeric measures need at least one numeric column.")

            st.divider()
            st.markdown("### 2. Create a Custom Measure")
            measure_name = st.text_input(
                "Measure name",
                placeholder="e.g. Total Revenue",
                key="custom_measure_name"
            )
            measure_type = st.selectbox(
                "Measure type",
                [
                    "Aggregation",
                    "Percentage of total",
                    "Column calculation"
                ],
                key="custom_measure_type"
            )

            custom_measure_value = None
            measure_description = ""

            if measure_type == "Aggregation":
                if all_measure_columns:
                    custom_column = st.selectbox(
                        "Column to aggregate",
                        all_measure_columns,
                        key="custom_aggregation_column"
                    )
                    aggregation = st.selectbox(
                        "Aggregation",
                        ["SUM", "AVERAGE", "COUNT", "DISTINCT COUNT", "MIN", "MAX"],
                        key="custom_aggregation_method"
                    )
                    column_series = df[custom_column]
                    if aggregation in ["SUM", "AVERAGE", "MIN", "MAX"] and not pd.api.types.is_numeric_dtype(column_series):
                        st.warning(f"{aggregation} requires a numeric column.")
                    else:
                        if aggregation == "SUM":
                            custom_measure_value = column_series.sum()
                        elif aggregation == "AVERAGE":
                            custom_measure_value = column_series.mean()
                        elif aggregation == "COUNT":
                            custom_measure_value = int(column_series.count())
                        elif aggregation == "DISTINCT COUNT":
                            custom_measure_value = int(column_series.nunique(dropna=True))
                        elif aggregation == "MIN":
                            custom_measure_value = column_series.min()
                        else:
                            custom_measure_value = column_series.max()
                    measure_description = f"{aggregation}({custom_column})"

            elif measure_type == "Percentage of total":
                if numeric_measure_columns:
                    percentage_column = st.selectbox(
                        "Numeric column",
                        numeric_measure_columns,
                        key="percentage_measure_column"
                    )
                    category_column = st.selectbox(
                        "Break down by category",
                        ["(Overall total)"] + all_measure_columns,
                        key="percentage_category_column"
                    )
                    total_value = df[percentage_column].sum()
                    if category_column == "(Overall total)":
                        custom_measure_value = 100.0 if total_value != 0 else None
                        measure_description = f"Share of total for {percentage_column}"
                    else:
                        percentage_table = (
                            df.groupby(category_column, dropna=False)[percentage_column]
                            .sum()
                            .reset_index(name="Value")
                        )
                        percentage_table["Percentage"] = (
                            percentage_table["Value"] / total_value * 100
                            if total_value != 0 else 0
                        )
                        st.dataframe(percentage_table, use_container_width=True, hide_index=True)
                        measure_description = f"{percentage_column} contribution by {category_column}"
                        custom_measure_value = None
                else:
                    st.info("Percentage measures require a numeric column.")

            else:
                if len(numeric_measure_columns) >= 2:
                    left_column = st.selectbox(
                        "First numeric column",
                        numeric_measure_columns,
                        key="measure_calc_left"
                    )
                    calculation_operator = st.selectbox(
                        "Operation",
                        ["+", "-", "×", "÷"],
                        key="measure_calc_operator"
                    )
                    right_column = st.selectbox(
                        "Second numeric column",
                        [c for c in numeric_measure_columns if c != left_column],
                        key="measure_calc_right"
                    )
                    left_total = df[left_column].sum()
                    right_total = df[right_column].sum()
                    if calculation_operator == "+":
                        custom_measure_value = left_total + right_total
                    elif calculation_operator == "-":
                        custom_measure_value = left_total - right_total
                    elif calculation_operator == "×":
                        custom_measure_value = left_total * right_total
                    else:
                        custom_measure_value = left_total / right_total if right_total != 0 else None
                    measure_description = f"SUM({left_column}) {calculation_operator} SUM({right_column})"
                else:
                    st.info("Column calculations need at least two numeric columns.")

            if custom_measure_value is not None and not pd.isna(custom_measure_value):
                st.write("**Current result:**")
                st.metric(
                    measure_name.strip() or "Preview measure",
                    f"{custom_measure_value:,.2f}" if isinstance(custom_measure_value, (int, float)) else str(custom_measure_value)
                )

            if st.button("➕ Save Measure", type="primary", key="save_custom_measure"):
                if not measure_name.strip():
                    st.warning("Enter a name for your measure.")
                elif any(item["name"].casefold() == measure_name.strip().casefold()
                         for item in st.session_state["saved_measures"]):
                    st.warning("A measure with that name already exists.")
                elif custom_measure_value is None or pd.isna(custom_measure_value):
                    st.warning("This measure has no single numeric result to save. Check the selected columns or calculation.")
                else:
                    st.session_state["saved_measures"].append({
                        "name": measure_name.strip(),
                        "type": measure_type,
                        "description": measure_description,
                        "value": float(custom_measure_value)
                    })
                    st.success("Measure saved.")
                    st.rerun()

            st.divider()
            st.markdown("### 3. Calculated Columns")
            st.caption(
                "Create row-by-row calculated columns. Review and approve each change. "
                "Approved columns are now available throughout the app, including statistics, charts, cleaning, and DAX Query Lab. "
                "The uploaded source file itself remains unchanged."
            )

            if st.session_state.get("calculated_columns_source") != current_measure_signature:
                st.session_state["calculated_columns_source"] = current_measure_signature
                st.session_state["calculated_columns_df"] = df.copy()
                st.session_state["calculated_columns_history"] = []

            calculated_df = st.session_state["calculated_columns_df"].copy()
            calculated_numeric_columns = calculated_df.select_dtypes(include="number").columns.tolist()
            calculated_all_columns = calculated_df.columns.tolist()
            calculated_name = st.text_input(
                "New column name", placeholder="e.g. Profit", key="calculated_column_name"
            )
            calculated_type = st.selectbox(
                "Calculation type",
                ["Arithmetic between columns", "Percentage of another column", "Conditional category", "Combine text columns"],
                key="calculated_column_type"
            )
            calculated_preview = None
            calculated_description = ""

            if calculated_type == "Arithmetic between columns":
                if len(calculated_numeric_columns) >= 2:
                    calc_left = st.selectbox("First numeric column", calculated_numeric_columns, key="calc_col_left")
                    calc_operator = st.selectbox("Operation", ["+", "-", "×", "÷"], key="calc_col_operator")
                    calc_right = st.selectbox(
                        "Second numeric column", [c for c in calculated_numeric_columns if c != calc_left], key="calc_col_right"
                    )
                    if calc_operator == "+":
                        calculated_preview = calculated_df[calc_left] + calculated_df[calc_right]
                    elif calc_operator == "-":
                        calculated_preview = calculated_df[calc_left] - calculated_df[calc_right]
                    elif calc_operator == "×":
                        calculated_preview = calculated_df[calc_left] * calculated_df[calc_right]
                    else:
                        calculated_preview = calculated_df[calc_left].div(calculated_df[calc_right].replace(0, float("nan")))
                    calculated_description = f"{calc_left} {calc_operator} {calc_right}"
                else:
                    st.info("Arithmetic columns require at least two numeric columns.")

            elif calculated_type == "Percentage of another column":
                if len(calculated_numeric_columns) >= 2:
                    numerator_col = st.selectbox("Numerator column", calculated_numeric_columns, key="calc_pct_numerator")
                    denominator_col = st.selectbox("Denominator column", calculated_numeric_columns, key="calc_pct_denominator")
                    calculated_preview = calculated_df[numerator_col].div(
                        calculated_df[denominator_col].replace(0, float("nan"))
                    ) * 100
                    calculated_description = f"{numerator_col} / {denominator_col} * 100"
                    st.caption("Rows with a zero denominator will have a missing result, not an error.")
                else:
                    st.info("Percentage calculations require at least two numeric columns.")

            elif calculated_type == "Conditional category":
                if calculated_numeric_columns:
                    condition_col = st.selectbox("Numeric column to evaluate", calculated_numeric_columns, key="calc_cond_column")
                    threshold = st.number_input("Threshold", value=100.0, key="calc_cond_threshold")
                    below_label = st.text_input("Label below threshold", value="Low", key="calc_cond_below")
                    above_label = st.text_input("Label at or above threshold", value="High", key="calc_cond_above")
                    calculated_preview = pd.Series(
                        [None if pd.isna(v) else (above_label if v >= threshold else below_label)
                         for v in calculated_df[condition_col]], index=calculated_df.index, dtype="string"
                    )
                    calculated_description = f"IF({condition_col} >= {threshold}, {above_label}, {below_label})"
                else:
                    st.info("Conditional categories require a numeric column.")

            else:
                if calculated_all_columns:
                    text_columns = st.multiselect("Columns to combine (choose at least two)", calculated_all_columns, key="calc_text_columns")
                    text_separator = st.text_input("Separator", value=" ", key="calc_text_separator")
                    if len(text_columns) >= 2:
                        calculated_preview = calculated_df[text_columns].astype("string").fillna("").agg(
                            text_separator.join, axis=1
                        )
                        calculated_description = f"Combine {', '.join(map(str, text_columns))}"
                    else:
                        st.info("Choose at least two columns to combine text.")

            if calculated_preview is not None:
                preview_df = pd.DataFrame({"Original row": calculated_df.index, "Calculated preview": calculated_preview})
                st.write("**Preview (first 10 rows)**")
                st.dataframe(preview_df.head(10), use_container_width=True, hide_index=True)
                confirm_calculated_column = st.checkbox(
                    "I reviewed the preview and approve adding this column", key="confirm_calculated_column"
                )
                if st.button("➕ Apply Calculated Column", type="primary", key="apply_calculated_column"):
                    clean_name = calculated_name.strip()
                    if not confirm_calculated_column:
                        st.warning("Please review the preview and confirm first.")
                    elif not clean_name:
                        st.warning("Enter a name for the new column.")
                    elif clean_name in calculated_all_columns:
                        st.warning("That column name already exists. Choose a unique name.")
                    else:
                        calculated_df[clean_name] = calculated_preview
                        st.session_state["calculated_columns_df"] = calculated_df.copy()
                        st.session_state["primary_dataset_df"] = calculated_df.copy()
                        st.session_state["transform_df"] = calculated_df.copy()
                        st.session_state["cleaned_df"] = calculated_df.copy()
                        st.session_state["calculated_columns_history"].append(f"Created {clean_name}: {calculated_description}")
                        st.success(f"Added calculated column: {clean_name}")
                        st.rerun()

            if st.session_state.get("calculated_columns_history"):
                with st.expander("Calculated column history", expanded=False):
                    for history_item in st.session_state["calculated_columns_history"]:
                        st.write(f"• {history_item}")

            st.write("**Derived dataset preview**")
            st.dataframe(calculated_df.head(100), use_container_width=True, hide_index=True)
            calculated_csv = calculated_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Download Dataset with Calculated Columns (CSV)",
                data=calculated_csv, file_name="dataset_with_calculated_columns.csv",
                mime="text/csv", key="download_calculated_columns_csv"
            )
            calculated_excel_buffer = io.BytesIO()
            with pd.ExcelWriter(calculated_excel_buffer, engine="openpyxl") as writer:
                calculated_df.to_excel(writer, sheet_name="Calculated Data", index=False)
            st.download_button(
                "⬇️ Download Dataset with Calculated Columns (Excel)",
                data=calculated_excel_buffer.getvalue(), file_name="dataset_with_calculated_columns.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_calculated_columns_excel"
            )

            st.divider()
            st.markdown("### 4. DAX Query Lab")
            st.caption(
                "Run a safe, supported subset of DAX-style table queries on the current working dataset, including approved calculated columns. "
                "This is not the full Power BI DAX engine. Supported patterns: EVALUATE TableName and "
                'EVALUATE SUMMARIZE(TableName, TableName[GroupColumn], "Output Name", SUM(TableName[NumericColumn])) ' 
                "with SUM, AVERAGE, COUNT, DISTINCTCOUNT, MIN, or MAX."
            )

            table_alias = st.text_input("Table name used in queries", value="Data", key="dax_table_name").strip()
            default_query = (f'EVALUATE\nSUMMARIZE(\n    {table_alias or "Data"},\n    {table_alias or "Data"}[{df.columns[0]}],\n    "Total Rows", COUNT({table_alias or "Data"}[{df.columns[0]}])\n)')
            dax_examples = {
                "Group by with row count": default_query,
                "Show the dataset": f"EVALUATE {table_alias or 'Data'}",
            }
            example_choice = st.selectbox("Load an example", list(dax_examples.keys()), key="dax_example_choice")
            if st.button("Load selected example", key="load_dax_example"):
                st.session_state["dax_query_editor"] = dax_examples[example_choice]
            dax_query = st.text_area(
                "DAX-style query", value=st.session_state.get("dax_query_editor", default_query),
                height=180, key="dax_query_editor", help="Use the table name shown above. Column names are case-sensitive."
            )

            def run_supported_dax(query_text, frame, table_name):
                import re
                query = query_text.strip().rstrip(";").strip()
                if not re.match(r"(?is)^EVALUATE\b", query):
                    raise ValueError("Query must start with EVALUATE.")
                body = re.sub(r"(?is)^EVALUATE\s+", "", query, count=1).strip()
                table_name = table_name or "Data"
                if re.fullmatch(re.escape(table_name), body, flags=re.IGNORECASE):
                    return frame.copy()
                # Deliberately support a constrained SUMMARIZE form rather than evaluating arbitrary code.
                match = re.fullmatch(r"(?is)SUMMARIZE\s*\((.*)\)", body)
                if not match:
                    raise ValueError("Unsupported query. Use EVALUATE Data or the supported SUMMARIZE pattern shown above.")
                inner = match.group(1)
                # Split arguments on commas outside quoted strings and parentheses/brackets.
                args, buf, depth, quoted = [], [], 0, False
                for ch in inner:
                    if ch == '"':
                        quoted = not quoted
                    if not quoted:
                        if ch == '(':
                            depth += 1
                        elif ch == ')':
                            depth -= 1
                        elif ch == ',' and depth == 0:
                            args.append(''.join(buf).strip()); buf=[]; continue
                    buf.append(ch)
                if buf:
                    args.append(''.join(buf).strip())
                if len(args) < 4 or (len(args)-2) % 2 != 0:
                    raise ValueError("SUMMARIZE needs a table, at least one grouping column, and name/expression pairs.")
                if args[0].strip().casefold() != table_name.casefold():
                    raise ValueError(f"Use '{table_name}' as the table name in this query.")
                group_cols=[]
                for arg in args[1:-1:2]:
                    colmatch = re.fullmatch(r"(?is)" + re.escape(table_name) + r"\s*\[([^\]]+)\]", arg)
                    if not colmatch:
                        raise ValueError(f"Invalid grouping column reference: {arg}")
                    col=colmatch.group(1).strip()
                    if col not in frame.columns:
                        raise ValueError(f"Column not found: {col}")
                    group_cols.append(col)
                result = frame.groupby(group_cols, dropna=False, as_index=False).size().drop(columns=[], errors='ignore')
                # Replace pandas' default size column with explicitly requested aggregations.
                result = result[group_cols].drop_duplicates().reset_index(drop=True)
                for idx in range(2, len(args), 2):
                    output_name = args[idx].strip()
                    if len(output_name) < 2 or output_name[0] != '"' or output_name[-1] != '"':
                        raise ValueError("Aggregation output names must be in double quotes.")
                    output_name = output_name[1:-1]
                    expr = args[idx+1].strip()
                    aggmatch = re.fullmatch(r"(?is)(SUM|AVERAGE|COUNT|DISTINCTCOUNT|MIN|MAX)\s*\(\s*" + re.escape(table_name) + r"\s*\[([^\]]+)\]\s*\)", expr)
                    if not aggmatch:
                        raise ValueError(f"Unsupported aggregation expression: {expr}")
                    agg, col = aggmatch.group(1).upper(), aggmatch.group(2).strip()
                    if col not in frame.columns:
                        raise ValueError(f"Column not found: {col}")
                    if output_name in group_cols:
                        raise ValueError(f"Output name conflicts with grouping column: {output_name}")
                    if agg in ("SUM", "AVERAGE", "MIN", "MAX") and not pd.api.types.is_numeric_dtype(frame[col]):
                        raise ValueError(f"{agg} requires a numeric column; '{col}' is not numeric.")
                    grouped = frame.groupby(group_cols, dropna=False)[col]
                    if agg == "SUM": values=grouped.sum(min_count=1)
                    elif agg == "AVERAGE": values=grouped.mean()
                    elif agg == "COUNT": values=grouped.count()
                    elif agg == "DISTINCTCOUNT": values=grouped.nunique(dropna=True)
                    elif agg == "MIN": values=grouped.min()
                    else: values=grouped.max()
                    result = result.merge(values.rename(output_name).reset_index(), on=group_cols, how="left")
                return result

            if st.button("▶ Run Query", type="primary", key="run_dax_query"):
                try:
                    if not table_alias:
                        raise ValueError("Enter a table name first.")
                    result_df = run_supported_dax(dax_query, df, table_alias)
                    st.session_state["dax_query_result"] = result_df
                    st.session_state["dax_query_error"] = None
                except Exception as exc:
                    st.session_state["dax_query_error"] = str(exc)
                    st.session_state["dax_query_result"] = None
            if st.session_state.get("dax_query_error"):
                st.error(f"Query error: {st.session_state['dax_query_error']}")
            if isinstance(st.session_state.get("dax_query_result"), pd.DataFrame):
                dax_result = st.session_state["dax_query_result"]
                st.success(f"Query completed: {len(dax_result):,} rows returned.")
                st.dataframe(dax_result, use_container_width=True, hide_index=True)
                st.download_button(
                    "⬇️ Download Query Results (CSV)", data=dax_result.to_csv(index=False).encode("utf-8-sig"),
                    file_name="dax_query_results.csv", mime="text/csv", key="download_dax_results_csv"
                )
                dax_excel_buffer = io.BytesIO()
                with pd.ExcelWriter(dax_excel_buffer, engine="openpyxl") as writer:
                    dax_result.to_excel(writer, sheet_name="Query Results", index=False)
                st.download_button(
                    "⬇️ Download Query Results (Excel)", data=dax_excel_buffer.getvalue(),
                    file_name="dax_query_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_dax_results_excel"
                )
                st.caption("To use a grouped DAX result in the dashboard and later analysis, promote it to the primary working dataset.")
                if st.button("Use DAX query result as primary dataset", key="promote_dax_primary"):
                    st.session_state["primary_dataset_df"] = dax_result.copy()
                    st.session_state["calculated_columns_df"] = dax_result.copy()
                    st.session_state["transform_df"] = dax_result.copy()
                    st.session_state["cleaned_df"] = dax_result.copy()
                    st.session_state["combined_result_df"] = None
                    st.session_state["combined_result_promoted"] = False
                    st.session_state["primary_dataset_name"] = "DAX Query Result"
                    st.success("DAX query result is now the primary working dataset.")
                    st.rerun()

            st.divider()
            st.markdown("### 5. Saved Measures")
            saved_measures = st.session_state["saved_measures"]
            if saved_measures:
                measures_table = pd.DataFrame(saved_measures)
                st.dataframe(measures_table, use_container_width=True, hide_index=True)
                st.download_button(
                    "⬇️ Download Measures (CSV)",
                    data=measures_table.to_csv(index=False).encode("utf-8-sig"),
                    file_name="measures_summary.csv",
                    mime="text/csv",
                    key="download_measures_csv"
                )
                measures_excel_buffer = io.BytesIO()
                with pd.ExcelWriter(measures_excel_buffer, engine="openpyxl") as writer:
                    measures_table.to_excel(writer, sheet_name="Measures", index=False)
                st.download_button(
                    "⬇️ Download Measures (Excel)",
                    data=measures_excel_buffer.getvalue(),
                    file_name="measures_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_measures_excel"
                )
                if st.button("Clear Saved Measures", key="clear_saved_measures"):
                    st.session_state["saved_measures"] = []
                    st.rerun()
            else:
                st.info("No saved measures yet. Create a custom measure above and save it.")

        with tab1:
            st.subheader("Dataset Preview")

            preview_rows = st.slider(
                "Rows to display",
                min_value=1,
                max_value=min(100, total_rows),
                value=min(10, total_rows),
                key="preview_rows"
            )

            st.dataframe(
                df.head(preview_rows),
                use_container_width=True,
                hide_index=True
            )

            st.subheader("Column Information")

            information = pd.DataFrame({
                "Column": df.columns.astype(str),
                "Data Type": [
                    str(dtype) for dtype in df.dtypes
                ],
                "Missing Values": [
                    int(value) for value in df.isna().sum()
                ],
                "Unique Values": [
                    int(value) for value in df.nunique()
                ]
            })

            st.dataframe(
                information,
                use_container_width=True,
                hide_index=True
            )

        with tab2:
            st.subheader("Data Quality Report")

            missing_report = pd.DataFrame({
                "Column": df.columns.astype(str),
                "Missing Count": [
                    int(value) for value in df.isna().sum()
                ],
                "Missing Percentage": [
                    round(float(value) / total_rows * 100, 2)
                    for value in df.isna().sum()
                ]
            })

            st.write("### Missing Values by Column")

            st.dataframe(
                missing_report,
                use_container_width=True,
                hide_index=True
            )

            st.write("### Duplicate Records")
            st.write(f"Potential duplicate rows: {duplicate_count:,}")

            st.write("### Constant Columns")

            constant_columns = [
                str(column)
                for column in df.columns
                if df[column].nunique(dropna=False) <= 1
            ]

            if constant_columns:
                st.warning(
                    "Columns containing only one distinct value: "
                    + ", ".join(constant_columns)
                )
            else:
                st.success("No constant columns were detected.")

            st.write("### Duplicate Column Names")

            column_names = list(map(str, df.columns))

            duplicate_names = [
                name
                for name, count in Counter(
                    column_names
                ).items()
                if count > 1
            ]

            if duplicate_names:
                st.warning(", ".join(duplicate_names))
            else:
                st.success("No duplicate column names were detected.")

        with tab3:
            st.subheader("Descriptive Statistics")

            numeric_df = df.select_dtypes(include="number")

            if not numeric_df.empty:
                st.dataframe(
                    numeric_df.describe().T,
                    use_container_width=True
                )
            else:
                st.info("No numeric columns were detected.")

            st.subheader("Category Summaries")

            categorical_columns = df.select_dtypes(
                include=["object", "category", "string"]
            ).columns.tolist()

            if categorical_columns:
                selected_category = st.selectbox(
                    "Select a categorical column",
                    categorical_columns
                )

                category_counts = (
                    df[selected_category]
                    .fillna("(Missing)")
                    .astype(str)
                    .value_counts()
                    .head(20)
                )

                st.bar_chart(category_counts)
            else:
                st.info("No categorical columns were detected.")

        with tab4:
                        # ==========================================
            # ADVANCED DATA TRANSFORMATIONS
            # ==========================================
            st.subheader("🛠️ Advanced Data Transformations")

            file_bytes = uploaded_file.getvalue()
            transform_signature = hashlib.sha256(file_bytes).hexdigest()

            if st.session_state.get("transform_source") != transform_signature:
                st.session_state["transform_source"] = transform_signature
                st.session_state["transform_df"] = df.copy()
                st.session_state["transform_history"] = []
            if not isinstance(st.session_state.get("transform_df"), pd.DataFrame):
                st.session_state["transform_df"] = df.copy()
            transform_df = st.session_state["transform_df"].copy()

            st.caption(
                "Preview your changes before applying them. "
                "Applied transformations are kept in this panel."
            )

            transform_action = st.selectbox(
                "Choose a transformation",
                [
                    "Promote First Row to Headers",
                    "Rename Column",
                    "Split Column",
                    "Extract Text",
                    "Join Columns",
                    "Change Data Type",
                    "Find and Replace",
                    "Trim Whitespace",
                    "Remove Columns"
                ],
                key="advanced_transform_action"
            )

            transform_columns = transform_df.columns.tolist()

            # ------------------------------------------
            # 1. PROMOTE FIRST ROW TO HEADERS
            # ------------------------------------------
            if transform_action == "Promote First Row to Headers":

                st.write("Use the first data row as column names.")

                st.dataframe(
                    transform_df.head(3),
                    use_container_width=True
                )

                if not transform_df.empty:
                    proposed_headers = [
                        str(value).strip()
                        if pd.notna(value) and str(value).strip()
                        else f"Column_{i + 1}"
                        for i, value in enumerate(transform_df.iloc[0])
                    ]

                    # Make header names unique
                    unique_headers = []
                    header_counts = {}

                    for header in proposed_headers:
                        header_counts[header] = header_counts.get(header, 0) + 1

                        if header_counts[header] > 1:
                            unique_headers.append(
                                f"{header}_{header_counts[header]}"
                            )
                        else:
                            unique_headers.append(header)

                    st.write("Proposed headers:")
                    st.write(unique_headers)

                    confirm_headers = st.checkbox(
                        "Confirm: use the first row as headers",
                        key="confirm_promote_headers"
                    )

                    if st.button(
                        "Apply Header Transformation",
                        key="apply_promote_headers"
                    ):
                        if confirm_headers:
                            new_df = transform_df.iloc[1:].copy()
                            new_df.columns = unique_headers
                            new_df.reset_index(drop=True, inplace=True)

                            st.session_state["transform_df"] = new_df
                            st.session_state["primary_dataset_df"] = new_df.copy()
                            st.session_state["calculated_columns_df"] = new_df.copy()
                            st.session_state["cleaned_df"] = new_df.copy()
                            st.session_state["transform_history"].append(
                                "Promoted first row to headers"
                            )

                            st.success("First row promoted to headers.")
                            st.rerun()
                        else:
                            st.warning("Please confirm the transformation.")

            # ------------------------------------------
            # 2. RENAME COLUMN
            # ------------------------------------------
            elif transform_action == "Rename Column":

                selected_column = st.selectbox(
                    "Select column",
                    transform_columns,
                    key="rename_transform_column"
                )

                new_column_name = st.text_input(
                    "New column name",
                    value=str(selected_column),
                    key="rename_transform_name"
                )

                confirm_rename = st.checkbox(
                    "Confirm column rename",
                    key="confirm_rename_transform"
                )

                if st.button("Apply Rename", key="apply_rename_transform"):

                    new_column_name = new_column_name.strip()

                    if not confirm_rename:
                        st.warning("Please confirm the change.")
                    elif not new_column_name:
                        st.error("Column name cannot be empty.")
                    elif (
                        new_column_name != selected_column
                        and new_column_name in transform_columns
                    ):
                        st.error("A column with that name already exists.")
                    else:
                        new_df = transform_df.rename(
                            columns={selected_column: new_column_name}
                        )

                        st.session_state["transform_df"] = new_df
                        st.session_state["primary_dataset_df"] = new_df.copy()
                        st.session_state["calculated_columns_df"] = new_df.copy()
                        st.session_state["cleaned_df"] = new_df.copy()
                        st.session_state["transform_history"].append(
                            f"Renamed {selected_column} to {new_column_name}"
                        )

                        st.success("Column renamed.")
                        st.rerun()

            # ------------------------------------------
            # 3. SPLIT COLUMN
            # ------------------------------------------
            elif transform_action == "Split Column":

                selected_column = st.selectbox(
                    "Select column to split",
                    transform_columns,
                    key="split_transform_column"
                )

                split_separator = st.text_input(
                    "Separator",
                    value=",",
                    key="split_transform_separator"
                )

                first_output_name = st.text_input(
                    "First output column name",
                    value=f"{selected_column}_1",
                    key="split_output_one"
                )

                second_output_name = st.text_input(
                    "Second output column name",
                    value=f"{selected_column}_2",
                    key="split_output_two"
                )

                split_preview = transform_df[selected_column].astype(
                    "string"
                ).str.split(
                    split_separator,
                    n=1,
                    expand=True
                ) if split_separator else None

                if split_preview is not None and split_preview.shape[1] >= 2:
                    preview_split = split_preview.copy()
                    preview_split.columns = ["Part 1", "Part 2"]

                    st.write("Preview:")
                    st.dataframe(
                        preview_split.head(10),
                        use_container_width=True
                    )

                confirm_split = st.checkbox(
                    "Confirm split",
                    key="confirm_split_transform"
                )

                if st.button("Apply Split", key="apply_split_transform"):

                    if not confirm_split:
                        st.warning("Please confirm the split.")
                    elif not split_separator:
                        st.error("Separator cannot be empty.")
                    elif not first_output_name.strip() or not second_output_name.strip():
                        st.error("Output column names cannot be empty.")
                    elif first_output_name == second_output_name:
                        st.error("Choose two different output column names.")
                    elif (
                        first_output_name in transform_columns
                        or second_output_name in transform_columns
                    ):
                        st.error(
                            "Output column names already exist. "
                            "Choose different names."
                        )
                    else:
                        split_result = transform_df[
                            selected_column
                        ].astype("string").str.split(
                            split_separator,
                            n=1,
                            expand=True
                        )

                        if split_result.shape[1] < 2:
                            st.error(
                                "The selected column did not split into two parts."
                            )
                        else:
                            new_df = transform_df.drop(
                                columns=[selected_column]
                            ).copy()

                            new_df[first_output_name] = split_result.iloc[:, 0]
                            new_df[second_output_name] = split_result.iloc[:, 1]

                            st.session_state["transform_df"] = new_df
                            st.session_state["primary_dataset_df"] = new_df.copy()
                            st.session_state["calculated_columns_df"] = new_df.copy()
                            st.session_state["cleaned_df"] = new_df.copy()
                            st.session_state["transform_history"].append(
                                f"Split {selected_column}"
                            )

                            st.success("Column split successfully.")
                            st.rerun()

            # ------------------------------------------
            # 4. EXTRACT TEXT
            # ------------------------------------------
            elif transform_action == "Extract Text":

                selected_column = st.selectbox(
                    "Select source column",
                    transform_columns,
                    key="extract_transform_column"
                )

                extract_method = st.selectbox(
                    "Extraction method",
                    [
                        "Text Before Separator",
                        "Text After Separator",
                        "First N Characters",
                        "Last N Characters"
                    ],
                    key="extract_transform_method"
                )

                if extract_method in [
                    "Text Before Separator",
                    "Text After Separator"
                ]:
                    extract_separator = st.text_input(
                        "Separator",
                        value="-",
                        key="extract_transform_separator"
                    )
                else:
                    extract_count = st.number_input(
                        "Number of characters",
                        min_value=1,
                        max_value=10000,
                        value=3,
                        key="extract_transform_count"
                    )

                extracted_name = st.text_input(
                    "New column name",
                    value=f"{selected_column}_extracted",
                    key="extract_transform_name"
                )

                if extract_method in [
                    "Text Before Separator",
                    "Text After Separator"
                ]:
                    if extract_separator:
                        if extract_method == "Text Before Separator":
                            extracted_preview = transform_df[
                                selected_column
                            ].astype("string").str.split(
                                extract_separator, n=1
                            ).str[0]
                        else:
                            extracted_preview = transform_df[
                                selected_column
                            ].astype("string").str.split(
                                extract_separator, n=1
                            ).str[1]
                    else:
                        extracted_preview = None
                elif extract_method == "First N Characters":
                    extracted_preview = transform_df[
                        selected_column
                    ].astype("string").str[:int(extract_count)]
                else:
                    extracted_preview = transform_df[
                        selected_column
                    ].astype("string").str[-int(extract_count):]

                if extracted_preview is not None:
                    st.write("Preview:")
                    st.dataframe(
                        pd.DataFrame({
                            selected_column: transform_df[selected_column],
                            "Extracted": extracted_preview
                        }).head(10),
                        use_container_width=True
                    )

                confirm_extract = st.checkbox(
                    "Confirm text extraction",
                    key="confirm_extract_transform"
                )

                if st.button("Apply Extraction", key="apply_extract_transform"):

                    if not confirm_extract:
                        st.warning("Please confirm extraction.")
                    elif not extracted_name.strip():
                        st.error("New column name cannot be empty.")
                    elif extracted_name in transform_columns:
                        st.error("That output column already exists.")
                    elif extracted_preview is None:
                        st.error("Enter a valid separator.")
                    else:
                        new_df = transform_df.copy()
                        new_df[extracted_name] = extracted_preview

                        st.session_state["transform_df"] = new_df
                        st.session_state["primary_dataset_df"] = new_df.copy()
                        st.session_state["calculated_columns_df"] = new_df.copy()
                        st.session_state["cleaned_df"] = new_df.copy()
                        st.session_state["transform_history"].append(
                            f"Extracted text from {selected_column}"
                        )

                        st.success("Text extracted successfully.")
                        st.rerun()

            # ------------------------------------------
            # 5. JOIN COLUMNS
            # ------------------------------------------
            elif transform_action == "Join Columns":

                columns_to_join = st.multiselect(
                    "Select at least two columns",
                    transform_columns,
                    key="join_transform_columns"
                )

                join_separator = st.text_input(
                    "Separator between values",
                    value=" ",
                    key="join_transform_separator"
                )

                joined_column_name = st.text_input(
                    "New joined column name",
                    value="Joined_Column",
                    key="join_transform_name"
                )

                if len(columns_to_join) >= 2:
                    joined_preview = transform_df[
                        columns_to_join
                    ].astype("string").fillna("").agg(
                        join_separator.join,
                        axis=1
                    )

                    st.write("Preview:")
                    st.dataframe(
                        pd.DataFrame({
                            "Joined Preview": joined_preview
                        }).head(10),
                        use_container_width=True
                    )

                confirm_join = st.checkbox(
                    "Confirm column join",
                    key="confirm_join_transform"
                )

                if st.button("Apply Join", key="apply_join_transform"):

                    if not confirm_join:
                        st.warning("Please confirm the join.")
                    elif len(columns_to_join) < 2:
                        st.error("Select at least two columns.")
                    elif not joined_column_name.strip():
                        st.error("New column name cannot be empty.")
                    elif joined_column_name in transform_columns:
                        st.error("That output column already exists.")
                    else:
                        new_df = transform_df.copy()

                        new_df[joined_column_name] = new_df[
                            columns_to_join
                        ].astype("string").fillna("").agg(
                            join_separator.join,
                            axis=1
                        )

                        st.session_state["transform_df"] = new_df
                        st.session_state["primary_dataset_df"] = new_df.copy()
                        st.session_state["calculated_columns_df"] = new_df.copy()
                        st.session_state["cleaned_df"] = new_df.copy()
                        st.session_state["transform_history"].append(
                            f"Joined columns into {joined_column_name}"
                        )

                        st.success("Columns joined successfully.")
                        st.rerun()

            # ------------------------------------------
            # 6. CHANGE DATA TYPE
            # ------------------------------------------
            elif transform_action == "Change Data Type":

                selected_column = st.selectbox(
                    "Select column",
                    transform_columns,
                    key="dtype_transform_column"
                )

                target_dtype = st.selectbox(
                    "Convert to",
                    ["Text", "Integer", "Decimal", "Date/Time"],
                    key="dtype_transform_choice"
                )

                confirm_dtype = st.checkbox(
                    "Confirm data type conversion",
                    key="confirm_dtype_transform"
                )

                if st.button("Apply Data Type", key="apply_dtype_transform"):

                    if not confirm_dtype:
                        st.warning("Please confirm the conversion.")
                    else:
                        try:
                            new_df = transform_df.copy()

                            if target_dtype == "Text":
                                new_df[selected_column] = (
                                    new_df[selected_column].astype("string")
                                )
                            elif target_dtype == "Integer":
                                new_df[selected_column] = pd.to_numeric(
                                    new_df[selected_column],
                                    errors="raise"
                                ).astype("Int64")
                            elif target_dtype == "Decimal":
                                new_df[selected_column] = pd.to_numeric(
                                    new_df[selected_column],
                                    errors="raise"
                                )
                            else:
                                new_df[selected_column] = pd.to_datetime(
                                    new_df[selected_column],
                                    errors="raise"
                                )

                            st.session_state["transform_df"] = new_df
                            st.session_state["primary_dataset_df"] = new_df.copy()
                            st.session_state["calculated_columns_df"] = new_df.copy()
                            st.session_state["cleaned_df"] = new_df.copy()
                            st.session_state["transform_history"].append(
                                f"Changed {selected_column} to {target_dtype}"
                            )

                            st.success("Data type changed.")
                            st.rerun()

                        except Exception as error:
                            st.error(
                                f"Conversion failed. Original data was kept: {error}"
                            )

            # ------------------------------------------
            # 7. FIND AND REPLACE
            # ------------------------------------------
            elif transform_action == "Find and Replace":

                selected_column = st.selectbox(
                    "Select column",
                    transform_columns,
                    key="replace_transform_column"
                )

                find_value = st.text_input(
                    "Find this text",
                    key="replace_transform_find"
                )

                replace_value = st.text_input(
                    "Replace with",
                    key="replace_transform_value"
                )

                if find_value:
                    replace_preview = transform_df[
                        selected_column
                    ].astype("string").str.replace(
                        find_value,
                        replace_value,
                        regex=False
                    )

                    st.write("Preview:")
                    st.dataframe(
                        pd.DataFrame({
                            "Original": transform_df[selected_column],
                            "After Replacement": replace_preview
                        }).head(10),
                        use_container_width=True
                    )

                confirm_replace = st.checkbox(
                    "Confirm find and replace",
                    key="confirm_replace_transform"
                )

                if st.button("Apply Find & Replace", key="apply_replace_transform"):

                    if not confirm_replace:
                        st.warning("Please confirm replacement.")
                    elif find_value == "":
                        st.error("Enter the text to find.")
                    else:
                        new_df = transform_df.copy()

                        new_df[selected_column] = new_df[
                            selected_column
                        ].astype("string").str.replace(
                            find_value,
                            replace_value,
                            regex=False
                        )

                        st.session_state["transform_df"] = new_df
                        st.session_state["primary_dataset_df"] = new_df.copy()
                        st.session_state["calculated_columns_df"] = new_df.copy()
                        st.session_state["cleaned_df"] = new_df.copy()
                        st.session_state["transform_history"].append(
                            f"Find and replace in {selected_column}"
                        )

                        st.success("Replacement applied.")
                        st.rerun()

            # ------------------------------------------
            # 8. TRIM WHITESPACE
            # ------------------------------------------
            elif transform_action == "Trim Whitespace":

                text_columns = [
                    column for column in transform_columns
                    if (
                        pd.api.types.is_object_dtype(transform_df[column])
                        or pd.api.types.is_string_dtype(transform_df[column])
                    )
                ]

                trim_columns = st.multiselect(
                    "Select text columns",
                    text_columns,
                    default=text_columns,
                    key="trim_transform_columns"
                )

                confirm_trim = st.checkbox(
                    "Confirm trimming",
                    key="confirm_trim_transform"
                )

                if st.button("Apply Trim", key="apply_trim_transform"):

                    if not confirm_trim:
                        st.warning("Please confirm trimming.")
                    elif not trim_columns:
                        st.warning("Select at least one text column.")
                    else:
                        new_df = transform_df.copy()

                        for column in trim_columns:
                            new_df[column] = new_df[
                                column
                            ].astype("string").str.strip()

                        st.session_state["transform_df"] = new_df
                        st.session_state["primary_dataset_df"] = new_df.copy()
                        st.session_state["calculated_columns_df"] = new_df.copy()
                        st.session_state["cleaned_df"] = new_df.copy()
                        st.session_state["transform_history"].append(
                            "Trimmed whitespace in selected columns"
                        )

                        st.success("Whitespace trimmed.")
                        st.rerun()

            # ------------------------------------------
            # 9. REMOVE COLUMNS
            # ------------------------------------------
            elif transform_action == "Remove Columns":

                columns_to_remove = st.multiselect(
                    "Select columns to remove",
                    transform_columns,
                    key="remove_transform_columns"
                )

                st.warning(
                    "Removed columns will be excluded from the transformed dataset."
                )

                confirm_remove = st.checkbox(
                    "I understand and confirm column removal",
                    key="confirm_remove_transform"
                )

                if st.button("Apply Column Removal", key="apply_remove_transform"):

                    if not confirm_remove:
                        st.warning("Please confirm column removal.")
                    elif not columns_to_remove:
                        st.warning("Select at least one column.")
                    elif len(columns_to_remove) >= len(transform_columns):
                        st.error("You cannot remove every column.")
                    else:
                        new_df = transform_df.drop(
                            columns=columns_to_remove
                        )

                        st.session_state["transform_df"] = new_df
                        st.session_state["primary_dataset_df"] = new_df.copy()
                        st.session_state["calculated_columns_df"] = new_df.copy()
                        st.session_state["cleaned_df"] = new_df.copy()
                        st.session_state["transform_history"].append(
                            "Removed columns: " + ", ".join(columns_to_remove)
                        )

                        st.success("Columns removed.")
                        st.rerun()

            # ------------------------------------------
            # TRANSFORMATION HISTORY + EXPORT
            # ------------------------------------------
            st.markdown("### 📋 Transformation History")

            history = st.session_state.get("transform_history", [])

            if history:
                for index, item in enumerate(history, start=1):
                    st.write(f"{index}. {item}")
            else:
                st.info("No transformations applied yet.")

            st.markdown("### Current Transformed Dataset")

            transformed_df = st.session_state["transform_df"]

            st.dataframe(
                transformed_df.head(100),
                use_container_width=True
            )

            transformed_csv = transformed_df.to_csv(
                index=False
            ).encode("utf-8-sig")

            st.download_button(
                "⬇️ Download Transformed CSV",
                data=transformed_csv,
                file_name="transformed_dataset.csv",
                mime="text/csv",
                key="download_transformed_csv"
            )

            st.divider()
            st.subheader("🔗 Append, Merge & Join Datasets")
            st.caption(
                "Combine another CSV, TSV, TXT, Excel, or JSON file with your "
                "current dataset. Your original uploaded dataset remains unchanged."
            )

            operation = st.selectbox(
                "Choose a dataset operation",
                ["Append Rows", "Merge on Matching Columns", "Join Side-by-Side"],
                key="dataset_combine_operation",
            )

            second_file = st.file_uploader(
                "Upload the second dataset",
                type=["csv", "tsv", "txt", "xlsx", "xls", "json"],
                key="dataset_combine_upload",
                help="Choose the file you want to combine with the current dataset.",
            )

            if second_file is not None:
                try:
                    second_df = load_dataset(second_file)

                    if second_df.empty:
                        st.warning("The second dataset has no data rows.")
                    else:
                        st.write("### Second Dataset Preview")
                        st.dataframe(second_df.head(10), use_container_width=True)

                        combined_df = None

                        if operation == "Append Rows":
                            st.write(
                                "Append stacks the rows. Columns are matched by name; "
                                "columns missing from either file are filled with empty values."
                            )
                            combined_df = pd.concat(
                                [df, second_df],
                                ignore_index=True,
                                sort=False,
                            )

                        elif operation == "Merge on Matching Columns":
                            common_columns = [
                                col for col in df.columns if col in second_df.columns
                            ]
                            if not common_columns:
                                st.warning(
                                    "These datasets have no identically named columns. "
                                    "Rename matching columns first, or use Join Side-by-Side."
                                )
                            else:
                                key_columns = st.multiselect(
                                    "Select matching key column(s)",
                                    options=common_columns,
                                    default=[common_columns[0]],
                                    key="dataset_merge_keys",
                                )
                                merge_how = st.selectbox(
                                    "Merge type",
                                    ["inner", "left", "right", "outer"],
                                    index=0,
                                    key="dataset_merge_how",
                                    help=(
                                        "Inner keeps matches only; left keeps all rows "
                                        "from the first dataset; right keeps all rows from "
                                        "the second; outer keeps all rows from both."
                                    ),
                                )
                                if key_columns:
                                    if st.button(
                                        "Create Merged Dataset",
                                        key="create_merged_dataset",
                                        type="primary",
                                    ):
                                        st.session_state["combined_result_promoted"] = False
                                        st.session_state["combined_result_df"] = df.merge(
                                            second_df,
                                            on=key_columns,
                                            how=merge_how,
                                            suffixes=("_left", "_right"),
                                        )
                                        st.session_state["combined_result_name"] = "merged_dataset.csv"
                                        st.session_state["combined_result_label"] = "Merged"
                                        st.rerun()
                                else:
                                    st.info("Select at least one matching key column.")

                        else:
                            st.write(
                                "Join places columns from the second dataset beside the "
                                "first dataset. Choose a matching key column to align rows, "
                                "or use row position if both files are already in the same order."
                            )
                            join_mode = st.radio(
                                "How should rows be aligned?",
                                ["Match by key column", "Match by row position"],
                                horizontal=True,
                                key="dataset_join_mode",
                            )

                            if join_mode == "Match by key column":
                                common_columns = [
                                    col for col in df.columns if col in second_df.columns
                                ]
                                if not common_columns:
                                    st.warning(
                                        "No identically named key columns were found. "
                                        "Use row position or rename the key columns first."
                                    )
                                else:
                                    join_key = st.selectbox(
                                        "Select key column",
                                        common_columns,
                                        key="dataset_join_key",
                                    )
                                    join_how = st.selectbox(
                                        "Join type",
                                        ["left", "inner", "right", "outer"],
                                        key="dataset_join_how",
                                    )
                                    if st.button(
                                        "Create Joined Dataset",
                                        key="create_key_joined_dataset",
                                        type="primary",
                                    ):
                                        st.session_state["combined_result_promoted"] = False
                                        st.session_state["combined_result_df"] = df.merge(
                                            second_df,
                                            on=join_key,
                                            how=join_how,
                                            suffixes=("_left", "_right"),
                                        )
                                        st.session_state["combined_result_name"] = "joined_dataset.csv"
                                        st.session_state["combined_result_label"] = "Joined"
                                        st.rerun()
                            else:
                                if len(df) != len(second_df):
                                    st.warning(
                                        f"The files have different row counts ({len(df):,} vs "
                                        f"{len(second_df):,}). A row-position join will keep "
                                        "all rows and may leave blank cells where one file ends."
                                    )
                                if st.button(
                                    "Join by Row Position",
                                    key="create_position_joined_dataset",
                                    type="primary",
                                ):
                                    left = df.reset_index(drop=True).copy()
                                    right = second_df.reset_index(drop=True).copy()
                                    duplicate_names = set(left.columns).intersection(right.columns)
                                    right = right.rename(
                                        columns={
                                            col: f"{col}_right"
                                            for col in duplicate_names
                                        }
                                    )
                                    st.session_state["combined_result_promoted"] = False
                                    st.session_state["combined_result_df"] = pd.concat(
                                        [left, right], axis=1
                                    )
                                    st.session_state["combined_result_name"] = "joined_dataset.csv"
                                    st.session_state["combined_result_label"] = "Joined"
                                    st.rerun()

                        if operation == "Append Rows":
                            if st.button(
                                "Create Appended Dataset",
                                key="create_appended_dataset",
                                type="primary",
                            ):
                                st.session_state["combined_result_promoted"] = False
                                st.session_state["combined_result_df"] = combined_df
                                st.session_state["combined_result_name"] = "appended_dataset.csv"
                                st.session_state["combined_result_label"] = "Appended"
                                st.rerun()

                except Exception as error:
                    st.error(f"Could not combine these datasets: {error}")

            if st.session_state.get("combined_result_df") is not None:
                result_df = st.session_state["combined_result_df"]
                result_name = st.session_state.get(
                    "combined_result_name", "combined_dataset.csv"
                )
                result_label = st.session_state.get(
                    "combined_result_label", "Combined"
                )
                st.markdown(f"### ✅ {result_label} Dataset Result")
                st.write(
                    f"Rows: {len(result_df):,}  |  Columns: {len(result_df.columns):,}"
                )
                st.dataframe(result_df.head(100), use_container_width=True)
                st.download_button(
                    f"⬇️ Download {result_label} Dataset (CSV)",
                    data=result_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=result_name,
                    mime="text/csv",
                    key="download_combined_result_csv",
                )
                excel_buffer_combined = io.BytesIO()
                with pd.ExcelWriter(excel_buffer_combined, engine="openpyxl") as writer:
                    result_df.to_excel(writer, sheet_name="Combined Data", index=False)
                st.download_button(
                    f"⬇️ Download {result_label} Dataset (Excel)",
                    data=excel_buffer_combined.getvalue(),
                    file_name=result_name.replace(".csv", ".xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_combined_result_excel",
                )
                if st.button("Clear Combined Result", key="clear_combined_result"):
                    st.session_state["combined_result_df"] = None
                    st.session_state["combined_result_name"] = "combined_dataset.csv"
                    st.session_state["combined_result_label"] = "Combined"
                    st.rerun()

            # Append/merge/join output is the new primary dataset, not a separate side file.
            if (isinstance(st.session_state.get("combined_result_df"), pd.DataFrame)
                    and not st.session_state.get("combined_result_promoted", False)):
                _combined_primary = st.session_state["combined_result_df"]
                st.session_state["primary_dataset_df"] = _combined_primary.copy()
                st.session_state["calculated_columns_df"] = _combined_primary.copy()
                st.session_state["cleaned_df"] = _combined_primary.copy()
                st.session_state["transform_df"] = _combined_primary.copy()
                st.session_state["combined_result_promoted"] = True
                st.session_state["primary_dataset_name"] = st.session_state.get("combined_result_label", "Combined")
                df = _combined_primary.copy()

            st.divider()
            st.subheader("🧹 Smart Data Cleaning")

            file_bytes = uploaded_file.getvalue()
            source_signature = hashlib.sha256(file_bytes).hexdigest()

            if st.session_state.get("cleaning_source") != source_signature:
                st.session_state["cleaning_source"] = source_signature
                st.session_state["cleaning_messages"] = []
            if not isinstance(st.session_state.get("cleaned_df"), pd.DataFrame):
                st.session_state["cleaned_df"] = df.copy()
            original_df = df.copy()

            st.write(
                "Clean missing values, remove duplicates, "
                "and compare your dataset before and after cleaning."
            )

            st.markdown("### 📊 Before Cleaning")

            before_col1, before_col2, before_col3 = st.columns(3)

            before_col1.metric("Total Rows", len(original_df))
            before_col2.metric(
                "Missing Values",
                int(original_df.isna().sum().sum())
            )
            before_col3.metric(
                "Duplicate Rows",
                int(original_df.duplicated().sum())
            )

            st.divider()

            st.markdown("### 1. Handle Missing Values")

            missing_columns = original_df.columns[
                original_df.isna().any()
            ].tolist()

            if missing_columns:
                selected_columns = st.multiselect(
                    "Select columns to fill",
                    options=missing_columns,
                    default=missing_columns,
                    key="cleaning_columns"
                )

                strategy = st.selectbox(
                    "Choose a missing-value strategy",
                    [
                        "Median",
                        "Mean",
                        "Mode",
                        "Custom Value",
                        "Leave Unchanged"
                    ],
                    key="cleaning_strategy"
                )

                custom_value = None

                if strategy == "Custom Value":
                    custom_value = st.text_input(
                        "Enter the value to fill missing cells",
                        key="custom_missing_value"
                    )

                if strategy in ["Mean", "Median"]:
                    st.caption(
                        "Mean and median work only with numeric columns. "
                        "Non-numeric columns will be skipped."
                    )

                if strategy == "Mode":
                    st.caption(
                        "Mode fills missing cells with the most frequent "
                        "non-missing value in each selected column."
                    )

            else:
                selected_columns = []
                strategy = "Leave Unchanged"
                custom_value = None

                st.success("No missing values found in this dataset!")

            st.divider()

            st.markdown("### 2. Other Cleaning Operations")

            remove_duplicates = st.checkbox(
                "Remove duplicate rows",
                value=False,
                key="remove_duplicate_rows"
            )

            drop_missing = st.checkbox(
                "Remove rows containing any remaining missing values",
                value=False,
                key="drop_incomplete_rows"
            )

            st.warning(
                "Removing incomplete rows can delete useful data. "
                "Check the results before downloading."
            )

            st.divider()

            if st.button(
                "✨ Apply Cleaning Operations",
                type="primary",
                key="apply_smart_cleaning"
            ):
                cleaned_df = original_df.copy()
                cleaning_messages = []

                if strategy != "Leave Unchanged":
                    for column in selected_columns:

                        if not cleaned_df[column].isna().any():
                            continue

                        if strategy == "Median":
                            if pd.api.types.is_numeric_dtype(
                                cleaned_df[column]
                            ):
                                fill_value = cleaned_df[column].median()
                            else:
                                cleaning_messages.append(
                                    f"Skipped '{column}': median requires "
                                    "a numeric column."
                                )
                                continue

                        elif strategy == "Mean":
                            if pd.api.types.is_numeric_dtype(
                                cleaned_df[column]
                            ):
                                fill_value = cleaned_df[column].mean()
                            else:
                                cleaning_messages.append(
                                    f"Skipped '{column}': mean requires "
                                    "a numeric column."
                                )
                                continue

                        elif strategy == "Mode":
                            modes = cleaned_df[column].mode(dropna=True)

                            if modes.empty:
                                cleaning_messages.append(
                                    f"Skipped '{column}': no existing "
                                    "values are available to calculate mode."
                                )
                                continue

                            fill_value = modes.iloc[0]

                        elif strategy == "Custom Value":
                            if custom_value is None or custom_value.strip() == "":
                                cleaning_messages.append(
                                    "Custom value was blank. Missing values "
                                    "were not filled."
                                )
                                break

                            fill_value = custom_value

                            if pd.api.types.is_numeric_dtype(
                                cleaned_df[column]
                            ):
                                try:
                                    fill_value = float(custom_value)
                                except ValueError:
                                    cleaning_messages.append(
                                        f"Skipped '{column}': enter a valid "
                                        "number for this numeric column."
                                    )
                                    continue

                        else:
                            continue

                        cleaned_df[column] = cleaned_df[column].fillna(
                            fill_value
                        )

                if remove_duplicates:
                    rows_before = len(cleaned_df)
                    cleaned_df = cleaned_df.drop_duplicates()
                    removed_duplicates = rows_before - len(cleaned_df)

                    cleaning_messages.append(
                        f"Removed {removed_duplicates} duplicate row(s)."
                    )

                if drop_missing:
                    rows_before = len(cleaned_df)
                    cleaned_df = cleaned_df.dropna()
                    removed_rows = rows_before - len(cleaned_df)

                    cleaning_messages.append(
                        f"Removed {removed_rows} row(s) containing "
                        "remaining missing values."
                    )

                st.session_state["cleaned_df"] = cleaned_df.copy()
                st.session_state["primary_dataset_df"] = cleaned_df.copy()
                st.session_state["calculated_columns_df"] = cleaned_df.copy()
                st.session_state["transform_df"] = cleaned_df.copy()
                st.session_state["cleaning_messages"] = cleaning_messages
                st.session_state["cleaning_applied"] = True

            cleaned_df = st.session_state.get(
                "cleaned_df",
                original_df.copy()
            )

            if st.session_state.get("cleaning_applied", False):

                st.markdown("### ✅ After Cleaning")

                after_col1, after_col2, after_col3 = st.columns(3)

                after_col1.metric(
                    "Total Rows",
                    len(cleaned_df),
                    delta=len(cleaned_df) - len(original_df)
                )

                after_col2.metric(
                    "Missing Values",
                    int(cleaned_df.isna().sum().sum()),
                    delta=(
                        int(original_df.isna().sum().sum())
                        - int(cleaned_df.isna().sum().sum())
                    )
                )

                after_col3.metric(
                    "Duplicate Rows",
                    int(cleaned_df.duplicated().sum()),
                    delta=(
                        int(original_df.duplicated().sum())
                        - int(cleaned_df.duplicated().sum())
                    )
                )

                for message in st.session_state.get(
                    "cleaning_messages", []
                ):
                    st.info(message)

                st.markdown("### 👀 Cleaned Dataset Preview")

                st.dataframe(
                    cleaned_df.head(100),
                    use_container_width=True
                )

                csv_data = cleaned_df.to_csv(index=False).encode("utf-8-sig")

                st.download_button(
                    label="⬇️ Download Cleaned CSV",
                    data=csv_data,
                    file_name="cleaned_dataset.csv",
                    mime="text/csv",
                    key="download_cleaned_csv"
                )

                excel_buffer = io.BytesIO()

                with pd.ExcelWriter(
                    excel_buffer,
                    engine="openpyxl"
                ) as writer:

                    cleaned_df.to_excel(
                        writer,
                        sheet_name="Cleaned Data",
                        index=False
                    )

                    quality_report = pd.DataFrame({
                        "Column": cleaned_df.columns,
                        "Data Type": [
                            str(dtype) for dtype in cleaned_df.dtypes
                        ],
                        "Missing Values": [
                            int(value)
                            for value in cleaned_df.isna().sum()
                        ],
                        "Missing Percentage": [
                            round(value * 100 / len(cleaned_df), 2)
                            if len(cleaned_df) > 0 else 0
                            for value in cleaned_df.isna().sum()
                        ],
                        "Unique Values": [
                            int(cleaned_df[column].nunique())
                            for column in cleaned_df.columns
                        ]
                    })

                    quality_report.to_excel(
                        writer,
                        sheet_name="Data Quality",
                        index=False
                    )

                st.download_button(
                    label="⬇️ Download Excel Report",
                    data=excel_buffer.getvalue(),
                    file_name="data_analysis_report.xlsx",
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    key="download_cleaned_excel"
                )

            else:
                st.info(
                    "Choose your cleaning options and click "
                    "'Apply Cleaning Operations' to see the results."
                )

        with tab7:
            st.subheader("💬 Ask Your Data")
            st.write(
                "Ask a question about your current working dataset in plain English. "
                "This first version answers common analysis questions locally, without an API key."
            )
            st.caption("Examples: What is the total sales? · Average quantity · Top 5 products by sales · Sales by region · Which column has the most missing values?")

            ask_question = st.text_input(
                "What would you like to know?",
                placeholder="e.g. Show the top 5 products by Sales",
                key="ask_data_question"
            )
            ask_numeric_cols = df.select_dtypes(include="number").columns.tolist()
            ask_all_cols = df.columns.tolist()
            ask_default_metric = ask_numeric_cols[0] if ask_numeric_cols else ask_all_cols[0]
            ask_col1, ask_col2 = st.columns(2)
            with ask_col1:
                ask_metric = st.selectbox(
                    "Numeric measure (used when a question doesn't name one)",
                    ask_numeric_cols if ask_numeric_cols else ask_all_cols,
                    key="ask_data_metric"
                )
            with ask_col2:
                ask_category = st.selectbox(
                    "Group/category column (optional fallback)",
                    ["(Automatic)"] + ask_all_cols,
                    key="ask_data_category"
                )

            def _ask_format(value):
                try:
                    if pd.isna(value):
                        return "Not available"
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        return f"{value:,.2f}" if abs(float(value)) % 1 else f"{value:,.0f}"
                except Exception:
                    pass
                return str(value)

            if st.button("Answer question", type="primary", key="ask_data_submit"):
                if not ask_question.strip():
                    st.warning("Enter a question first.")
                else:
                    q = ask_question.strip().lower()
                    # Resolve columns mentioned in the question, preferring the longest names.
                    mentioned = [c for c in sorted(ask_all_cols, key=lambda x: len(str(x)), reverse=True)
                                 if str(c).strip() and str(c).lower() in q]
                    metric = next((c for c in mentioned if c in ask_numeric_cols), ask_metric)
                    category = next((c for c in mentioned if c not in ask_numeric_cols), None)
                    if category is None and ask_category != "(Automatic)":
                        category = ask_category
                    result_df = None
                    answer_text = None
                    try:
                        if any(word in q for word in ["missing", "null", "blank", "empty"]):
                            missing = df.isna().sum().sort_values(ascending=False)
                            result_df = pd.DataFrame({"Column": missing.index, "Missing values": missing.values})
                            answer_text = f"The dataset contains **{int(missing.sum()):,} missing values** across {int((missing > 0).sum())} columns."
                        elif any(word in q for word in ["duplicate", "duplicated"]):
                            answer_text = f"The dataset contains **{int(df.duplicated().sum()):,} duplicate rows**."
                        elif any(word in q for word in ["how many rows", "row count", "number of rows", "total rows", "record count"]):
                            answer_text = f"The dataset contains **{len(df):,} rows** and **{len(df.columns):,} columns**."
                        elif any(word in q for word in ["how many columns", "column count", "number of columns", "total columns"]):
                            answer_text = f"The dataset contains **{len(df.columns):,} columns**."
                        elif any(word in q for word in ["top ", "highest", "most", "best", "largest"]):
                            import re
                            n_match = re.search(r"top\s+(\d+)", q)
                            n = min(max(int(n_match.group(1)), 1), 100) if n_match else 5
                            if category is None:
                                category_candidates = [c for c in ask_all_cols if c != metric]
                                category = category_candidates[0] if category_candidates else None
                            if category is not None and metric in ask_numeric_cols:
                                result_df = df.groupby(category, dropna=False)[metric].sum().sort_values(ascending=False).head(n).reset_index()
                                answer_text = f"Top {len(result_df)} values of **{category}** ranked by total **{metric}**."
                            else:
                                answer_text = f"The selected measure is **{metric}**. Choose a category column to rank values."
                        elif any(word in q for word in ["by ", "per ", "group", "compare", "breakdown", "across"]):
                            if category is None:
                                category_candidates = [c for c in ask_all_cols if c != metric]
                                category = category_candidates[0] if category_candidates else None
                            if category is not None and metric in ask_numeric_cols:
                                agg = "mean" if any(word in q for word in ["average", "avg", "mean"]) else "sum"
                                result_df = df.groupby(category, dropna=False)[metric].agg(agg).sort_values(ascending=False).reset_index()
                                result_df = result_df.rename(columns={metric: f"{agg.title()} of {metric}"})
                                answer_text = f"{agg.title()} **{metric}** grouped by **{category}**."
                            else:
                                answer_text = "I couldn't identify a suitable category and numeric measure. Select them above and try again."
                        elif any(word in q for word in ["average", "avg", "mean"]):
                            if metric in ask_numeric_cols:
                                answer_text = f"Average **{metric}**: **{_ask_format(df[metric].mean())}**."
                            else:
                                answer_text = f"**{metric}** isn't numeric, so I can't calculate its average. Choose a numeric measure above."
                        elif any(word in q for word in ["minimum", "minimum value", "lowest", "smallest", "least"]):
                            if metric in ask_numeric_cols:
                                answer_text = f"Minimum **{metric}**: **{_ask_format(df[metric].min())}**."
                            else:
                                answer_text = f"**{metric}** isn't numeric. Choose a numeric measure above."
                        elif any(word in q for word in ["maximum", "maximum value", "highest value", "largest value"]):
                            if metric in ask_numeric_cols:
                                answer_text = f"Maximum **{metric}**: **{_ask_format(df[metric].max())}**."
                            else:
                                answer_text = f"**{metric}** isn't numeric. Choose a numeric measure above."
                        elif any(word in q for word in ["count", "how many", "number of"]):
                            if category is not None:
                                answer_text = f"There are **{int(df[category].nunique(dropna=True)):,} distinct values** in **{category}**."
                            else:
                                answer_text = f"There are **{len(df):,} rows**. Select a category column above to count distinct values in a field."
                        elif any(word in q for word in ["total", "sum", "revenue", "sales", "profit", "amount"]):
                            if metric in ask_numeric_cols:
                                answer_text = f"Total **{metric}**: **{_ask_format(df[metric].sum())}**."
                            else:
                                answer_text = f"**{metric}** isn't numeric. Choose a numeric measure above."
                        elif any(word in q for word in ["describe", "summary", "statistics", "distribution"]):
                            result_df = df.describe(include="all").transpose().reset_index(names="Column")
                            answer_text = "Here is a statistical summary of the current working dataset."
                        else:
                            answer_text = (
                                "I couldn't confidently map that question to a supported operation yet. "
                                "Try asking for a total, average, minimum, maximum, top N, grouped breakdown, "
                                "row count, duplicate count, or missing-value summary."
                            )
                        if answer_text:
                            st.markdown(answer_text)
                        if result_df is not None:
                            st.dataframe(result_df, use_container_width=True, hide_index=True)
                            if len(result_df.columns) >= 2 and len(result_df) > 0:
                                st.download_button(
                                    "Download answer as CSV",
                                    data=result_df.to_csv(index=False).encode("utf-8-sig"),
                                    file_name="ask_your_data_answer.csv",
                                    mime="text/csv",
                                    key="ask_data_download"
                                )
                    except Exception as ask_error:
                        st.error(f"Couldn't answer that question: {type(ask_error).__name__}: {ask_error}")
                        st.info("Try a simpler question or select the measure and category explicitly above.")

        with tab8:
            st.subheader("🗣️ Conversational AI Dashboard Builder")
            st.write("Optional guided workflow: tell the builder what you want to analyse, review its recommendations, then send the approved setup to the existing AI Dashboard Advisor. Your AI Advisor remains the main automatic dashboard feature.")
            st.info("This builder works locally without an API key. For natural-language interpretation by an LLM, you may optionally enter an OpenAI API key below. Without a key, your selections still configure the existing dashboard builder.")

            _conv_numeric = [c for c in df.select_dtypes(include="number").columns if not any(t in str(c).lower() for t in (" id", "id ", "identifier", "phone", "postal", "zip", "code"))]
            _conv_date = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c]) or any(t in str(c).lower() for t in ("date", "time", "month", "year"))]
            _conv_cats = [c for c in df.columns if c not in _conv_numeric and c not in _conv_date]
            _conv_metrics = _conv_numeric or df.columns.tolist()
            _conv_default_metric = next((c for c in _conv_metrics if any(t in str(c).lower() for t in ("sales", "revenue", "profit", "amount", "total", "quantity", "cost"))), _conv_metrics[0] if _conv_metrics else None)

            with st.expander("Optional LLM connection (not required)", expanded=False):
                st.caption("The API key is used only for this session and is not written to the project file. Dataset rows are not sent; only column names, data types, and your request are sent to the model.")
                _conv_api_key = st.text_input("OpenAI API key", type="password", key="conv_openai_api_key", placeholder="Optional — leave blank for local guided mode")
                _conv_model = st.text_input("Model name", value="gpt-4o-mini", key="conv_openai_model")

            _conv_goal_options = ["Complete business dashboard", "Sales / revenue performance", "Profitability analysis", "Customer analysis", "Product analysis", "Operations / delivery", "Compare categories", "Explore data quality", "Custom goal"]
            _conv_goal = st.selectbox("1. What do you want to understand?", _conv_goal_options, key="conv_goal")
            _conv_custom_goal = st.text_input("Describe your goal", key="conv_custom_goal", placeholder="e.g. Find why profit dropped and compare regions") if _conv_goal == "Custom goal" else ""
            _conv_goal_text = _conv_custom_goal.strip() if _conv_goal == "Custom goal" else _conv_goal
            _conv_metric_defaults = [_conv_default_metric] if _conv_default_metric is not None else []
            _conv_kpis = st.multiselect("2. Choose KPI measures", _conv_metrics, default=_conv_metric_defaults, key="conv_kpis")
            _conv_chart_options = ["Bar comparison", "Line trend", "Donut share", "Stacked bar", "Scatter relationship", "Histogram", "Data table"]
            _conv_charts = st.multiselect("3. Choose visualizations", _conv_chart_options, default=["Bar comparison", "Line trend", "Donut share", "Data table"], key="conv_charts")
            _conv_dimensions = st.multiselect("4. Which categories or date fields should be used?", list(df.columns), default=([_conv_date[0]] if _conv_date else []) + ([_conv_cats[0]] if _conv_cats else []), key="conv_dimensions")
            _conv_filters = st.multiselect("5. Which fields should be available as dashboard filters?", list(df.columns), default=_conv_cats[:2], key="conv_filters")
            _conv_request = st.text_area("6. Additional instructions", key="conv_request", placeholder="e.g. Show top 10 products, compare regions, use monthly trends")

            _conv_apply = st.button("Build recommendation and send to AI Advisor", type="primary", key="conv_apply_setup")
            if _conv_apply:
                if not _conv_kpis and not _conv_charts:
                    st.warning("Choose at least one KPI or visualization.")
                else:
                    _conv_recommendation = {"title": "Data Insights Dashboard", "subtitle": _conv_goal_text, "kpis": [], "charts": [], "filters": _conv_filters, "notes": _conv_request}
                    _goal_lower = (_conv_goal_text + " " + _conv_request).lower()
                    if any(t in _goal_lower for t in ("sales", "revenue")):
                        _conv_recommendation["title"] = "Sales Performance Dashboard"
                    elif "profit" in _goal_lower:
                        _conv_recommendation["title"] = "Profitability Analysis Dashboard"
                    elif "customer" in _goal_lower:
                        _conv_recommendation["title"] = "Customer Insights Dashboard"
                    elif "product" in _goal_lower:
                        _conv_recommendation["title"] = "Product Performance Dashboard"
                    for _metric in _conv_kpis:
                        _mname = str(_metric).lower()
                        _agg = "Sum" if any(t in _mname for t in ("sales", "revenue", "profit", "amount", "total", "cost", "quantity", "units")) else "Average"
                        _conv_recommendation["kpis"].append({"column": _metric, "aggregation": _agg, "label": f"{_agg} of {_metric}"})
                    _dim1 = next((c for c in _conv_dimensions if c in _conv_date), None) or next((c for c in _conv_dimensions if c in _conv_cats), None) or (_conv_cats[0] if _conv_cats else (_conv_date[0] if _conv_date else None))
                    _dim2 = next((c for c in _conv_dimensions if c != _dim1 and c in _conv_cats), None) or next((c for c in _conv_cats if c != _dim1), None)
                    _measure = _conv_kpis[0] if _conv_kpis else (_conv_numeric[0] if _conv_numeric else None)
                    _valid_chart_types = set(_conv_chart_options)
                    for _idx, _chart_type in enumerate(_conv_charts, 1):
                        _x = _dim1
                        _y = _measure or "(Count rows)"
                        if _chart_type == "Line trend" and _conv_date:
                            _x = next((c for c in _conv_dimensions if c in _conv_date), _conv_date[0])
                        if _chart_type == "Scatter relationship":
                            if len(_conv_numeric) < 2:
                                continue
                            _x, _y = _conv_numeric[0], _conv_numeric[1]
                        elif _chart_type == "Histogram":
                            _x = _measure or (_conv_numeric[0] if _conv_numeric else _dim1)
                            _y = "(Count rows)"
                        elif _chart_type in ("Donut share", "Stacked bar") and _dim2 and _chart_type == "Stacked bar":
                            pass
                        if _x is None:
                            _x = _conv_numeric[0] if _conv_numeric else (df.columns[0] if len(df.columns) else None)
                        _title = f"{_y} by {_x}" if _x is not None else _chart_type
                        _chart_cfg = {"type": _chart_type, "title": _title, "position": _idx, "x": _x, "y": _y, "aggregation": "Sum" if _measure in _conv_numeric else "Count", "legend": _dim2 if _chart_type == "Stacked bar" and _dim2 else None, "latitude": None, "longitude": None, "location": None, "details": None}
                        if _chart_type in _valid_chart_types:
                            _conv_recommendation["charts"].append(_chart_cfg)

                    # Optional LLM enhancement. It receives schema metadata, never raw rows.
                    if _conv_api_key.strip():
                        try:
                            import urllib.request
                            _schema = [{"name": str(c), "dtype": str(df[c].dtype), "unique_values": int(df[c].nunique(dropna=True))} for c in df.columns]
                            _llm_prompt = {"task": "Improve the dashboard title, subtitle, KPI aggregations/labels, and chart titles/field choices using only the provided schema and user request. Return JSON only with keys title, subtitle, notes. Do not invent columns or claim data findings.", "goal": _conv_goal_text, "instructions": _conv_request, "selected_kpis": _conv_recommendation["kpis"], "selected_charts": _conv_recommendation["charts"], "schema": _schema}
                            _body = json.dumps({"model": _conv_model.strip() or "gpt-4o-mini", "messages": [{"role": "system", "content": "You are a careful dashboard designer. Return valid JSON only. Never invent field names or factual findings."}, {"role": "user", "content": json.dumps(_llm_prompt)}], "response_format": {"type": "json_object"}, "temperature": 0.2}).encode("utf-8")
                            _req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=_body, headers={"Authorization": "Bearer " + _conv_api_key.strip(), "Content-Type": "application/json"}, method="POST")
                            with urllib.request.urlopen(_req, timeout=25) as _resp:
                                _llm_data = json.loads(_resp.read().decode("utf-8"))
                            _llm_content = _llm_data["choices"][0]["message"]["content"]
                            _llm_result = json.loads(_llm_content)
                            if isinstance(_llm_result.get("title"), str) and _llm_result["title"].strip():
                                _conv_recommendation["title"] = _llm_result["title"].strip()[:120]
                            if isinstance(_llm_result.get("subtitle"), str) and _llm_result["subtitle"].strip():
                                _conv_recommendation["subtitle"] = _llm_result["subtitle"].strip()[:240]
                            if isinstance(_llm_result.get("notes"), str) and _llm_result["notes"].strip():
                                _conv_recommendation["llm_notes"] = _llm_result["notes"].strip()[:2000]
                            st.success("Optional AI model improved the dashboard brief using schema metadata.")
                        except Exception as _llm_error:
                            st.warning(f"Optional LLM request failed ({type(_llm_error).__name__}). The local recommendation is still available; check the key, model name, and network connection.")

                    st.session_state["pending_conv_advisor_config"] = _conv_recommendation
                    st.success("Recommendation prepared. The app will pass it to the existing AI Dashboard Advisor so you can review, edit, and render it.")
                    st.rerun()

            _existing_conv = st.session_state.get("conv_dashboard_recommendation")
            if isinstance(_existing_conv, dict):
                st.markdown("#### Latest conversational recommendation")
                st.markdown(f"**{_existing_conv.get('title', 'Dashboard')}**")
                st.caption(_existing_conv.get("subtitle", ""))
                if _existing_conv.get("notes"):
                    st.write("Your instructions:", _existing_conv["notes"])
                if _existing_conv.get("llm_notes"):
                    st.write("AI design notes:", _existing_conv["llm_notes"])
                st.write("**KPIs**", ", ".join(x.get("label", x.get("column", "")) for x in _existing_conv.get("kpis", [])) or "No KPIs selected")
                st.write("**Charts**", ", ".join(x.get("title", x.get("type", "Chart")) for x in _existing_conv.get("charts", [])) or "No charts selected")
                st.caption("This recommendation does not replace the main AI Advisor; it preconfigures its existing editable dashboard controls.")

    except Exception as error:
        st.error(f"Unable to load or analyse this dataset: {type(error).__name__}: {error}")
        st.info(
            "Check that the file is not open in another program and is a valid CSV, TSV, TXT, "
            "XLSX, XLS, or JSON file. For Excel files, try saving a fresh .xlsx copy. "
            "If the file is very large, try a smaller CSV sample to isolate the issue."
        )

else:
    st.info(
        "Upload a CSV, TSV, TXT, Excel, or JSON file to begin."
    )

    st.markdown(
        """
        ### What this application can do

        - Inspect dataset structure
        - Identify missing values and duplicates
        - Generate descriptive statistics
        - Create basic charts
        - Apply optional cleaning operations
        - Export cleaned data to CSV or Excel
        """
    )
