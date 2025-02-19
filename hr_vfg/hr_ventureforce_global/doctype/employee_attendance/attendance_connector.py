from __future__ import unicode_literals
import frappe
from frappe import utils
from frappe import throw, _

import sys
import time
from zk import ZK, const
from datetime import datetime, timedelta
from frappe.utils import date_diff, add_months, get_datetime, today, getdate, add_days, flt, get_last_day
import calendar
from frappe.utils.background_jobs import enqueue
from requests import request
import json
from datetime import datetime
from datetime import timedelta


@frappe.whitelist()
def get_attendance_long(**args):
	if not args:
		args = frappe.local.form_dict
	"Enqueue longjob for taking backup to dropbox"
	enqueue("hr_vfg.hr_ventureforce_global.doctype.employee_attendance.attendance_connector.execute_job", 
	 queue='long', timeout=8000,args=args)
	
	frappe.msgprint(_("Queued for biometric attendance. It may take a few minutes to an hour."))
@frappe.whitelist()
def execute_job(args):
	hr_settings = frappe.get_single('V HR Settings')
	for machine in hr_settings.attendance_machine:
		if machine.type == 'In':
			get_checkins(args,machine.ip,machine.port,machine.password)
		elif machine.type == "Out":
			get_checkouts(args,machine.ip,machine.port,machine.password)
		else:
			get_checkins_checkouts(args,machine.ip,machine.port,machine.password)

def get_checkins(args=None, ip=None, port=None,password=0):
	conn = None
	if not args:
		args = {"from_date":"2022-01-01","to_date":today()}
	emp_list = [] #110.93.236.48
	if not password:
		password = 0
	zk = ZK(ip, port=int(port), timeout=1500, password=password, force_udp=False, ommit_ping=False)
	frappe.log_error("Starting in..","Attendance hook test")
	try:
		conn = zk.connect()
		if conn:
			users = conn.get_users()
			if users:
				for u in users:
					#print(u)
					pass

			attendance = conn.get_attendance()
			print("getting attendance data")
			
			if attendance:
				#print(attendance)
				
				attendance_dict={}
				condition1 =""
				condition2=""
				biometric_list=[]
				b_filters = {}
				if args.get("employee"):
					condition1=" and parent in (select name from `tabEmployee Attendance` where employee='{0}')".format(args.get("employee"))
					condition2=" and biometric_id in (select biometric_id from `tabEmployee` where name='{0}')".format(args.get("employee"))
					b_filters["name"]=args.get("employee")
				if args.get("department"):
					condition1=" and parent in (select name from `tabEmployee Attendance` where department='{0}')".format(args.get("department"))
					condition2=" and biometric_id in (select biometric_id from `tabEmployee` where department='{0}')".format(args.get("department"))
					b_filters["department"]=args.get("department")
				if args.get("employee") and args.get("department"):
					condition1=" and parent in (select name from `tabEmployee Attendance` where employee='{0}' and department='{1}')".format(args.get("employee"),args.get("department"))
					condition2=" and biometric_id in (select biometric_id from `tabEmployee` where name='{0}' and department='{1}')".format(args.get("employee"),args.get("department"))

				B_r = frappe.db.get_all("Employee",filters=b_filters,fields=["biometric_id"])
				for bid in B_r:
					biometric_list.append(bid.biometric_id)
				frappe.db.sql(""" delete from `tabAttendance Logs` where attendance_date >= %s and attendance_date <= %s and ip=%s {0} """.format(condition2), (args.get("from_date"),args.get("to_date"),ip+":"+port))
				frappe.db.sql(""" update `tabEmployee Attendance Table` set check_in_1=NULL,  late_sitting=NULL, night_switch=0 where date >= %s and date <= %s and ip=%s and type!="Adjustment"{0} """.format(condition1), (args.get("from_date"),args.get("to_date"),ip+":"+port))
				frappe.db.commit()
				print(str(biometric_list))
				#frappe.log_error(len(attendance))
				for attend1 in attendance:
					if getdate(str(attend1).split()[3]) < getdate(args.get("from_date")) or getdate(str(attend1).split()[3]) > getdate(args.get("to_date")):
						continue
					# if str(attend1).split()[1] == "405":
					# 		print("Found 1 a")
					if len(biometric_list) > 0:
						if str(attend1).split()[1] not in biometric_list:
							continue
					if attendance_dict.get(str(attend1).split()[1]):
						if attendance_dict.get(str(attend1).split()[1]).get(str(attend1).split()[3]):
							# attendance_dict.get(str(attend1).split()[1]).get(str(attend1).split()[3])["check in"]=str(attend1).split()[4]
							# attendance_dict.get(str(attend1).split()[1]).get(str(attend1).split()[3])["checkin string"]=str(attend1)
							pass
						else:
							attendance_dict.get(str(attend1).split()[1])[str(attend1).split()[3]]={
								"check in": str(attend1).split()[4],
								"checkin string":str(attend1)
							}
					else:
						attendance_dict[str(attend1).split()[1]]={
							str(attend1).split()[3] :{
								"check in": str(attend1).split()[4],
								"checkin string":str(attend1)
							}
						}
					
					

				import json
				for users in attendance_dict:
					print(users)
					for dates in attendance_dict[users]:
						try:
							date = dates
							check_in = attendance_dict[users][dates].get("check in")
							check_in_string = attendance_dict[users][dates].get("checkin string")
							
							if check_in:
									d_a = str(utils.today()) +" 8:30:0"
									d_b = str(utils.today()) +" 1:0:0"
									d_s = str(utils.today()) +" 23:59:00"
									d_c = str(date+" "+check_in)
									
									res = frappe.db.sql(""" select name, biometric_id from `tabAttendance Logs` where 
									biometric_id=%s and attendance_date=%s and attendance_time=%s and type='Check In'""", 
									(users, str(date), check_in))
									if res:
										
										atl = frappe.get_doc("Attendance Logs",res[0][0])
										atl.save()
									else:
										print("adding check in")
										doc1 = frappe.new_doc("Attendance Logs")
										doc1.attendance = check_in_string
										doc1.biometric_id= users
										doc1.attendance_date= str(date)
										doc1.attendance_time= str(check_in)
										doc1.type = "Check In"
										doc1.ip = ip+":"+port
										doc1.save(ignore_permissions=True)
							
						except:
							frappe.log_error(frappe.get_traceback(),"Attendance hook test")
				
	except Exception as e:
		print ("Process terminate : {}"+frappe.get_traceback())
		frappe.log_error(frappe.get_traceback(),"Attendance hook test")
	finally:
		if conn:
			conn.disconnect()

