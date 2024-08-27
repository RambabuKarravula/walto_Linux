import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
import random
import time
from datetime import datetime
import matplotlib.pyplot as plt
import plotly.express as px
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# Path for the master CSV file
MASTER_CSV = "master_users.csv"

# Ensure the master CSV file exists
if not os.path.exists(MASTER_CSV):
    master_df = pd.DataFrame(
        columns=["Sl.no", "User Number", "Name", "Username", "Email", "Password", "Assigned", "Spoke", "Tried", "SF"])
    master_df.to_csv(MASTER_CSV, index=False)


# Function to load master CSV data
def load_master_csv():
    return pd.read_csv(MASTER_CSV)


# Function to update the master CSV
def update_master_csv(master_df):
    master_df.to_csv(MASTER_CSV, index=False)


# Function to load user data from individual CSV
def load_user_data(email):
    file_path = os.path.join("user_data", f"{email}.csv")
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return pd.DataFrame(
            columns=['Sl.no', 'Name', 'Phone Number', 'Membershipnumber', 'Sex', 'Designation', 'Org', 'Location',
                     'S/T/SF', 'Regards', 'New Location'])


# Function to save user data to their individual CSV
def save_user_data(email, data):
    file_path = os.path.join("user_data", f"{email}.csv")
    data.to_csv(file_path, index=False)


# Function to send OTP via email
def send_otp(email):
    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    sender_email = "cmd@capcorporate.com"  # Replace with your email
    sender_password = "bqft ohrp hhjs kndq"  # Replace with your APP password

    msg = MIMEText(f"Your OTP is: {otp}")
    msg['Subject'] = "OTP for Verification"
    msg['From'] = sender_email
    msg['To'] = email

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, msg.as_string())
        return otp
    except Exception as e:
        st.sidebar.error(f"Failed to send OTP: {str(e)}")
        return None


# Function to verify OTP
def verify_otp(user_otp, sent_otp):
    return user_otp == sent_otp


# Function to register a new user
def register_user(name, username, email, password):
    master_df = load_master_csv()
    sl_no = len(master_df) + 1
    new_user = pd.DataFrame({
        "Sl.no": [sl_no],
        "User Number": [f"user{sl_no}"],
        "Name": [name],
        "Username": [username],
        "Email": [email],
        "Password": [password],
        "Assigned": [0],
        "Spoke": [0],
        "Tried": [0],
        "SF": [0]
    })
    master_df = pd.concat([master_df, new_user], ignore_index=True)
    update_master_csv(master_df)
    st.sidebar.success(f"User {username} registered successfully!")


# Function to update user password
def update_user_password(username, new_password):
    master_df = load_master_csv()
    user_row = master_df[master_df["Username"] == username]
    if not user_row.empty:
        index = user_row.index[0]
        master_df.at[index, "Password"] = new_password
        update_master_csv(master_df)
        return True
    return False


# Function to update user statistics in the master CSV
def update_user_stats(username, spoke_status):
    master_df = load_master_csv()
    user_row = master_df[master_df["Email"] == username]

    if not user_row.empty:
        index = user_row.index[0]
        if spoke_status == "S":
            master_df.at[index, "Spoke"] += 1
        elif spoke_status == "T":
            master_df.at[index, "Tried"] += 1
        elif spoke_status == "SF":
            master_df.at[index, "SF"] += 1
        update_master_csv(master_df)


# Function to update assigned count in master CSV
def update_assigned_count(username, num_rows_assigned):
    master_df = load_master_csv()
    user_row = master_df[master_df["Email"] == username]

    if not user_row.empty:
        index = user_row.index[0]
        master_df.at[index, "Assigned"] += num_rows_assigned
        update_master_csv(master_df)


