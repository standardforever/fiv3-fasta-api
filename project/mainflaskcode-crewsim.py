from flask import Flask, render_template, request, jsonify
import pandas as pd
import calendar
import datetime

app = Flask(__name__)

# Load the modified l data
# NOTE: Update the path accordingly
df_crewsim = pd.read_excel(r"updated_data.xlsx")

regions = df_crewsim['Region'].unique().tolist()
markets = df_crewsim['Market'].unique().tolist()
smps = df_crewsim['SMP Name'].unique().tolist()
sdrms = df_crewsim['Site Deployment Reference Model'].unique().tolist()
sdrm_project_types = df_crewsim['SDRM-Project Type'].unique().tolist()
months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
          "December"]


@app.route('/get_sdrms', methods=['GET'])
def get_sdrms():
    selected_smp = request.args.get('smp')
    available_sdrms = df_crewsim[df_crewsim['SMP Name'] == selected_smp]['Site Deployment Reference Model'].unique().tolist()
    return jsonify(available_sdrms)


@app.route('/get_sdrm_project_types', methods=['GET'])
def get_sdrm_project_types():
    selected_sdrm = request.args.get('sdrm')
    available_sdrm_project_types = df_crewsim[df_crewsim['Site Deployment Reference Model'] == selected_sdrm][
        'SDRM-Project Type'].unique().tolist()
    return jsonify(available_sdrm_project_types)


@app.route('/get_markets', methods=['GET'])
def get_markets():
    region = request.args.get('region')
    available_markets = df_crewsim[df_crewsim['Region'] == region]['Market'].unique().tolist()
    return jsonify(available_markets)


@app.route('/get_cycle_time', methods=['GET'])
def get_cycle_time():
    smp = request.args.get('smp')
    sdrm = request.args.get('sdrm')
    sdrm_project_type = request.args.get('sdrm_project_type')
    selected_markets = request.args.getlist('markets')  # Get all selected markets

    # Filter rows based on the selected configuration and markets
    cycle_time_rows = df_crewsim[
        (df_crewsim['SMP Name'] == smp) &
        (df_crewsim['Site Deployment Reference Model'] == sdrm) &
        (df_crewsim['SDRM-Project Type'] == sdrm_project_type) &
        (df_crewsim['Market'].isin(selected_markets))  # Filter by selected markets
        ]['Cycle time']
    # print(cycle_time_rows)
    if not cycle_time_rows.empty:
        average_cycle_time = cycle_time_rows.mean()
        return jsonify({'cycle_time': average_cycle_time})
    else:
        return jsonify({'error': 'Cycle time not available'})


def count_days(year, month):
    weekdays_count = sum(1 for week in calendar.monthcalendar(year, month) for day in week if
                         day != 0 and datetime.date(year, month, day).weekday() < 5)
    weekends_count = sum(1 for week in calendar.monthcalendar(year, month) for day in week if
                         day != 0 and datetime.date(year, month, day).weekday() >= 5)
    return weekdays_count, weekends_count