def check_time(attend1):
	t_biometric = str(attend1).split()[1]
	flg = False
	t_date = str(attend1).split()[3]
	employee = frappe.db.get_value("Employee",{"biometric_id":t_biometric},"name")
	shift_ass = frappe.get_all("Shift Assignment", filters={'employee': employee,
													'start_date': ["<=", getdate(t_date)],'end_date': [">=", getdate(t_date)]}, fields=["*"])
	if len(shift_ass) > 0:
		shift = shift_ass[0].shift_type
	else:
		shift_ass = frappe.get_all("Shift Assignment", filters={'employee': employee,
															'start_date': ["<=", getdate(t_date)]}, fields=["*"])
	if len(shift_ass) > 0:
			shift = shift_ass[0].shift_type
			shift_doc = frappe.get_doc("Shift Type", shift)
			s_type = shift_doc.shift_type
			t_check_out = str(attend1).split()[4]
			t_check_out_f_f = timedelta(hours=int(t_check_out.split(":")[0]),minutes=int(t_check_out.split(":")[1]))
			shift_start_t = timedelta(hours=int(str(shift_doc.start_time).split(":")[0]),minutes=int(str(shift_doc.start_time).split(":")[1]))
			if t_check_out_f_f < shift_start_t:
				prev_date = add_days(getdate(t_date),-1)
				return True, prev_date
			return True, False

	return False, False
	