# Function to render the table with bold rows for completed data and fixed serial number column
def render_table_with_bold_rows(df):
    table_html = """
    <style>
        .scrollable-table {
            width: 100%;
            max-height: 400px;
            overflow-x: auto;
            overflow-y: auto;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }
        th, td {
            padding: 8px;
            border: 1px solid #ddd;
            font-size: 14px;
        }
        th {
            position: sticky;
            top: 0;
            background-color: #f1f1f1;
        }
        .bold-row td {
            font-weight: bold;
        }
        .fixed {
            position: sticky;
            left: 0;
            background-color: #fff;
            z-index: 1;
        }
    </style>
    <div class="scrollable-table">
    <table>
        <tr>
    """
    # Adding headers
    for col in df.columns:
        table_html += f"<th>{col}</th>"
    table_html += "</tr>"

    # Adding rows with bold formatting for completed data
    for _, row in df.iterrows():
        if not pd.isna(row['S/T/SF']):  # Completed data
            table_html += "<tr class='bold-row'>"
        else:
            table_html += "<tr>"

        for i, val in enumerate(row):
            if i == 0:  # Fixing the first column (Serial Number)
                table_html += f"<td class='fixed'>{val}</td>"
            else:
                table_html += f"<td>{val}</td>"
        table_html += "</tr>"

    table_html += "</table></div>"
    st.markdown(table_html, unsafe_allow_html=True)


# Admin Pages
def admin_dashboard():
    st.title("Admin Dashboard")
    st.write("User Statistics (Data from Master CSV):")

    master_df = load_master_csv()

    # Initialize the pending and completed lists
    pending_list = []
    completed_list = []

    # Loop through each user to calculate pending and completed serial number ranges
    for _, row in master_df.iterrows():
        user_email = row["Email"]
        assigned = row["Assigned"]

        # Load user data
        user_data = load_user_data(user_email)

        if not user_data.empty:
            # Find the highest completed serial number (S, T, SF filled)
            completed_data = user_data.dropna(subset=['S/T/SF'])
            if not completed_data.empty:
                first_completed_serial = completed_data['Sl.no'].min()
                last_completed_serial = completed_data['Sl.no'].max()

                completed_range = f"{first_completed_serial} - {last_completed_serial}" if first_completed_serial <= last_completed_serial else "None"
                pending_range = f"{last_completed_serial + 1} - {assigned}" if last_completed_serial < assigned else "None"
            else:
                completed_range = "None"
                pending_range = f"1 - {assigned}"  # If no data is completed
        else:
            completed_range = "None"
            pending_range = f"1 - {assigned}"  # If no data is assigned

        completed_list.append(completed_range)
        pending_list.append(pending_range)

    # Add the "Completed" and "Pending" columns to the master DataFrame
    master_df["Completed"] = completed_list
    master_df["Pending"] = pending_list

    # Calculate percentage of completion for each user and round to 2 decimal places
    master_df['Completion (%)'] = ((master_df['Spoke'] + master_df['Tried'] + master_df['SF']) / master_df['Assigned']) * 100
    master_df['Completion (%)'] = master_df['Completion (%)'].fillna(0).round(2)  # Handle NaN and round to 2 decimals

    # Calculate totals for Assigned, Spoke, Tried, and SF columns
    total_assigned = master_df['Assigned'].sum()
    total_spoke = master_df['Spoke'].sum()
    total_tried = master_df['Tried'].sum()
    total_sf = master_df['SF'].sum()

    # Calculate overall completion percentage for all users and round to 2 decimals
    overall_completion_percentage = ((total_spoke + total_tried + total_sf) / total_assigned) * 100 if total_assigned > 0 else 0
    overall_completion_percentage = round(overall_completion_percentage, 2)

    # Create a DataFrame with the required columns for AgGrid
    display_df = master_df[["Sl.no", "Name", "Assigned", "Spoke", "Tried", "SF", "Completion (%)", "Completed", "Pending"]].copy()

    # Use AgGrid to create an interactive table
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_pagination(enabled=True)
    gb.configure_side_bar()
    gb.configure_default_column(editable=False, filter=True, sortable=True, resizable=True)
    gb.configure_auto_height()
    gb.configure_selection(selection_mode="single")
    grid_options = gb.build()

    st.subheader("Interactive User Data Table")
    AgGrid(
        display_df,
        gridOptions=grid_options,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        theme='streamlit',  # Available themes: 'streamlit', 'light', 'dark', 'blue', 'fresh', 'material'
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
    )

    # Display totals outside the table
    st.subheader("Total Statistics")
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Assigned", total_assigned)
    col2.metric("Total Spoke", total_spoke)
    col3.metric("Total Tried", total_tried)
    col4.metric("Total SF", total_sf)
    col5.metric("Overall Completion (%)", f"{overall_completion_percentage}%")

    # ----- Graphs -----
    # Bar chart: Assigned vs. Spoke, Tried, SF
    st.subheader("Bar Chart: Performance of Users")
    fig, ax = plt.subplots()
    master_df.set_index('Name')[['Spoke', 'Tried', 'SF']].plot(kind='bar', stacked=True, ax=ax)
    plt.title("Spoke, Tried, and SF by User")
    plt.ylabel("Count")
    plt.xlabel("User")
    st.pyplot(fig)

    # Pie chart: Distribution of total Spoke, Tried, SF
    st.subheader("Pie Chart: Distribution of Actions")
    actions_totals = pd.Series([total_spoke, total_tried, total_sf], index=['Spoke', 'Tried', 'SF'])
    fig2, ax2 = plt.subplots()
    ax2.pie(actions_totals, labels=actions_totals.index, autopct='%1.1f%%', startangle=90,
            colors=['#66b3ff', '#99ff99', '#ffcc99'])
    ax2.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    st.pyplot(fig2)

    # Completion percentage bar chart using Plotly
    st.subheader("Completion Percentage by User")
    fig3 = px.bar(master_df, x='Name', y='Completion (%)', title='User Completion Percentage',
                  labels={'Completion (%)': 'Completion (%)'})
    st.plotly_chart(fig3)



