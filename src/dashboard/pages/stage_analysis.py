"""
Stage Analysis Page.

Deep dive into each pipeline stage's performance.
"""

import pandas as pd
import streamlit as st

from dashboard.components.sidebar import render_sidebar
from services.metrics_service import job_metrics_service

# Configure page
st.set_page_config(
    page_title="Stage Analysis - Pipeline Health Dashboard",
    page_icon="🔄",
    layout="wide",
)

# Render sidebar
render_sidebar()

# Main content
st.title("🔄 Stage Analysis")

# Check if date is selected
if not st.session_state.get("selected_date"):
    st.warning("⚠️ Please select a date from the calendar in the sidebar.")
    st.stop()

selected_date = st.session_state.selected_date
st.markdown(f"### Date: {selected_date}")
st.markdown("---")

# Fetch data
with st.spinner("Loading stage metrics..."):
    aggregate = job_metrics_service.get_pipeline_health_metrics(selected_date)
    companies = job_metrics_service.get_companies_by_date(selected_date)

if not aggregate:
    st.error(f"❌ No data found for {selected_date}")
    st.stop()

# === STAGE SELECTOR ===
st.subheader("📊 Select Stage")

stage_tabs = st.tabs([f"Stage {i}" for i in range(1, 6)])

for stage_idx, tab in enumerate(stage_tabs):
    stage = stage_idx + 1

    with tab:
        st.markdown(f"## Stage {stage} Performance")

        # Get stage metrics
        total_processed = getattr(aggregate, f"stage_{stage}_total_processed")
        success_rate = getattr(aggregate, f"stage_{stage}_success_rate")
        avg_time = getattr(aggregate, f"stage_{stage}_avg_execution_seconds")

        # Calculate completed and failed
        completed = int(total_processed * success_rate / 100) if success_rate > 0 else 0
        failed = total_processed - completed

        # === STAGE METRICS ===
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("📊 Processed", total_processed)

        with col2:
            st.metric("✅ Completed", completed)

        with col3:
            st.metric("❌ Failed", failed)

        with col4:
            st.metric("⏱️ Avg Time (s)", f"{avg_time:.2f}")

        st.markdown("---")

        # === SUCCESS RATE ===
        st.markdown("### Success Rate")

        col1, col2 = st.columns([1, 3])

        with col1:
            # Determine color
            if success_rate >= 95:
                color_emoji = "🟢"
            elif success_rate >= 70:
                color_emoji = "🟡"
            else:
                color_emoji = "🔴"

            st.markdown(f"## {color_emoji} {success_rate:.1f}%")

        with col2:
            st.progress(success_rate / 100)

        st.markdown("---")

        # === COMPANY-LEVEL DETAILS ===
        st.markdown("### Company Performance")

        # Get company-level data for this stage
        stage_company_data = []
        for company in companies:
            status = getattr(company, f"stage_{stage}_status", None)
            processed = getattr(company, f"stage_{stage}_jobs_processed", 0)
            completed_jobs = getattr(company, f"stage_{stage}_jobs_completed", 0)
            exec_time = getattr(company, f"stage_{stage}_execution_seconds", 0)
            error = getattr(company, f"stage_{stage}_error_message", None)

            stage_company_data.append(
                {
                    "Company": company.company_name,
                    "Status": status or "N/A",
                    "Processed": processed or 0,
                    "Completed": completed_jobs or 0,
                    "Time (s)": f"{exec_time:.2f}" if exec_time else "0.00",
                    "Error": error or "None",
                }
            )

        # Create DataFrame
        df_companies = pd.DataFrame(stage_company_data)

        # Filter options
        col1, col2 = st.columns(2)

        with col1:
            status_filter = st.selectbox(
                "Filter by Status",
                options=["All", "success", "failed", "N/A"],
                key=f"stage_{stage}_status_filter",
            )

        with col2:
            sort_by = st.selectbox(
                "Sort by",
                options=["Company", "Status", "Processed", "Time (s)"],
                key=f"stage_{stage}_sort",
            )

        # Apply filters
        if status_filter != "All":
            df_filtered = df_companies[df_companies["Status"] == status_filter]
        else:
            df_filtered = df_companies

        # Sort
        if sort_by == "Time (s)":
            df_filtered = df_filtered.sort_values(by="Time (s)", ascending=False)
        else:
            df_filtered = df_filtered.sort_values(by=sort_by)

        st.caption(f"Showing {len(df_filtered)} of {len(df_companies)} companies")

        # Display table
        st.dataframe(
            df_filtered,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")

        # === FAILURE ANALYSIS ===
        st.markdown("### ⚠️ Failure Analysis")

        failures = df_companies[df_companies["Status"] == "failed"]

        if len(failures) > 0:
            st.warning(f"Found {len(failures)} failed companies in Stage {stage}")

            # Group errors
            error_groups: dict[str, list[str]] = {}
            for _, row in failures.iterrows():
                error_msg = row["Error"]
                if error_msg != "None":
                    if error_msg not in error_groups:
                        error_groups[error_msg] = []
                    error_groups[error_msg].append(row["Company"])

            # Display error groups
            if error_groups:
                st.markdown("#### Error Messages")
                for error_msg, company_list in error_groups.items():
                    with st.expander(f"🔴 {error_msg} ({len(company_list)} companies)"):
                        st.write("**Affected Companies:**")
                        for company in company_list:
                            st.write(f"- {company}")
            else:
                st.info("No error messages recorded")

            # Show failed companies table
            st.markdown("#### Failed Companies")
            st.dataframe(
                failures[["Company", "Processed", "Completed", "Time (s)", "Error"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success(f"✅ No failures in Stage {stage}!")

        st.markdown("---")

        # === EXECUTION TIME STATISTICS ===
        st.markdown("### ⏱️ Execution Time Statistics")

        # Filter out zero times
        exec_times = [
            float(row["Time (s)"])
            for _, row in df_companies.iterrows()
            if float(row["Time (s)"]) > 0
        ]

        if exec_times:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Min", f"{min(exec_times):.2f}s")

            with col2:
                st.metric("Max", f"{max(exec_times):.2f}s")

            with col3:
                st.metric("Avg", f"{sum(exec_times) / len(exec_times):.2f}s")

            with col4:
                # Calculate median
                sorted_times = sorted(exec_times)
                median = sorted_times[len(sorted_times) // 2]
                st.metric("Median", f"{median:.2f}s")
        else:
            st.info("No execution time data available")

st.caption("🔄 Pipeline Health Dashboard - Stage Analysis")