def get_checkouts(args=None,ip=None, port=None,password=0):
	conn = None
	emp_list = [] #110.93.236.48
	if not args:
		args = {"from_date":"2023-03-01","to_date":today()}
	if not password:
		password = 0
	zk = ZK(ip, port=int(port), timeout=1500, password=password, force_udp=False, ommit_ping=False)
	frappe.log_error("Starting out now","Attendance hook test")
	try:
		conn = zk.connect()
		if conn:
			users = conn.get_users()
			if users:
				for u in users:
					#print(u)
					pass

			attendance = conn.get_attendance()
			print("getting attendance data")
			#print(attendance)
			if attendance:
				#print(attendance)
				
				attendance_dict={}
				condition1 =""
				condition2=""
				biometric_list=[]
				b_filters = {}
				if args.get("employee"):
					condition1=" and parent in (select name from `tabEmployee Attendance` where employee='{0}')".format(args.get("employee"))
					condition2=" and biometric_id in (select biometric_id from `tabEmployee` where name='{0}')".format(args.get("employee"))
					b_filters["name"]=args.get("employee")
				if args.get("department"):
					condition1=" and parent in (select name from `tabEmployee Attendance` where department='{0}')".format(args.get("department"))
					condition2=" and biometric_id in (select biometric_id from `tabEmployee` where department='{0}')".format(args.get("department"))
					b_filters["department"]=args.get("department")
				if args.get("employee") and args.get("department"):
					condition1=" and parent in (select name from `tabEmployee Attendance` where employee='{0}' and department='{1}')".format(args.get("employee"),args.get("department"))
					condition2=" and biometric_id in (select biometric_id from `tabEmployee` where name='{0}' and department='{1}')".format(args.get("employee"),args.get("department"))

				B_r = frappe.db.get_all("Employee",filters=b_filters,fields=["biometric_id"])
				for bid in B_r:
					biometric_list.append(bid.biometric_id)
				frappe.db.sql(""" delete from `tabAttendance Logs` where attendance_date >= %s and attendance_date <= %s and ip=%s {0} """.format(condition2), (args.get("from_date"),args.get("to_date"),ip+":"+port))
				frappe.db.sql(""" update `tabEmployee Attendance Table` set check_out_1=NULL, late_sitting=NULL, night_switch=0 where date >= %s and date <= %s and ip=%s and type!="Adjustment"{0} """.format(condition1), (args.get("from_date"),args.get("to_date"),ip+":"+port))
				frappe.db.commit()
				for attend1 in attendance:
					if getdate(str(attend1).split()[3]) < getdate(args.get("from_date")) or getdate(str(attend1).split()[3]) > getdate(args.get("to_date")):
						continue
					if len(biometric_list) > 0:
						if str(attend1).split()[1] not in biometric_list:
							continue
					if attendance_dict.get(str(attend1).split()[1]):
						if attendance_dict.get(str(attend1).split()[1]).get(str(attend1).split()[3]):
							shift, prev_date = check_time(attend1)
							if shift:
									if prev_date:
										if attendance_dict.get(str(attend1).split()[1]).get(str(prev_date)):
											attendance_dict.get(str(attend1).split()[1]).get(str(prev_date))["check out"]=str(attend1).split()[4]
											attendance_dict.get(str(attend1).split()[1]).get(str(prev_date))["checkout string"]=str(attend1)
										else:
											attendance_dict[str(attend1).split()[1]]={
												str(prev_date) :{
													"check out": str(attend1).split()[4],
													"checkout string":str(attend1)
												}
											}
									else:
										flg = True

							else: 
								flg = True
							
							if flg:
								attendance_dict.get(str(attend1).split()[1]).get(str(attend1).split()[3])["check out"]=str(attend1).split()[4]
								attendance_dict.get(str(attend1).split()[1]).get(str(attend1).split()[3])["checkout string"]=str(attend1)
							print("done")
						else:
							shift, prev_date = check_time(attend1)
							if prev_date:
								attendance_dict.get(str(attend1).split()[1])[str(prev_date)]={
									"check out": str(attend1).split()[4],
									"checkout string":str(attend1)
								}
							else:
								attendance_dict.get(str(attend1).split()[1])[str(attend1).split()[3]]={
									"check out": str(attend1).split()[4],
									"checkout string":str(attend1)
								}
					else:
						
						shift, prev_date = check_time(attend1)
						if prev_date:
							attendance_dict[str(attend1).split()[1]]={
								str(prev_date) :{
									"check out": str(attend1).split()[4],
									"checkout string":str(attend1)
								}
							}
						else:
							attendance_dict[str(attend1).split()[1]]={
								str(attend1).split()[3] :{
									"check out": str(attend1).split()[4],
									"checkout string":str(attend1)
								}
							}
					
					

				import json
				#print(attendance_dict)
				for users in attendance_dict:
					print(users)
					for dates in attendance_dict[users]:
						try:
							date = dates
							check_in = attendance_dict[users][dates].get("check in")
							check_in_string = attendance_dict[users][dates].get("checkin string")
							check_out = attendance_dict[users][dates].get("check out")
							check_out_string = attendance_dict[users][dates].get("checkout string")
							
							check_in = None
							temp_chk_in = None
							
							if check_out:
									
									if check_in:
										x = datetime.strptime(
                        					str(temp_chk_in), '%H:%M:%S').time()
										y = datetime.strptime(
                        					str(check_out), '%H:%M:%S').time()
										hi,mi,si = str(x).split(':')
										ho,mo,so = str(y).split(':')
										diff_time = timedelta(hours=0, minutes=30, seconds=0)
										
										if (timedelta(hours=float(ho), minutes=float(mo), seconds=float(so))-timedelta(hours=float(hi), minutes=float(mi), seconds=float(si))) < diff_time:
											continue

									res = frappe.db.sql(""" select name, biometric_id from `tabAttendance Logs` where 
									biometric_id=%s and attendance_date=%s and attendance_time=%s and type='Check Out'""", 
									(users, str(date), check_out))
									if res:
										
										atl = frappe.get_doc("Attendance Logs",res[0][0])
										atl.save()
									else:
										print("adding check out")
										doc2 = frappe.new_doc("Attendance Logs")
										doc2.attendance = check_out_string
										doc2.biometric_id= users
										doc2.attendance_date= str(date)
										doc2.attendance_time= str(check_out)
										doc2.type = "Check Out"
										doc2.ip = '182.184.121.132:4371'
										doc2.save(ignore_permissions=True)
						except:
							frappe.log_error(frappe.get_traceback(),"Attendance hook test")
				
				
	except Exception as e:
		frappe.log_error ("Process terminate : {}"+frappe.get_traceback())
	finally:
		if conn:
			conn.disconnect()