def admin_dashboard():
    st.title("Admin Dashboard")
    st.write("User Statistics (Data from Master CSV):")

    master_df = load_master_csv()

    # Calculate percentage of completion for each user and round to 2 decimal places
    master_df['Completion (%)'] = ((master_df['Spoke'] + master_df['Tried'] + master_df['SF']) / master_df['Assigned']) * 100
    master_df['Completion (%)'] = master_df['Completion (%)'].fillna(0).round(2)  # Handle NaN and round to 2 decimals

    # Calculate totals for Assigned, Spoke, Tried, and SF columns
    total_assigned = master_df['Assigned'].sum()
    total_spoke = master_df['Spoke'].sum()
    total_tried = master_df['Tried'].sum()
    total_sf = master_df['SF'].sum()

    # Calculate overall completion percentage for all users and round to 2 decimals
    overall_completion_percentage = ((total_spoke + total_tried + total_sf) / total_assigned) * 100 if total_assigned > 0 else 0
    overall_completion_percentage = round(overall_completion_percentage, 2)

    # Display totals horizontally using Streamlit columns
    st.subheader("Total Statistics")
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Assigned", total_assigned)
    col2.metric("Total Spoke", total_spoke)
    col3.metric("Total Tried", total_tried)
    col4.metric("Total SF", total_sf)
    col5.metric("Overall Completion (%)", f"{overall_completion_percentage}%")

    # Create a DataFrame without the totals row for AgGrid
    display_df = master_df[["Sl.no", "Name", "Assigned", "Spoke", "Tried", "SF", "Completion (%)"]].copy()

    # Use AgGrid to create an interactive table
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_pagination(enabled=True)
    gb.configure_side_bar()
    gb.configure_default_column(editable=False, filter=True, sortable=True, resizable=True)
    gb.configure_auto_height()
    gb.configure_selection(selection_mode="single")
    grid_options = gb.build()

    st.subheader("Interactive User Data Table")
    AgGrid(
        display_df,
        gridOptions=grid_options,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        theme='streamlit',  # Available themes: 'streamlit', 'light', 'dark', 'blue', 'fresh', 'material'
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
    )

    # Reduce the gap by removing excessive spacing
    st.markdown("<style>div.block-container {padding-top: 0px; padding-bottom: 0px;}</style>", unsafe_allow_html=True)



    # ----- Graphs -----
    # Bar chart: Assigned vs. Spoke, Tried, SF
    st.subheader("Bar Chart: Performance of Users")
    fig, ax = plt.subplots()
    master_df.set_index('Name')[['Spoke', 'Tried', 'SF']].plot(kind='bar', stacked=True, ax=ax)
    plt.title("Spoke, Tried, and SF by User")
    plt.ylabel("Count")
    plt.xlabel("User")
    st.pyplot(fig)

    # Pie chart: Distribution of total Spoke, Tried, SF
    st.subheader("Pie Chart: Distribution of Actions")
    actions_totals = pd.Series([total_spoke, total_tried, total_sf], index=['Spoke', 'Tried', 'SF'])
    fig2, ax2 = plt.subplots()
    ax2.pie(actions_totals, labels=actions_totals.index, autopct='%1.1f%%', startangle=90,
            colors=['#66b3ff', '#99ff99', '#ffcc99'])
    ax2.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    st.pyplot(fig2)

    # Completion percentage bar chart using Plotly
    st.subheader("Completion Percentage by User")
    fig3 = px.bar(master_df, x='Name', y='Completion (%)', title='User Completion Percentage',
                  labels={'Completion (%)': 'Completion (%)'})
    st.plotly_chart(fig3)


