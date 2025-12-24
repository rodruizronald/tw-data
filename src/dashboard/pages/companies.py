"""
Companies Page.

Displays individual company processing details for selected date.
"""

import pandas as pd
import streamlit as st

from dashboard.components.metrics_cards import render_status_badge
from dashboard.components.sidebar import render_sidebar
from services.metrics_service import job_metrics_service

# Configure page
st.set_page_config(
    page_title="Companies - Pipeline Health Dashboard",
    page_icon="🏢",
    layout="wide",
)

# Render sidebar
render_sidebar()

# Main content
st.title("🏢 Company Details")

# Check if date is selected
if not st.session_state.get("selected_date"):
    st.warning("⚠️ Please select a date from the calendar in the sidebar.")
    st.stop()

selected_date = st.session_state.selected_date
st.markdown(f"### Date: {selected_date}")
st.markdown("---")

# Fetch data
with st.spinner("Loading company metrics..."):
    companies = job_metrics_service.get_companies_by_date(selected_date)

if not companies:
    st.error(f"❌ No company data found for {selected_date}")
    st.stop()

# === SUMMARY METRICS ===
st.subheader("📊 Summary")

col1, col2, col3, col4 = st.columns(4)

success_count = sum(1 for c in companies if c.overall_status == "success")
partial_count = sum(1 for c in companies if c.overall_status == "partial")
failed_count = sum(1 for c in companies if c.overall_status == "failed")

with col1:
    st.metric("Total Companies", len(companies))

with col2:
    st.metric("✅ Successful", success_count)

with col3:
    st.metric("⚠️ Partial", partial_count)

with col4:
    st.metric("❌ Failed", failed_count)

st.markdown("---")

# === FILTERS ===
st.subheader("🔍 Filters")

col1, col2 = st.columns(2)

with col1:
    status_filter = st.selectbox(
        "Filter by Status",
        options=["All", "success", "partial", "failed"],
        key="status_filter",
    )

with col2:
    search_query = st.text_input(
        "Search Company Name",
        key="company_search",
    )

# Apply filters
filtered_companies = companies

if status_filter != "All":
    filtered_companies = [
        c for c in filtered_companies if c.overall_status == status_filter
    ]

if search_query:
    filtered_companies = [
        c for c in filtered_companies if search_query.lower() in c.company_name.lower()
    ]

# Apply quick filters from sidebar
if st.session_state.get("show_failures_only"):
    filtered_companies = [c for c in filtered_companies if c.overall_status == "failed"]
elif st.session_state.get("show_partial_only"):
    filtered_companies = [
        c for c in filtered_companies if c.overall_status == "partial"
    ]

st.caption(f"Showing {len(filtered_companies)} of {len(companies)} companies")

st.markdown("---")

# === COMPANIES TABLE ===
st.subheader("📋 Company List")

# Create table data
table_data = []
for company in filtered_companies:
    table_data.append(
        {
            "Company": company.company_name,
            "Status": company.overall_status,
            "New Jobs": company.new_jobs_found or 0,
            "Active Jobs": company.total_active_jobs or 0,
            "Inactive Jobs": company.total_inactive_jobs or 0,
            "Updated At": company.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            if company.updated_at
            else "N/A",
        }
    )

df = pd.DataFrame(table_data)

# Display table
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Status": st.column_config.TextColumn(
            "Status",
            width="small",
        ),
    },
)

st.markdown("---")

# === EXPANDABLE COMPANY DETAILS ===
st.subheader("🔍 Detailed Company Information")

# Select company to view details
company_names = [c.company_name for c in filtered_companies]

if company_names:
    selected_company_name = st.selectbox(
        "Select a company to view details:",
        options=company_names,
        key="selected_company",
    )

    # Find selected company
    selected_company = next(
        (c for c in filtered_companies if c.company_name == selected_company_name), None
    )

    if selected_company:
        # Company header
        st.markdown(f"### {selected_company.company_name}")
        st.markdown(
            render_status_badge(selected_company.overall_status), unsafe_allow_html=True
        )

        # Company metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("New Jobs Found", selected_company.new_jobs_found or 0)

        with col2:
            st.metric("Active Jobs", selected_company.total_active_jobs or 0)

        with col3:
            st.metric("Inactive Jobs", selected_company.total_inactive_jobs or 0)

        st.markdown("---")

        # Stage details
        st.markdown("#### Stage Details")

        stage_details = []
        for stage in range(1, 6):
            status = getattr(selected_company, f"stage_{stage}_status", None)
            processed = getattr(selected_company, f"stage_{stage}_jobs_processed", 0)
            completed = getattr(selected_company, f"stage_{stage}_jobs_completed", 0)
            exec_time = getattr(selected_company, f"stage_{stage}_execution_seconds", 0)
            error = getattr(selected_company, f"stage_{stage}_error_message", None)

            stage_details.append(
                {
                    "Stage": f"Stage {stage}",
                    "Status": status or "N/A",
                    "Processed": processed or 0,
                    "Completed": completed or 0,
                    "Execution Time (s)": f"{exec_time:.2f}" if exec_time else "0.00",
                    "Error": error or "None",
                }
            )

        df_stages = pd.DataFrame(stage_details)
        st.dataframe(df_stages, use_container_width=True, hide_index=True)

        # Show errors if any
        errors = []
        for stage in range(1, 6):
            error = getattr(selected_company, f"stage_{stage}_error_message", None)
            if error:
                errors.append(f"**Stage {stage}:** {error}")

        if errors:
            st.markdown("#### ⚠️ Errors")
            for error in errors:
                st.error(error)

        # Metadata
        with st.expander("Metadata"):
            st.write(f"**Date:** {selected_company.date}")
            st.write(
                f"**Last Updated Stage:** {selected_company.last_updated_stage or 'N/A'}"
            )
            st.write(
                f"**Created At:** {selected_company.created_at.strftime('%Y-%m-%d %H:%M:%S') if selected_company.created_at else 'N/A'}"
            )
            st.write(
                f"**Updated At:** {selected_company.updated_at.strftime('%Y-%m-%d %H:%M:%S') if selected_company.updated_at else 'N/A'}"
            )
            if selected_company.prefect_flow_run_id:
                st.write(
                    f"**Prefect Flow Run ID:** {selected_company.prefect_flow_run_id}"
                )
            if selected_company.pipeline_version:
                st.write(f"**Pipeline Version:** {selected_company.pipeline_version}")

else:
    st.info("No companies match the selected filters.")

st.caption("🏢 Pipeline Health Dashboard - Companies")