from zk import ZK
from concurrent.futures import ThreadPoolExecutor
import frappe
from frappe import _
from frappe.exceptions import ValidationError

# Function to get check-ins and check-outs from a single machine
def get_checkins_checkouts(args, ip, port):
    try:
        # Connect to the ZK device (no password required)
        zk = ZK(ip, port=int(port), timeout=30)
        conn = zk.connect()
        conn.disable_device()

        # Fetch attendance logs
        logs = conn.get_attendance()  # ✅ Fetch all logs at once
        conn.enable_device()
        conn.disconnect()

        # Return only necessary data (employee_id and timestamp)
        return [(log.user_id, log.timestamp) for log in logs]

    except Exception as e:
        frappe.log_error(message=f"Error fetching data from {ip}:{port} - {str(e)}", title="ZK Attendance Fetch Error")
        return []  # Return an empty list in case of error

# Function to fetch attendance from all machines
def execute_job(args):
    try:
        # Log the arguments to help debug the issue
        frappe.log_error(message=f"Starting attendance job with args: {args}", title="Job Arguments")
        
        # Validate from_date and to_date in the args
        from_date = args.get('from_date')
        to_date = args.get('to_date')
        
        if not from_date or not to_date:
            frappe.log_error(message=f"Missing from_date or to_date: from_date={from_date}, to_date={to_date}", title="Missing Date Parameters")
            raise ValidationError(_("Missing from_date or to_date."))

        # Fetch machine details from V HR Settings
        hr_settings = frappe.get_single('V HR Settings')
        machines = [
            {'ip': row.ip, 'port': row.port, 'password': row.password}
            for row in hr_settings.attendance_machine
        ]

        if not machines:
            frappe.log_error(message="No machines provided for attendance fetch.", title="No Machines Provided")
            raise ValidationError(_("No machines configured for attendance fetch."))

        # Validate cmd (command) parameter in args
        if not args.get('cmd'):
            frappe.log_error(message="No command provided (cmd).", title="Missing Command")
            raise ValidationError(_("No command (cmd) provided."))

        # Attempt to fetch attendance logs from all machines
        try:
            result = fetch_all_attendance(args, machines)
            frappe.log_error(message=f"Attendance fetch result: {result}", title="Attendance Fetch Result")
        except Exception as fetch_error:
            frappe.log_error(message=f"Error in fetch_all_attendance: {str(fetch_error)}", title="Fetch Attendance Error")
            raise ValidationError(_("Error fetching attendance logs."))

        # Return the result after processing
        frappe.log_error(message=f"Attendance job completed successfully with result: {result}", title="Job Success")
        return result

    except Exception as e:
        # General exception handling for the job
        frappe.log_error(message=f"Error in execute_job: {str(e)}", title="Execute Job Error")
        raise ValidationError(_("Error executing attendance job."))