def admin_allocate():
    st.title("Admin Allocate")

    # Load master CSV for users
    master_df = load_master_csv()

    # Display a dropdown to select a user by name for allocation
    user_name = st.selectbox("Select User to Allocate Data", master_df["Name"].tolist())

    # Find the corresponding email for the selected user
    user_row = master_df[master_df["Name"] == user_name]
    if not user_row.empty:
        user_email = user_row["Email"].values[0]

        # Display a file uploader to upload data for allocation
        uploaded_file = st.file_uploader("Upload Data for Allocation", type=["csv", "xlsx"])

        if uploaded_file is not None:
            # Load the uploaded file into a DataFrame
            if uploaded_file.name.endswith(".csv"):
                new_data = pd.read_csv(uploaded_file)
            else:
                new_data = pd.read_excel(uploaded_file)

            st.write("Uploaded Data Preview")
            st.write(new_data.head())  # Display the first few rows of the data

            # Load the existing user data (if any)
            existing_data = load_user_data(user_email)

            if not existing_data.empty:
                # Append new data to the existing data
                combined_data = pd.concat([existing_data, new_data], ignore_index=True)
            else:
                # No existing data, so just use the new data
                combined_data = new_data

            # Button to confirm the allocation
            if st.button("Allocate Data"):
                try:
                    # Save the combined data back to the user's individual CSV
                    save_user_data(user_email, combined_data)

                    # Update the user's assigned count in the master CSV
                    update_assigned_count(user_email, len(new_data))

                    # Reload the updated master CSV to refresh the dashboard
                    master_df = load_master_csv()

                    st.success(f"Data allocated successfully to {user_name}!")

                except Exception as e:
                    st.error(f"An error occurred while saving data: {str(e)}")

    else:
        st.error("User not found in master CSV")

    # ---- Reallocation Section ----
    st.subheader("Reallocate Data")

    if 'reallocation_started' not in st.session_state:
        st.session_state.reallocation_started = False

    if st.button("Reallocate"):
        st.session_state.reallocation_started = True

    if st.session_state.reallocation_started:
        reallocate_from = st.selectbox("Reallocate from", master_df["Name"].tolist(), key="reallocate_from")
        reallocate_to = st.selectbox("Reallocate to", master_df["Name"].tolist(), key="reallocate_to")

        start_serial = st.number_input("From Serial No.", min_value=0, key="start_serial")
        end_serial = st.number_input("To Serial No.", min_value=0, key="end_serial")

        if st.button("Confirm Reallocation"):
            if start_serial > end_serial:
                st.error("The starting serial number must be less than or equal to the ending serial number.")
            else:
                try:
                    # Load user data for both users
                    from_user_email = master_df[master_df["Name"] == reallocate_from]["Email"].values[0]
                    to_user_email = master_df[master_df["Name"] == reallocate_to]["Email"].values[0]

                    from_user_data = load_user_data(from_user_email)
                    to_user_data = load_user_data(to_user_email)

                    # Check if the serial range exists in the 'from' user's data using the 'Sl.no' column
                    range_data = from_user_data[
                        (from_user_data['Sl.no'] >= start_serial) & (from_user_data['Sl.no'] <= end_serial)]

                    if range_data.empty:
                        st.error("No data found in the specified serial range for reallocation.")
                    else:
                        # Remove the reallocated data from the 'from' user's data
                        from_user_data = from_user_data.drop(range_data.index)

                        # Append the reallocated data to the 'to' user's data
                        to_user_data = pd.concat([to_user_data, range_data], ignore_index=True)

                        # Reassign new serial numbers in the 'to' user's data if necessary
                        to_user_data = to_user_data.sort_values(by='Sl.no').reset_index(drop=True)
                        to_user_data['Sl.no'] = range(1, len(to_user_data) + 1)

                        # Save the updated data to the respective users' CSV files
                        save_user_data(from_user_email, from_user_data)
                        save_user_data(to_user_email, to_user_data)

                        # Update assigned counts in the master CSV
                        update_assigned_count(from_user_email, -len(range_data))
                        update_assigned_count(to_user_email, len(range_data))

                        # Reload the updated master CSV to refresh the dashboard
                        master_df = load_master_csv()

                        st.success(
                            f"Successfully reallocated Serial No. {start_serial} to {end_serial} from {reallocate_from} to {reallocate_to}!")

                except Exception as e:
                    st.error(f"An error occurred during reallocation: {str(e)}")