@app.route('/crewsim', methods=['GET', 'POST'])
def index():
    total_volume_divided = 0
    cycle_times = {}
    actual_crew_required = None
    total_days = 0
    total_weekends = 0
    crew_capabilities = {}
    crews_needed_actual = {}
    crew_capabilities_ideal = {}  # Added to store the ideal crew capabilities
    crews_needed_ideal = {}
    average_slas = {}
    entered_sites_values = []
    sum_crews_needed_ideal = 0
    sum_crews_needed_actual = 0
    overall_average_sla_time = 0
    overall_average_cycle_time = 0
    markets = []
    form_region = []
    if request.method == 'POST':
        selected_option2 = request.form.getlist('selectedOption2[]')
        volume = float(request.form['volume'])
        smps_selected = request.form.getlist('smp')
        sdrms_selected = request.form.getlist('sdrm')
        sdrm_project_types_selected = request.form.getlist('sdrm_project_type')
        percentages = request.form.getlist('percentage')
        selected_months = request.form.getlist('months')
        markets = request.form.getlist('market[]')
        form_region = request.form.getlist('region[]')
     

        selected_months = request.form.getlist('months')
        current_year = datetime.datetime.now().year
        for month_name in selected_months:
            month_num = months.index(month_name) + 1
            weekdays, weekends = count_days(current_year, month_num)
            total_days += weekdays
            total_weekends += weekends

        for i in range(len(smps_selected)):
            # for market in markets:
            key = f"{smps_selected[i]}, {sdrms_selected[i]}, {sdrm_project_types_selected[i]}"
            total_volume_divided += volume * (float(percentages[i]) / 100)

            filtered_rows = df_crewsim[
                (df_crewsim['Region'].isin(form_region)) &
                (df_crewsim['Market'].isin(markets)) &
                (df_crewsim['SMP Name'].isin(smps_selected)) &
                (df_crewsim['Site Deployment Reference Model'].isin(sdrms_selected)) &
                (df_crewsim['SDRM-Project Type'].isin(sdrm_project_types_selected))
                ]
         
            average_cycle_time = filtered_rows['Cycle time'].mean()
            average_sla_time = filtered_rows['Installation SLA'].mean()

            cycle_times[key] = round(average_cycle_time) if not pd.isna(average_cycle_time) else "Not available"
            average_slas[key] = round(average_sla_time) if not pd.isna(average_sla_time) else "Not available"

            if not pd.isna(average_cycle_time):
                crew_capabilities[key] = total_days / average_cycle_time
                crews_needed_actual[key] = round(total_volume_divided / crew_capabilities[key]) if \
                crew_capabilities[key] != 0 else float('inf')
            else:
                crew_capabilities[key] = "Not available"
                crews_needed_actual[key] = "Not available"

            if not pd.isna(average_sla_time):
                crew_capabilities_ideal[key] = total_days / average_sla_time
                crews_needed_ideal[key] = round(
                    volume * (float(percentages[i]) / 100) / crew_capabilities_ideal[key]) if \
                crew_capabilities_ideal[key] != "Not available" else "Not available"
            else:
                crew_capabilities_ideal[key] = "Not available"
                crews_needed_ideal[key] = "Not available"

            entered_sites_values.append(float(percentages[i]))

        actual_crew_required = total_volume_divided / len(smps_selected)

        sum_crews_needed_ideal = sum([value for key, value in crews_needed_ideal.items() if value != "Not available"])
        sum_crews_needed_actual = sum([value for key, value in crews_needed_actual.items() if value != "Not available"])
        return render_template('result.html', regions=form_region, markets=markets, months=selected_months, smps=smps, sdrms=sdrms,
                           sdrm_project_types=sdrm_project_types, actual_crew_required=actual_crew_required,
                           cycle_times=cycle_times, total_days=total_days, total_weekends=total_weekends,
                           crew_capabilities=crew_capabilities, crews_needed_actual=crews_needed_actual,
                           crew_capabilities_ideal=crew_capabilities_ideal, crews_needed_ideal=crews_needed_ideal,
                           average_slas=average_slas, entered_sites_values=entered_sites_values,
                           sum_crews_needed_ideal=sum_crews_needed_ideal,
                           sum_crews_needed_actual=sum_crews_needed_actual, cycle=overall_average_cycle_time,
                           sla=overall_average_sla_time)


    return render_template('main38.html', regions=regions, markets=markets, months=months, smps=smps, sdrms=sdrms,
                           sdrm_project_types=sdrm_project_types, actual_crew_required=actual_crew_required,
                           cycle_times=cycle_times, total_days=total_days, total_weekends=total_weekends,
                           crew_capabilities=crew_capabilities, crews_needed_actual=crews_needed_actual,
                           crew_capabilities_ideal=crew_capabilities_ideal, crews_needed_ideal=crews_needed_ideal,
                           average_slas=average_slas, entered_sites_values=entered_sites_values,
                           sum_crews_needed_ideal=sum_crews_needed_ideal,
                           sum_crews_needed_actual=sum_crews_needed_actual, cycle=overall_average_cycle_time,
                           sla=overall_average_sla_time)


# """ ============NEw code i added =============="""

@app.route('/get_second_dropdown_data', methods=['POST'])
def get_options():
    # Filter rows
    selected_regions = request.json.get('selectedOptions')
    second_dropdown_data = []
    
    for selected_region in selected_regions:
        if selected_region in regions:
            north_rows = df_crewsim[df_crewsim['Region'] == selected_region]
            # Get unique values
            second_dropdown_data += north_rows['Market'].unique().tolist()
    return jsonify(second_dropdown_data)


if __name__ == '__main__':
    app.run(debug=True)