def update_employee_attendance(biometric_id, attendance_date, attendance_time):
    try:
        # Debug: Log the biometric ID being processed
        frappe.log_error(f"Processing biometric_id: {biometric_id}", "Attendance Debug")

        # Fetch employee linked to biometric_id
        employee = frappe.db.get_value("Employee", {"biometric_id": biometric_id}, "name")

        # Debug: Log the employee fetch result
        frappe.log_error(f"Employee lookup result for {biometric_id}: {employee}", "Attendance Debug")

        if not employee:
            frappe.log_error(f"Employee not found in the system for biometric_id: {biometric_id}", "Attendance Error")
            return  # Skip if employee is not found

        # Convert attendance_date to month and year
        attendance_date_obj = datetime.strptime(attendance_date, "%d-%m-%Y")  # Fix applied here
        month = attendance_date_obj.strftime("%B")  # Get full month name
        year = attendance_date_obj.year  # Get year as integer

        # Debug: Log extracted month and year
        frappe.log_error(f"Extracted month and year: {month}, {year}", "Attendance Debug")

        # Check if an attendance record exists for this employee in the given month & year
        attendance = frappe.get_value(
            "Employee Attendance", 
            {"employee": employee, "month": month, "year": year},  
            ["name"], 
            as_dict=True
        )

        # Debug: Log attendance fetch result
        frappe.log_error(f"Attendance record lookup result: {attendance}", "Attendance Debug")

        if attendance:
            # Fetch full Employee Attendance document
            attendance_doc = frappe.get_doc("Employee Attendance", attendance["name"])

            # Find matching child row for this date
            child_row = next((row for row in attendance_doc.table1 if row.date == attendance_date), None)

            if child_row:
                # Convert current time and update check-in and check-out times
                current_time = datetime.strptime(attendance_time, "%H:%M:%S")

                # Debug: Log check-in update
                frappe.log_error(f"Updating check-in/check-out for existing row: {child_row.name}", "Attendance Debug")

                # Update check-in to the earliest time (first check-in)
                if child_row.check_in_1:
                    check_in_time = datetime.strptime(child_row.check_in_1, "%H:%M:%S")
                    child_row.check_in_1 = min(check_in_time, current_time).strftime("%H:%M:%S")
                else:
                    child_row.check_in_1 = attendance_time  # First check-in

                # Update check-out to the latest time (last check-out)
                if child_row.check_out_1:
                    check_out_time = datetime.strptime(child_row.check_out_1, "%H:%M:%S")
                    child_row.check_out_1 = max(check_out_time, current_time).strftime("%H:%M:%S")
                else:
                    child_row.check_out_1 = attendance_time  # First check-out
            

            else:
                # Debug: Log new row creation
                frappe.log_error(f"Creating new child row for date: {attendance_date}", "Attendance Debug")

                # Add a new row if no existing row matches the date
                attendance_doc.append("table1", {
                    "date": attendance_date,  
                    "check_in_1": attendance_time,  # First check-in
                    "check_out_1": attendance_time  # Initially same as check-in
                })

            attendance_doc.save(ignore_permissions=True)

        else:
            frappe.log_error(f"Attendance record not found, creating a new one", "Attendance Debug")

            # Create a new attendance document with a child table row
            doc = frappe.get_doc({
                "doctype": "Employee Attendance",
                "employee": employee,
                "month": month,
                "year": year,
                "table1": [
                    {
                        "date": attendance_date,
                        "check_in_1": attendance_time,  # First check-in
                        "check_out_1": attendance_time  # Initially same as check-in
                    }
                ]
            })
            doc.insert(ignore_permissions=True)
            doc.save()

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Error updating attendance for {biometric_id}: {str(e)}", "Attendance Update Error")