def admin_reports():
    st.title("Admin Reports")

    # Date filters for the report
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")

    if start_date > end_date:
        st.error("End date must be greater than or equal to start date.")

    # Load the master CSV for all users
    master_df = load_master_csv()

    # Initialize an empty list to store filtered data
    filtered_data = []

    # Iterate through each user and load their respective CSV file for data filtering
    for _, row in master_df.iterrows():
        user_email = row["Email"]
        user_name = row["Name"]

        # Load the user's data
        user_data = load_user_data(user_email)

        # Filter the data based on the date range selected by the admin
        if not user_data.empty and "Date" in user_data.columns:
            user_data['Date'] = pd.to_datetime(user_data['Date'], errors='coerce')
            filtered_user_data = user_data[(user_data['Date'] >= pd.to_datetime(start_date)) &
                                           (user_data['Date'] <= pd.to_datetime(end_date))]

            # Append the user's name to the filtered data
            if not filtered_user_data.empty:
                filtered_user_data["User"] = user_name
                filtered_data.append(filtered_user_data)

    # If there is filtered data, combine it into one DataFrame
    if filtered_data:
        report_df = pd.concat(filtered_data, ignore_index=True)

        # Reorder and rename columns as required
        report_df = report_df[['Sl.no', 'Name', 'Membershipnumber', 'Phone Number', 'S/T/SF',
                               'Regards', 'Date', 'Location', 'New Location', 'User']]

        st.write("Filtered Report")
        st.dataframe(report_df)

        # Function to convert DataFrame to Excel
        def convert_df_to_excel(df):
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Report')
            writer.save()
            processed_data = output.getvalue()
            return processed_data

        # Add a button to download the filtered report as Excel
        excel_data = convert_df_to_excel(report_df)
        st.download_button(label="Download Report as Excel",
                           data=excel_data,
                           file_name=f"report_{start_date}_to_{end_date}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="download_button")
    else:
        st.write("No data available for the selected date range.")

# User Page
def user_page(username):
    st.title(f"{username} Data Entry")

    # Retrieve the email associated with the username
    master_df = load_master_csv()
    user_email = master_df[master_df["Username"] == username]["Email"].values[0]

    # Load the current user data from their CSV
    allocated_data = load_user_data(user_email)

    if not allocated_data.empty:
        # Create two columns, one for the table and one for the form
        col1, col2 = st.columns([2, 1])

        with col1:
            st.write("Your Allocated Data:")
            render_table_with_bold_rows(allocated_data)

        with col2:
            st.write("Select a serial number to fill or edit the data:")

            # Combine both unfinished and completed data for selection
            serial_no = st.selectbox("Choose Serial Number", allocated_data['Sl.no'])

            # Find the corresponding row for the selected serial number
            selected_row = allocated_data[allocated_data['Sl.no'] == serial_no].iloc[0]

            # Default values for the form fields are set using the selected row data
            with st.form(key='data_entry_form'):
                spoke_status = st.selectbox("Spoke/Tried/Spoke & Followup Required",
                                            options=['S', 'T', 'SF'],
                                            index=['S', 'T', 'SF'].index(selected_row['S/T/SF'] if pd.notna(selected_row['S/T/SF']) else 'S'))
                regards = st.selectbox("Regards?", options=['None', 'High', 'Medium', 'Low'],
                                       index=['None', 'High', 'Medium', 'Low'].index(selected_row['Regards'] if pd.notna(selected_row['Regards']) else 'High'))
                location_change = st.text_input("Location Change?", value=selected_row['New Location'] if pd.notna(selected_row['New Location']) else '')

                submit_button = st.form_submit_button(label='Submit')

            if submit_button:
                # Update the selected row with the new data
                allocated_data.loc[allocated_data['Sl.no'] == serial_no, 'S/T/SF'] = spoke_status
                allocated_data.loc[allocated_data['Sl.no'] == serial_no, 'Regards'] = regards
                allocated_data.loc[allocated_data['Sl.no'] == serial_no, 'New Location'] = location_change
                allocated_data.loc[allocated_data['Sl.no'] == serial_no, 'Date'] = datetime.now().strftime('%Y-%m-%d')

                # Save the updated data to the user's CSV file
                save_user_data(user_email, allocated_data)

                # Update the master CSV
                update_user_stats(user_email, spoke_status)

                # Inform the user of the successful update
                st.success(f"Data for Serial No {serial_no} updated successfully.")

                # Simulate page refresh by resetting query params (forces rerun)
                st.experimental_set_query_params(refresh="true")

    else:
        st.write("No data allocated to you.")




if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.sidebar.title("Authentication")
    auth_option = st.sidebar.radio("Choose an option", ["Login", "Register", "Forgot Password"], key="auth_radio_key")
    # Add text near the login button
    st.sidebar.write("Click Twice")

    if auth_option == "Login":
        st.sidebar.subheader("Login")
        username = st.sidebar.text_input("Username", key="login_username")
        password = st.sidebar.text_input("Password", type="password", key="login_password")
        login_button = st.sidebar.button("Login")

        if login_button:
            if username == "admin" and password == "Password1$":
                st.session_state.logged_in = True
                st.session_state.username = "admin"
                st.sidebar.success(f"Logged in as admin")
            else:
                master_df = load_master_csv()
                user_data = master_df[(master_df["Username"] == username) & (master_df["Password"] == password)]
                if not user_data.empty:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.sidebar.success(f"Logged in as {username}")
                else:
                    st.sidebar.error("Incorrect username or password")

    elif auth_option == "Register":
        st.sidebar.subheader("Register")
        new_name = st.sidebar.text_input("Name", key="register_name")
        new_username = st.sidebar.text_input("Username", key="register_username")
        new_email = st.sidebar.text_input("Email", key="register_email")
        new_password = st.sidebar.text_input("Password", type="password", key="register_password")
        register_button = st.sidebar.button("Register", key="register_button")

        if register_button:
            if new_name and new_username and new_email and new_password:
                # Send OTP to email
                otp = send_otp(new_email)
                if otp:
                    st.session_state.registration_otp = otp
                    st.session_state.registration_data = {
                        "name": new_name,
                        "username": new_username,
                        "email": new_email,
                        "password": new_password
                    }
                    st.sidebar.success("OTP sent to your email. Please verify.")
                    st.session_state.registration_stage = "verify_otp"
                else:
                    st.sidebar.error("Failed to send OTP. Please try again.")
            else:
                st.sidebar.error("Please fill all fields")

        # OTP verification for registration
        if 'registration_stage' in st.session_state and st.session_state.registration_stage == "verify_otp":
            user_otp = st.sidebar.text_input("Enter OTP", key="register_otp")
            verify_button = st.sidebar.button("Verify OTP", key="register_verify_button")

            if verify_button:
                if user_otp == st.session_state.registration_otp:
                    register_user(**st.session_state.registration_data)
                    st.sidebar.success("Registration successful! Please login.")
                    del st.session_state.registration_stage
                    del st.session_state.registration_otp
                    del st.session_state.registration_data
                else:
                    st.sidebar.error("Invalid OTP. Please try again.")

    elif auth_option == "Forgot Password":
        st.sidebar.subheader("Forgot Password")
        forgot_username = st.sidebar.text_input("Username", key="forgot_username_input")
        forgot_email = st.sidebar.text_input("Email", key="forgot_email_input")
        forgot_button = st.sidebar.button("Send OTP", key="forgot_button")

        if forgot_button:
            master_df = load_master_csv()
            user_data = master_df[(master_df["Username"] == forgot_username) & (master_df["Email"] == forgot_email)]
            if not user_data.empty:
                sent_otp = send_otp(forgot_email)
                if sent_otp:
                    st.session_state.forgot_username_state = forgot_username
                    st.session_state.forgot_email_state = forgot_email
                    st.session_state.sent_otp = sent_otp
                    st.sidebar.success("OTP sent to your email.")
                    st.session_state.forgot_stage = "verify_otp"
                else:
                    st.sidebar.error("Failed to send OTP. Please try again.")
            else:
                st.sidebar.error("Username and email do not match our records.")

        if 'forgot_stage' in st.session_state and st.session_state.forgot_stage == "verify_otp":
            user_otp = st.sidebar.text_input("Enter OTP", key="forgot_otp_input")
            new_password = st.sidebar.text_input("New Password", type="password", key="new_password_input")
            verify_button = st.sidebar.button("Verify OTP and Change Password", key="forgot_verify_button")

            if verify_button:
                if user_otp == st.session_state.sent_otp:
                    if update_user_password(st.session_state.forgot_username_state, new_password):
                        st.sidebar.success("Password changed successfully. Please login with your new password.")
                        del st.session_state.forgot_stage
                        del st.session_state.sent_otp
                        del st.session_state.forgot_username_state
                        del st.session_state.forgot_email_state
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.sidebar.error("Failed to update password. Please try again.")
                else:
                    st.sidebar.error("Invalid OTP")

else:
    username = st.session_state.username
    st.sidebar.subheader(f"Welcome, {username}")

    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.sidebar.success("Logged out successfully.")
        st.rerun()

    if username == "admin":
        page = st.sidebar.radio("Admin Pages", ['Dashboard', 'Allocate', 'Reports'])
        if page == 'Dashboard':
            admin_dashboard()
        elif page == 'Allocate':
            admin_allocate()
        elif page == 'Reports':
            admin_reports()
    else:
        change_password = st.sidebar.checkbox("Change Password")
        if change_password:
            current_password = st.sidebar.text_input("Current Password", type="password", key="current_password")
            new_password = st.sidebar.text_input("New Password", type="password", key="new_password")
            confirm_password = st.sidebar.text_input("Confirm New Password", type="password", key="confirm_password")
            change_password_button = st.sidebar.button("Change Password")

            if change_password_button:
                master_df = load_master_csv()
                user_data = master_df[(master_df["Username"] == username) & (master_df["Password"] == current_password)]
                if not user_data.empty:
                    if new_password == confirm_password:
                        if update_user_password(username, new_password):
                            st.sidebar.success("Password changed successfully.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.sidebar.error("Failed to update password. Please try again.")
                    else:
                        st.sidebar.error("New passwords do not match.")
                else:
                    st.sidebar.error("Current password is incorrect.")

        user_page(username)

# Main content area
if not st.session_state.logged_in:
    st.title("Welcome to Victory!")