import calendar
from datetime import datetime

def is_valid_date(date_str):
    """Check if a date string is valid and exists in the calendar."""
    try:
        # Parse the date string
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        # Check if the date exists in the calendar
        year, month, day = date_obj.year, date_obj.month, date_obj.day
        return day <= calendar.monthrange(year, month)[1]
    except ValueError:
        # If ValueError is raised, the date is invalid
        return False


import frappe
import calendar
from datetime import datetime
from frappe import _ 
from frappe.utils.background_jobs import enqueue


@frappe.whitelist()
def test_enqueue():
    """Enqueue the attendance marking process to avoid timeout and enable progress tracking."""
    enqueue(test, queue="long", timeout=9000000)  # Run in the background


@frappe.whitelist()
def test():
    # Fetch all employees with a biometric ID
    employees = frappe.db.sql("""
        SELECT name, biometric_id FROM `tabEmployee` WHERE biometric_id IS NOT NULL and status = "Active"
    """, as_dict=True)

    if not employees:
        frappe.log_error("No employees found with biometric IDs", "Attendance Marking Error")
        return

    for emp in employees:
        biometric_id = emp["biometric_id"]
        employee_name = emp["name"]

        # Fetch all attendance logs for the employee
        attendance_logs = frappe.db.sql("""
            SELECT attendance_date, attendance_time FROM `tabAttendance Logs` 
            WHERE biometric_id = %s 
            ORDER BY attendance_date, attendance_time
        """, (biometric_id,), as_dict=True)

        if not attendance_logs:
            frappe.log_error(f"No attendance logs found for biometric ID {biometric_id}", "Attendance Log Error")
            continue  # Skip this employee and move to the next

        # Group logs by (year, month)
        logs_by_month = {}
        for log in attendance_logs:
            attendance_date_obj = datetime.strptime(log["attendance_date"], "%Y-%m-%d")
            month = attendance_date_obj.strftime('%B')
            year = attendance_date_obj.year

            key = (year, month)
            if key not in logs_by_month:
                logs_by_month[key] = []
            logs_by_month[key].append(log)

        # Process each month separately
        for (year, month), logs in logs_by_month.items():
            # Check if Employee Attendance exists for this month/year
            attendance_doc_name = frappe.db.get_value(
                "Employee Attendance", {"employee": employee_name, "month": month, "year": year}, "name"
            )

            if attendance_doc_name:
                attendance_doc = frappe.get_doc("Employee Attendance", attendance_doc_name)
            else:
                attendance_doc = frappe.get_doc({
                    "doctype": "Employee Attendance",
                    "employee": employee_name,
                    "month": month,
                    "year": year
                })
                num_days_in_month = calendar.monthrange(year, datetime.strptime(month, '%B').month)[1]
                
                # Pre-fill attendance table for all days in the month
                for day in range(1, num_days_in_month + 1):
                    date_str = f"{year}-{datetime.strptime(month, '%B').month:02d}-{day:02d}"
                    attendance_doc.append("table1", {
                        "date": date_str,
                        "check_in_1": None,
                        "check_out_1": None
                    })

            # Update attendance records in the respective month
            for log in logs:
                attendance_date_obj = datetime.strptime(log["attendance_date"], "%Y-%m-%d")
                attendance_time = log["attendance_time"]

                # Find the correct row for this date
                child_row = next((row for row in attendance_doc.table1 if row.date == log["attendance_date"]), None)

                if child_row:
                    current_time = datetime.strptime(attendance_time, "%H:%M:%S")

                    # Update check-in (earliest time)
                    if child_row.check_in_1:
                        check_in_time = datetime.strptime(child_row.check_in_1, "%H:%M:%S")
                        child_row.check_in_1 = min(check_in_time, current_time).strftime("%H:%M:%S")
                    else:
                        child_row.check_in_1 = attendance_time  # First check-in

                    # Update check-out (latest time)
                    if child_row.check_out_1:
                        check_out_time = datetime.strptime(child_row.check_out_1, "%H:%M:%S")
                        child_row.check_out_1 = max(check_out_time, current_time).strftime("%H:%M:%S")
                    else:
                        child_row.check_out_1 = attendance_time  # First check-out

            if not attendance_doc_name:
                attendance_doc.insert(ignore_permissions=True)  # Insert only if it's a new document
            else:
                attendance_doc.save(ignore_permissions=True)  # Save if it's an existing document

    frappe.db.commit()  # Commit all changes at once
    frappe.log_error("Attendance processing completed for all employees", "Attendance Log")

from collections import defaultdict
from datetime import datetime

def fetch_all_attendance(args, machines):
    try:
        # Log machines being used for parallel fetching
        frappe.log_error(message=f"Machines being used: {machines}", title="Machines for Fetching Attendance")

        # Execute attendance fetching in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(machines)) as executor:
            # Fetch data from each machine in parallel
            all_logs = list(executor.map(lambda m: get_checkins_checkouts(args, m['ip'], m['port']), machines))

        # Flatten the list of logs from all machines
        all_logs = [log for logs in all_logs for log in logs]

        # Ensure all logs have the correct structure (employee_id, timestamp)
        if not all_logs:
            frappe.log_error(message="No attendance logs found to insert.", title="No Logs Found")
            raise ValidationError(_("No attendance logs found to insert."))

        # Group logs by employee and date
        logs_by_employee_and_date = defaultdict(lambda: defaultdict(list))
        for log in all_logs:
            biometric_id, timestamp = log
            attendance_date = timestamp.date()
            logs_by_employee_and_date[biometric_id][attendance_date].append(timestamp)

        # Format the logs for insertion into the database
        formatted_logs = []
        for biometric_id, dates in logs_by_employee_and_date.items():
            for attendance_date, timestamps in dates.items():
                # Sort timestamps for the day
                timestamps.sort()

                # Assign log types
                for i, timestamp in enumerate(timestamps):
                    if i == 0:
                        log_type = "Check In"  # First log of the day
                    elif i == len(timestamps) - 1:
                        log_type = "Check Out"  # Last log of the day
                    else:
                        continue  # Skip intermediate logs (optional)

                    attendance_time = timestamp.time()

                    # Format the attendance string
                    attendance = f"<Attendance>: {biometric_id} : {attendance_date} {attendance_time} (1, 0)"

                    formatted_logs.append({
                        "biometric_id": biometric_id,
                        "attendance_date": attendance_date,
                        "attendance_time": attendance_time,
                        "type": log_type,  # Assign log type (Check In/Check Out)
                        "ip": "Machine_IP",  # This can be dynamic if you need to store the machine IP
                        "attendance": attendance  # The correctly formatted attendance field
                    })
                    
        # update_employee_attendance(biometric_id, attendance_date, attendance_time)
        # mark_employee_attendance()

        # Bulk insert into the Attendance Logs doctype
        try:
            frappe.db.bulk_insert(
                "Attendance Logs", 
                fields=["name", "biometric_id", "attendance_date", "attendance_time", "type", "ip", "attendance"], 
                values=[
                    (frappe.generate_hash(length=10), log["biometric_id"], log["attendance_date"], log["attendance_time"], log["type"], log["ip"], log["attendance"])
                    for log in formatted_logs
                ]
            )

            frappe.log_error(message=f"Inserted {len(formatted_logs)} records successfully.", title="Bulk Insert Success")
            
            return f"Inserted {len(formatted_logs)} records successfully"

        except Exception as e:
            frappe.log_error(message=f"Error during bulk insert of attendance logs: {str(e)}", title="Bulk Insert Error")
            raise ValidationError(_("Error inserting attendance logs into the database."))

    except Exception as e:
        frappe.log_error(message=f"Error in fetch_all_attendance: {str(e)}", title="Fetch Attendance Error")
        raise ValidationError(_("Error fetching attendance logs."))
    

@frappe.whitelist()
def get_attendance_from_api(date):
	response = request(method="GET", url="""https://api.ubiattendance.com/attendanceservice/getempattendance?apikey==AlVGhUVup0cNFjWadVb4xmVwolNZpmTXJmVKJnUrRWYWZFcHZVMotmVrlTUTxmWOJ1MCl1VrZ1dWdlRzpVRax2VtJ1RWJDdPFWMWhlVtRHbW1GaHlFM4gXTHZEWWtmWXVlaGVVVB1TP&Attendancedate={0} 
		""".format(date))
	response.raise_for_status()
	data = json.loads(response.text.split("]")[0]+"]")
	for item in data:
		chk_in = frappe.db.sql(""" select name, biometric_id from `tabAttendance Logs` where 
			biometric_id=%s and attendance_date=%s and attendance_time=%s and type='Check In'""", 
									(item["Employeecode"], item["attendancedate"], item["Timein"]))
		if not chk_in:
			#add checkin
			checkin = frappe.new_doc("Attendance Logs")
			checkin.attendance = "&lt;Attendance&gt;: {0} : {1} {2} (1, 1)".format(item["Employeecode"],item["attendancedate"],item["Timein"])
			checkin.biometric_id= item["Employeecode"]
			checkin.attendance_date= item["attendancedate"]
			checkin.attendance_time= item["Timein"]
			checkin.type = "Check In"
			checkin.ip = 'from_rest_api'
			checkin.save()

		else:
			doc = frappe.get_doc("Attendance Logs",chk_in[0][0])
			doc.attendance = "&lt;Attendance&gt;: {0} : {1} {2} (1, 1)".format(item["Employeecode"],item["attendancedate"],item["Timein"])
			doc.biometric_id= item["Employeecode"]
			doc.attendance_date= item["attendancedate"]
			doc.attendance_time= item["Timein"]
			doc.type = "Check In"
			doc.ip = 'from_rest_api'
			doc.save()



		chk_out = frappe.db.sql(""" select name, biometric_id from `tabAttendance Logs` where 
									biometric_id=%s and attendance_date=%s and attendance_time=%s and type='Check Out'""", 
									(item["Employeecode"], item["attendancedate"], item["Timeout"]))
		if not chk_out:
			#add chkout
			chkout = frappe.new_doc("Attendance Logs")
			chkout.biometric_id= item["Employeecode"]
			chkout.attendance = "&lt;Attendance&gt;: {0} : {1} {2} (1, 1)".format(item["Employeecode"],item["attendancedate"],item["Timeout"])
			chkout.attendance_date= item["attendancedate"]
			chkout.attendance_time= item["Timeout"]
			chkout.type = "Check Out"
			chkout.ip = 'from_rest_api'
			chkout.save()

		else:
			doc = frappe.get_doc("Attendance Logs",chk_out[0][0])
			doc.attendance = "&lt;Attendance&gt;: {0} : {1} {2} (1, 1)".format(item["Employeecode"],item["attendancedate"],item["Timeout"])
			doc.biometric_id= item["Employeecode"]
			doc.attendance_date= item["attendancedate"]
			doc.attendance_time= item["Timeout"]
			doc.type = "Check Out"
			doc.ip = 'from_rest_api'
			doc.save()

	return "done"
		

@frappe.whitelist()
def get_attendance_from_hook():
	frappe.log_error("Fetchhing","BGHOOK")
	args={
		"from_date":add_days(today(),-1),
		"to_date":getdate(today()),
	}
	get_attendance_long(**args)


@frappe.whitelist()
def email_report():
		from frappe.email.doctype.auto_email_report.auto_email_report import send_now
		auto_email_report = frappe.get_doc('Auto Email Report', "Daily Attendance")
		auto_email_report.update({
			"filters": """{."from.":\""""+str(getdate(today()))+"""\",\"to\":\""""+str(getdate(today()))+"""\"}"""
		})
		auto_email_report.save()
		send_now("Daily Attendance")

		