# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe import msgprint, _
from datetime import datetime
from datetime import timedelta
from datetime import date as dt
import datetime as special
import time
from frappe.utils import cstr, flt,getdate, today, get_time
import calendar
from hrms.hr.utils import get_holidays_for_employee
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.setup.doctype.employee.employee import (
    InactiveEmployeeStatusError
)


class EmployeeAttendance(Document):
    def autoname(self):
        if not self.employee or not self.month:
            frappe.throw("Employee and Month must be set before generating the name.")
        self.name = make_autoname(self.employee + '-' + self.month)

    def validate(self):
        total_early = 0
        total_lates = 0
        total_lates1 = 0
        total_half_days = 0
        total_hr_worked = timedelta(hours=0, minutes=0, seconds=0)
        total_per_day_h = timedelta(hours=0, minutes=0, seconds=0)
        total_late_hr_worked = timedelta(hours=0, minutes=0, seconds=0)
        total_early_going_hrs= timedelta(hours=0, minutes=0, seconds=0)
        total_late_coming_hours = timedelta(hours=0, minutes=0, seconds=0)
        total_additional_hours = timedelta(hours=0, minutes=0, seconds=0)
        total_early_ot = timedelta(hours=0, minutes=0, seconds=0)
        total_approved_ot = timedelta(hours=0, minutes=0, seconds=0)
        total_approved_early_ot = timedelta(hours=0, minutes=0, seconds=0)
        required_working_hrs = 0.0
        holiday_halfday_ot =0
        holiday_full_day_ot =0
        self.no_of_holiday_night = 0
        self.total_absents = 0
        # self.late_comparision = 0
        self.late_comparision = 0
        extra_ot_amount = 0
        holiday_doc = None
        self.total_public_holidays = 0
        half_day_leave = None
        self.no_of_nights = 0
        total_working_days=0
        self.total_weekly_off = 0
        present_days=0
        accun_holiday=0
        self.total_extra_duty_for_halfday = 0
        self.total_extra_duty_for_fullday = 0
        holidays = []
        hr_settings = frappe.get_single('V HR Settings')
        allowance_settings = frappe.get_single('Attendance Allowance Settings')
        #try:
        month = self.get_month_no(self.month)
        year = int(self.year)
        _, num_days = calendar.monthrange(year, month)
        first_day = dt(year, month, 1)
        last_day = dt(year, month, num_days)
        

        if hr_settings.period_from != 1:
            if month == 1:
                temp_month = 12
            else:
                temp_month = month - 1
            first_day = dt(year, temp_month, int(hr_settings.period_from))
            last_day = dt(year, month, int(hr_settings.period_to))
            _, num_days = calendar.monthrange(year, temp_month)
            num_days = num_days - int(hr_settings.period_from) + int(hr_settings.period_to) + 1

        holidays = get_holidays_for_employee(self.employee,first_day,last_day)
        self.total_working_days = num_days -len(holidays)
        self.no_of_sundays = 0
        self.month_days = num_days
        # except:
        #     pass
        holiday_flag = False
        leave_flag = False
        total_holiday_hours = timedelta(hours=0,minutes=0,seconds=0)
        previous = None
        index = 0
        total_seconds1 = 0
        total_seconds2 = 0
        total_seconds3 = 0
        total_seconds_approved_eot = 0
        total_seconds_approved_ot1 = 0
        total_seconds_approved_ot2 = 0
        time_seconds_approved_eot1 = 0
        early_going_count = 0
        total_early_going_time = timedelta()  # Use timedelta for time calculations
        total_early_hours = 0
        total_early_goings = 0
        total_early_going_hours = timedelta()
        self.half_day_for_check_in = 0
        half_day_for_check_in = 0
        mark_absent = 0
        total_time = timedelta()
        absent_threshould = 0
        half_day_threshould = 0 
        present_threshould = 0 
        missing_absent_check_in = 0
        missing_half_day_check_in = 0
        # Initialize variables
        missing_absent_check_out = 0
        half_day_mark_due_to_missing_check_out = 0
        absent_threshould_weekly_off = 0
        half_day_threshould_weekly_off = 0
        present_threshould_weekly_off = 0
        manual = 0
        self.weekend_half_day = 0
        self.weekend_absent = 0
        self.weekend_present = 0
        late = 0
        self.lates = 0
        self.attendance_allowance = 0 
        self.puntuality_allowance = 0

        # Dictionary to map month names to numbers
        # Dictionary to map month names to numbers
        
        # Initialize manual_absent before the loop
        self.manual_absent = 0  
        
        holiday_dates = {str(getdate(d.holiday_date)) for d in holidays}  # Ensure correct format

        for data in self.table1:
            if data.check_in_1 == data.check_out_1:
                data.check_out_1 = None
            data_date = str(getdate(data.date))  # Ensure consistency

            # frappe.errprint(f"Checking {data_date} against holidays {holiday_dates}")

            # Step 1: Mark Weekly Off based on holiday list
            if data_date in holiday_dates:  # If it is a holiday
                data.weekly_off = 1
                self.total_weekly_off += 1
                # data.absent_due_to_below_threshould = 0  # Ensure it's not marked as absent on holidays
            else:  # If not a holiday
                data.weekly_off = 0
                # frappe.errprint(f"Date: {data_date}, Weekly Off: {data.weekly_off}, Absent: {data.absent_due_to_below_threshould}")

                # Step 2: Mark Absent if both check-in & check-out are missing
                if data.check_in_1 is None or data.check_in_1 is "" and data.check_out_1 is None or data.check_out_1 is "" and data.weekly_off == 0:
                    # data.absent_due_to_below_threshould = 1
                    data.present_due_to_above_threshould_weekly_off = 0 
                    data.half_day_due_to_below_threshould_weekly_off = 0
                    data.absent_due_to_below_threshould_weekly_off = 0
                    data.half_day_due_to_below_threshould = 0
                    data.present_due_to_above_threshould = 0
                    # frappe.errprint(f"Date: {data_date}, Weekly Off: {data.weekly_off}, Absent: {data.absent_due_to_below_threshould}")
                else:
                    data.absent_due_to_below_threshould = 0

            



        for data in self.table1:
            if str(getdate(data.date)) in holiday_dates:  # If not a holiday
                # frappe.errprint(f"hd {holiday_dates}")
                data.weekly_off = 1
                data.weekend = 1
        #         if data.check_in_1 is None and data.check_out_1 is None:
        #             data.absent_due_to_below_threshould = 1  # Mark absent
        
        
        

                

        
        for data in self.table1:
            

            date1 = data.date
            # print(f"\n\n\n\\\n\n\n{date1}")
            dateobj = getdate(date1)
            day_of_week = dateobj.strftime('%A')
            data.day = day_of_week
            shift = None
            shift_ass = frappe.get_all("Shift Assignment", filters={'employee': self.employee,
                                                                    'start_date': ["<=", getdate(data.date)],'end_date': [">=", getdate(data.date)]}, fields=["*"])
            if len(shift_ass) > 0:
                shift = shift_ass[0].shift_type
            else:
                shift_ass = frappe.get_all("Shift Assignment", filters={'employee': self.employee,
                                                                    'start_date': ["<=", getdate(data.date)]}, fields=["*"]) 
            if len(shift_ass) > 0:
                shift = shift_ass[0].shift_type
            if shift == None:
                pass
                # frappe.throw(_("No shift available for this employee{0}").format(self.employee))
            data.shift = shift
            shift_doc = frappe.get_doc("Shift Type", shift)
            s_type = shift_doc.shift_type
            data.shift_in = shift_doc.start_time
            data.shift_out =  shift_doc.end_time
            
            # from datetime import datetime, timedelta

            if data.shift_out:
                if isinstance(data.shift_out, str):
                    shift_out_time = datetime.strptime(data.shift_out, "%H:%M:%S").time()
                elif isinstance(data.shift_out, timedelta):
                    shift_out_time = (datetime.min + data.shift_out).time()
                else:
                    shift_out_time = None
            else:
                shift_out_time = None

            check_out_1_time = data.check_out_1
            if check_out_1_time:
                if isinstance(check_out_1_time, str):
                    check_out_1_time = datetime.strptime(check_out_1_time, "%H:%M:%S").time()
                elif isinstance(check_out_1_time, timedelta):
                    check_out_1_time = (datetime.min + check_out_1_time).time()
                else:
                    check_out_1_time = None
            else:
                check_out_1_time = None

            # Ensure values are not None before performing calculations
            if shift_out_time and check_out_1_time:
                shift_out_dt = datetime.combine(datetime.min, shift_out_time)
                check_out_1_dt = datetime.combine(datetime.min, check_out_1_time)

                estimate_late = check_out_1_dt - shift_out_dt  # ✅ Now works
                
                one_hour = timedelta(hours=1)
                two_hour = timedelta(hours=2)

                # Convert timedelta to string (hh:mm:ss) for storing in `data.estimate_late`
                if estimate_late > two_hour:
                    data.estimated_late = str(two_hour)
                elif estimate_late > one_hour:
                    data.estimated_late = str(estimate_late)
                    
                    # data.data = str(estimate_late)
                else:
                    data.estimated_late = ""
                    data.data = ""
                # data.estimated_late = str(estimate_late)
            else:
                pass
            
            #     frappe.throw(("Shift In or Check Out time is missing for employee {0} on {1}")
            #  .format(self.employee, data.date))
            
        for data in self.table1:
            for i in range(len(self.table1)):
                data = self.table1[i]

                # Step 1: Check if the current row is a Weekly Off (potential sandwich)
                if data.weekly_off == 1:
                    previous_row = self.table1[i - 1] if i > 0 else None
                    next_row = self.table1[i + 1] if i + 1 < len(self.table1) else None

                    # Step 2: Ensure previous and next rows exist
                    if previous_row and next_row:
                        # ✅ Modified Condition: Ensure the previous and next rows are absent (not another weekly off)
                        prev_condition = previous_row.weekly_off == 0 and previous_row.absent_due_to_below_threshould == 1
                        next_condition = next_row.weekly_off == 0 and next_row.absent_due_to_below_threshould == 1

                        if prev_condition and next_condition:
                            # ✅ Mark sandwich for previous, middle, and next row
                            previous_row.sandwitch = 1
                            data.sandwitch = 1
                            next_row.sandwitch = 1
                            # frappe.errprint(f"Marked sandwich: {previous_row.date}, {data.date}, {next_row.date}")
                        else:
                            # ❌ If condition not met, reset the fields
                            previous_row.sandwitch = 0
                            data.sandwitch = 0
                            next_row.sandwitch = 0
                            # frappe.errprint(f"Reset sandwich due to condition not met: "
                            #                 f"prev_weekly_off={previous_row.weekly_off}, prev_absent={previous_row.absent_due_to_below_threshould}, "
                            #                 f"next_weekly_off={next_row.weekly_off}, next_absent={next_row.absent_due_to_below_threshould}")
                    else:
                        # ❌ Reset if no valid previous or next row exists
                        data.sandwitch = 0
                        # frappe.errprint(f"Reset sandwich: {data.date} (no previous or next row)")



            
            


        for data in self.table1:
            employee1 = frappe.get_doc("Employee",self.employee)
            performance_allowance = employee1.custom_performance_allowance
            if performance_allowance == 1:
                pass
        
        month_name_to_number = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }

        for data in self.table1:
            joining_date = self.joining_date

            if joining_date:
                # Access year and month directly from the joining_date object
                joining_year = joining_date.year
                joining_month = joining_date.month
                joining_date_str = joining_date.strftime("%d-%m-%Y")
                joining_day = joining_date.day

                # Convert self.year and self.month from string to integer (month from dictionary)
                current_year = int(self.year)
                current_month = month_name_to_number.get(self.month, 0)  # Default to 0 if month name is invalid

                # Compare years and months
                if joining_year <= current_year:
                    if joining_month <= current_month:
                        # frappe.log_error(f"joining_month{joining_month}current_month{current_month}")
                        if joining_day:
                            for a in allowance_settings.allowance_eligibility_ct:
                                if a.from_date <= joining_day <= a.to_date:
                                    self.allowance_ = a.percentage
                                    break 
                                else:
                                    self.allowance_ = 0
                        else:
                            self.allowance_ = 0
                        # frappe.log_error(f"joining_day{joining_day}")
                    else:
                        # frappe.log_error(f"joining_month{joining_month}current_month{current_month}")
                        self.allowance_ = 0
                else:
                    self.allowance_ = 0
            else:
                self.allowance_ = 0       


        # # Convert time string to timedelta
        # def str_to_timedelta(time_str):
        #     if time_str:
        #         time_parts = list(map(int, time_str.split(':')))
        #         return timedelta(hours=time_parts[0], minutes=time_parts[1], seconds=time_parts[2])
        #     return timedelta(0)
        
        for data in self.table1:
            late += data.late or 0
        self.lates = late

        employee1 = frappe.get_doc("Employee",self.employee)
        allowed_att_allowance = employee1.custom_allowance_allowed
        allowed_puntuality_allowance = employee1.custom_puntuality_allowance
        for data in self.table1:    
            if allowed_att_allowance == 1:
                if allowance_settings.attendance_allowance_allowed:
                    for a in allowance_settings.attendance_allowance_slab:
                        if a.missing_check_in__check_out == self.total_absent_check_in_missing:
                            if self.half_day_threshould == 1: 
                                self.attendance_allowance = a.allowance_amount
                            elif self.half_day_threshould >= 2:
                                self.attendance_allowance = 0
                            elif self.absent_threshould >= 1:
                                self.attendance_allowance = 0
                            else:
                                self.attendance_allowance = a.allowance_amount
            if allowed_puntuality_allowance == 1:
                if allowance_settings.puntuality_allowance == 1:
                    for b in allowance_settings.puntuality_allowance_ct:
                        # Check if `self.lates` is within the range
                        if b.from_late <= self.lates <= b.to_late:
                            self.puntuality_allowance = b.amount
                            break  # Exit loop once the matching range is found
            # if allowed_puntuality_allowance == 1:
            #     if allowance_settings.puntuality_allowance == 1:
            #         for b in allowance_settings.puntuality_allowance_ct:
            #             if self.lates >= b.from_late or self.lates <= b.to_late:
            #                 self.puntuality_allowance = b.amount

                        # else:
                        #     self.attendance_allowance = 1010
            else:
                self.attendance_allowance = 0

            


        for data in self.table1:
            if data.weekly_off == 1:
                # Check if there is a check-in and it's not equal to check-out
                if data.check_in_1 and data.check_in_1 != data.check_out_1:
                    shift = None
                    
                    # Fetch shift assignment for the employee within the date range
                    shift_ass = frappe.get_all(
                        "Shift Assignment",
                        filters={
                            'employee': self.employee,
                            'start_date': ["<=", getdate(data.date)],
                            'end_date': [">=", getdate(data.date)]
                        },
                        fields=["*"]
                    )
                    
                    # If no assignment found within the range, get the closest one before the date
                    if len(shift_ass) == 0:
                        shift_ass = frappe.get_all(
                            "Shift Assignment",
                            filters={
                                'employee': self.employee,
                                'start_date': ["<=", getdate(data.date)]
                            },
                            fields=["*"]
                        )
                    
                    # Get the shift type if any assignment found
                    if len(shift_ass) > 0:
                        shift = shift_ass[0].shift_type
                    else:
                        pass
                        # frappe.throw(_("No shift available for this employee {0}").format(self.employee))
                        # frappe.throw(_("No shift available for this employee {0}").format(self.employee))
                    
                    # Set the shift type in data
                    data.shift = shift

                    # Retrieve the shift details
                    shift_doc = frappe.get_doc("Shift Type", shift)
                    shift_start_time = shift_doc.day[0].start_time  # Assuming start_time is in HH:MM format
                    shift_start_datetime = datetime.strptime(str(shift_start_time), "%H:%M:%S")
                    
                    # Convert check-in time to datetime for comparison
                    check_in_time = datetime.strptime(data.check_in_1, "%H:%M:%S")
                    
                    # Check if the employee is late by comparing check-in with shift start time
                    if check_in_time > shift_start_datetime:
                        data.late = 1  # Mark the employee as late if check-in is after shift start
                    else:
                        data.late = 0  # Not late if check-in is on or before shift start



        # Loop through data
        # absent_threshould_1 = 0
        # self.absent_threshould = sum(data.absent_due_to_below_threshould for data in self.table1)
        


        for data in self.table1:
            
            # self.absent_threshould += data.absent_due_to_below_threshould
            
            
            
            def str_to_timedelta(time_str):
                """Converts time string 'hh:mm:ss' to timedelta object."""
                if time_str:
                    time_parts = list(map(int, time_str.split(':')))
                    return timedelta(hours=time_parts[0], minutes=time_parts[1], seconds=time_parts[2])
                return timedelta(0)

            if data.check_in_1 and data.check_out_1:
                # Calculate total time
                check_in_1 = datetime.strptime(data.check_in_1, "%H:%M:%S")
                check_out_1 = datetime.strptime(data.check_out_1, "%H:%M:%S")
                total_time_timedelta = check_out_1 - check_in_1
                data.total_time = str(total_time_timedelta)
            else:
                data.total_time = None
                
                
            def str_to_timedelta(time_str):
                """Converts a time string 'hh:mm:ss' or timedelta to a timedelta object."""
                if isinstance(time_str, timedelta):  # If it's already timedelta, return it
                    return time_str
                if isinstance(time_str, str) and time_str:  # If it's a string, convert it
                    time_parts = list(map(int, time_str.split(':')))
                    return timedelta(hours=time_parts[0], minutes=time_parts[1], seconds=time_parts[2])
                return timedelta(0)  # Default case

            if data.check_in_1 is None and data.check_out_1 is None and data.weekend == 0:
                # frappe.errprint(f"{data.date}")
                # pass
                data.absent_due_to_below_threshould = 1
               
            if data.weekend == 1:
                data.absent_due_to_below_threshould = 0 

            if data.weekly_off == 0 and data.check_in_1 and data.check_out_1:
                # Fetch Shift Type details
                if data.shift:
                    doc = frappe.get_doc("Shift Type", data.shift)
                    shift_present_threshould = doc.custom_present_threshould or "00:00:00"
                    shift_absent_threshould = doc.custom_absent_threshould_ or "00:00:00"
                    shift_half_day_threshould_copy = doc.custom_halfday_threshould__ or "00:00:00"
                    self.shift_present_threshould = shift_present_threshould
                    self.shift_absent_threshould = shift_absent_threshould
                    self.shift_half_day_threshould_copy = shift_half_day_threshould_copy

                    # Convert thresholds to timedelta
                    absent_threshould_timedelta = str_to_timedelta(shift_absent_threshould)
                    half_day_timedelta = str_to_timedelta(shift_half_day_threshould_copy)
                    present_timedelta = str_to_timedelta(shift_present_threshould)

                    
                if total_time_timedelta >= absent_threshould_timedelta and total_time_timedelta <= half_day_timedelta :
                    data.half_day_due_to_below_threshould = 1
                    data.absent_due_to_below_threshould = 0
                    data.present_due_to_above_threshould = 0
                elif absent_threshould_timedelta > total_time_timedelta:
                    data.half_day_due_to_below_threshould = 0
                    data.absent_due_to_below_threshould = 1
                    data.present_due_to_above_threshould = 0
                elif total_time_timedelta >= present_timedelta:
                    # frappe.errprint(f"{data.date}{total_time_timedelta}{present_timedelta}")
                    data.present_due_to_above_threshould = 1
                    data.half_day_due_to_below_threshould = 0
                    data.absent_due_to_below_threshould = 0
                else:
                    data.present_due_to_above_threshould = 0
                    data.half_day_due_to_below_threshould = 0
                    data.absent_due_to_below_threshould = 0
                    

                # absent_threshould += data.absent_due_to_below_threshould
                # half_day_threshould += data.half_day_due_to_below_threshould
                self.present_threshould = sum(data.present_due_to_above_threshould for data in self.table1)
                self.absent_threshould = sum(data.absent_due_to_below_threshould for data in self.table1)
                self.half_day_threshould = sum(data.half_day_due_to_below_threshould for data in self.table1)

            elif data.weekly_off == 1 and data.check_in_1 and data.check_out_1:
                if data.shift:
                    doc = frappe.get_doc("Shift Type", data.shift)
                    shift_present_threshould = doc.custom_present_threshould or "00:00:00"
                    shift_absent_threshould = doc.custom_absent_threshould_ or "00:00:00"
                    shift_half_day_threshould_copy = doc.custom_halfday_threshould__ or "00:00:00"
                    self.shift_present_threshould = shift_present_threshould
                    self.shift_absent_threshould = shift_absent_threshould
                    self.shift_half_day_threshould_copy = shift_half_day_threshould_copy
                    
                # Convert thresholds to timedelta
                absent_threshould_timedelta = str_to_timedelta(shift_absent_threshould or "00:00:00")
                half_day_timedelta = str_to_timedelta(shift_half_day_threshould_copy or "00:00:00")
                present_timedelta = str_to_timedelta(shift_present_threshould or "00:00:00")

                # Mark as absent, half-day, or present for weekly off
                # if total_time_timedelta < absent_threshould_timedelta:
                if total_time_timedelta >= absent_threshould_timedelta and total_time_timedelta <= half_day_timedelta :
                
                    data.absent_due_to_below_threshould_weekly_off = 0    
                    data.half_day_due_to_below_threshould_weekly_off = 1
                    data.present_due_to_above_threshould_weekly_off = 0
                # elif total_time_timedelta < half_day_timedelta:
                
                elif absent_threshould_timedelta > total_time_timedelta:
                    data.half_day_due_to_below_threshould_weekly_off = 1
                    data.absent_due_to_below_threshould_weekly_off = 0
                    data.present_due_to_above_threshould_weekly_off = 0
                # elif total_time_timedelta >= present_timedelta:
                
                elif total_time_timedelta >= present_timedelta:
                    data.present_due_to_above_threshould_weekly_off = 1
                    data.half_day_due_to_below_threshould_weekly_off = 0
                    data.absent_due_to_below_threshould_weekly_off = 0
                else:
                    
                    data.present_due_to_above_threshould_weekly_off = 0
                    data.half_day_due_to_below_threshould_weekly_off = 0
                    data.absent_due_to_below_threshould_weekly_off = 0
                
                self.weekend_present = sum(data.present_due_to_above_threshould_weekly_off for data in self.table1)
                self.weekend_absent = sum(data.absent_due_to_below_threshould_weekly_off for data in self.table1)
                self.weekend_half_day = sum(data.half_day_due_to_below_threshould_weekly_off for data in self.table1)

                # absent_threshould_weekly_off += data.absent_due_to_below_threshould_weekly_off
                # half_day_threshould_weekly_off += data.half_day_due_to_below_threshould_weekly_off
                # present_threshould_weekly_off += data.present_due_to_above_threshould_weekly_off

        # Set totals
        # self.half_day_threshould = half_day_threshould
        # self.absent_threshould = absent_threshould
        # self.present_threshould = present_threshould

        # self.weekend_half_day = half_day_threshould_weekly_off
        # self.weekend_absent = absent_threshould_weekly_off
        # self.weekend_present = present_threshould_weekly_off

        for data in self.table1:
            if data.check_in_1 is None and data.check_out_1 is None or data.check_in_1 is "" or data.check_out_1 is "" :
                # Both are missing, set everything to 0
                data.check_in_missing = 0
                data.check_out_missing = 0
                data.absent_mark_due_to_missing_check_in = 0
                data.half_day_mark_due_to_missing__check_in = 0
                data.absent_mark_due_to_missing_check_out = 0
                data.half_day_mark_due_to_missing_check_out = 0

            # Case 2: If only check_in_1 is None but check_out_1 is available
            elif data.check_in_1 is None and data.check_out_1 is not None:
                data.check_in_missing = 1
                data.check_out_missing = 0  # check_out is available
                if hr_settings.check_not_marked == 1:
                    if hr_settings.mark_absent == 1:
                        data.absent_mark_due_to_missing_check_in = 1
                    else:
                        data.absent_mark_due_to_missing_check_in = 0
                        
                    if hr_settings.mark_half_day == 1:
                        data.half_day_mark_due_to_missing__check_in = 1
                    else:
                        data.half_day_mark_due_to_missing__check_in = 0

                # Ensure check-out related fields are set to 0 since check_out_1 is present
                data.absent_mark_due_to_missing_check_out = 0
                data.half_day_mark_due_to_missing_check_out = 0

            # Case 3: If only check_out_1 is None but check_in_1 is available
            elif data.check_in_1 is not None and data.check_out_1 is None:
                data.check_in_missing = 0
                data.check_out_missing = 1  # check_out is missing
                if hr_settings.check_out_not_marked == 1:
                    if hr_settings.mark_absent_check_out == 1:
                        data.absent_mark_due_to_missing_check_out = 1
                    else:
                        data.absent_mark_due_to_missing_check_out = 0
                        
                    if hr_settings.mark_half_day_check_out == 1:
                        data.half_day_mark_due_to_missing_check_out = 1
                    else:
                        data.half_day_mark_due_to_missing_check_out = 0
                else:
                    data.absent_mark_due_to_missing_check_out = 0
                    data.half_day_mark_due_to_missing_check_out = 0

            # Case 4: If both check_in_1 and check_out_1 are present
            else:
                # Both check_in_1 and check_out_1 are available, set all missing marks to 0
                data.check_in_missing = 0
                data.check_out_missing = 0
                data.absent_mark_due_to_missing_check_in = 0
                data.half_day_mark_due_to_missing__check_in = 0
                data.absent_mark_due_to_missing_check_out = 0
                data.half_day_mark_due_to_missing_check_out = 0
        
            missing_absent_check_in += data.absent_mark_due_to_missing_check_in
            missing_half_day_check_in += data.half_day_mark_due_to_missing__check_in
            missing_absent_check_out += data.absent_mark_due_to_missing_check_out
            half_day_mark_due_to_missing_check_out += data.half_day_mark_due_to_missing_check_out

        self.total_absent_check_in_missing_1 = (
            missing_absent_check_in - hr_settings.threshould if missing_absent_check_in > 0 else 0
        )
        self.total_absent_check_in_missing = (
            missing_half_day_check_in - hr_settings.threshould if missing_half_day_check_in > 0 else 0
        )
        self.total_absent_missing_check_out = (
            missing_absent_check_out - hr_settings.check_out_threshould if missing_absent_check_out > 0 else 0
        )
        self.total_halfday_missing_check_out = (
            half_day_mark_due_to_missing_check_out - hr_settings.check_out_threshould if half_day_mark_due_to_missing_check_out > 0 else 0
        )


            

            
                


        for data in self.table1:
            # Check if the 'early' checkbox is marked (1 means it's checked)
            if data.early == 1:
                total_early_goings += 1
            
            if data.early_going_hours:
                # If the value is a float, convert it to hours, minutes, and seconds
                if isinstance(data.early_going_hours, float):
                    hours = int(data.early_going_hours)
                    minutes = int((data.early_going_hours - hours) * 60)
                    seconds = int((((data.early_going_hours - hours) * 60) - minutes) * 60)
                    early_going_duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)

                # If the value is a string and represents a float, convert it to hours, minutes, and seconds
                elif isinstance(data.early_going_hours, str):
                    try:
                        # Check if it can be converted to a float
                        float_hours = float(data.early_going_hours)
                        hours = int(float_hours)
                        minutes = int((float_hours - hours) * 60)
                        seconds = int((((float_hours - hours) * 60) - minutes) * 60)
                        early_going_duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                    except ValueError:
                        continue  # Skip if the string cannot be converted to float
                    
                # If the value is already a timedelta, use it directly
                elif isinstance(data.early_going_hours, timedelta):
                    early_going_duration = data.early_going_hours
                else:
                    continue  # Skip if not a valid type

                # Add to total early going hours
                total_early_going_hours += early_going_duration

        # Store the count of marked checkboxes in the parent doctype
        self.early_going = total_early_goings


        if self.table1:
            first_date = self.table1[0].date  
            last_date = self.table1[-1].date 
             

            # Fetch fuel rate
            fuel = frappe.get_list("Fuel Rate", filters={
                "from_date": [">=", first_date],
                "to_date": ["<=", last_date]
            }, fields=['*'])

            if fuel and fuel[0]:
                fuel_allowed = fuel[0].rate_per_litre  
                self.fuel_allowance_rate = fuel_allowed
                if self.fuel_allowance_rate and self.fuel_allowance_limit:
                    self.fuel_allowance_total = self.fuel_allowance_rate * self.fuel_allowance_limit
                else:
                    self.fuel_allowance_total = 0
            else:
                self.fuel_allowance_rate = "0" 
            

        for data in self.table1:
            
            
            # if data.day_type == "Weekly Off":
            #     data.weekly_off = 1

            # Sum early_ot
            if data.early_ot:
                try:
                    time_parts = [int(part) for part in data.early_ot.split(':')]
                    if len(time_parts) == 3:
                        time_seconds1 = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
                        total_seconds1 += time_seconds1
                        print(f"Added {time_seconds1} seconds from {data.early_ot}")
                #     else:
                #         print(f"Invalid time format in early_ot: {data.early_ot}")
                except ValueError:
                    print(f"Error processing time format in early_ot: {data.early_ot}")
            # else:
                # print(f"early_ot is None or empty for row")
                # pass

            # Sum estimated_late
            if data.estimated_late:
                try:
                    time_parts1 = [int(part) for part in data.estimated_late.split(':')]
                    if len(time_parts1) == 3:
                        time_seconds2 = time_parts1[0] * 3600 + time_parts1[1] * 60 + time_parts1[2]
                        total_seconds2 += time_seconds2
                        print(f"Added {time_seconds2} seconds from {data.estimated_late}")
                    else:
                        print(f"Invalid time format in estimated_late: {data.estimated_late}")
                except ValueError:
                    print(f"Error processing time format in estimated_late: {data.estimated_late}")
            else:
                # print(f"estimated_late is None or empty for row")
                pass

            # Sum estimate_early (fixed variable and print statement)
            if data.estimate_early:
                try:
                    time_parts2 = [int(part) for part in data.estimate_early.split(':')]
                    if len(time_parts2) == 3:
                        time_seconds3 = time_parts2[0] * 3600 + time_parts2[1] * 60 + time_parts2[2]
                        total_seconds3 += time_seconds3
                        print(f"Added {time_seconds3} seconds from {data.estimate_early}")
                    else:
                        print(f"Invalid time format in estimate_early: {data.estimate_early}")
                except ValueError:
                    print(f"Error processing time format in estimate_early: {data.estimate_early}")
            else:
                pass
                # print(f"estimate_early is None or empty for row")
            
            # Sum approved_eot
            if data.approved_eot:
                try:
                    time_parts = [int(part) for part in data.approved_eot.split(':')]
                    if len(time_parts) == 3:
                        time_seconds_approved_eot = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
                        total_seconds_approved_eot += time_seconds_approved_eot
                        print(f"Added {time_seconds_approved_eot} seconds from {data.approved_eot}")
                    else:
                        print(f"Invalid time format in approved_eot: {data.approved_eot}")
                except ValueError:
                    print(f"Error processing time format in approved_eot: {data.approved_eot}")
            else:
                pass
                # print(f"approved_eot is None or empty for row")

            # total of late sitting approved 
            if data.approved_ot1:
                try:
                    time_parts3 = [int(parts) for parts in data.approved_ot1.split(':')]
                    if len(time_parts3) == 3:
                        time_seconds_approved_ot1 = time_parts3[0] * 3600 + time_parts3[1] * 60 + time_parts3[2]
                        total_seconds_approved_ot1 += time_seconds_approved_ot1
                    else:
                        print(f"Invalid time format in approved_ot1 : {data.approved_ot1}")
                except ValueError:
                    print(f"Error processing time format in approved_ot1: {data.approved_ot1}")
            else:
                pass
                # print(f"approved_ot1 is None or empty for row")
            
            # total of approved early ot 

            if data.approved_eot:
                try:
                    time_parts4 = [int(parts) for parts in data.approved_eot.split(':')]
                    if len(time_parts4) == 3:
                        time_seconds_approved_eot1 = time_parts4[0] * 3600 + time_parts4[1] * 60 + time_parts4[2]
                        total_seconds_approved_eot += time_seconds_approved_eot
                    else:
                        print(f"Invalid time format in approved_eot : {data.approved_eot}")
                except ValueError:
                    print(f"Error processing time format in approved_eot: {data.approved_eot}")
            else:
                pass
                # print(f"approved_eot is None or empty for row")


        # Calculate total hours after loop
        self.early_ot = "{:.2f}".format(total_seconds1 / 3600.0)
        self.late_sitting = "{:.2f}".format(total_seconds2 / 3600.0)
        self.early_sitting = "{:.2f}".format(total_seconds3 / 3600.0)
        self.approved_early_over_time_hour = "{:.2f}".format(total_seconds_approved_eot / 3600.0)

        # print(f"Total seconds accumulated for approved_eot: {total_seconds_approved_eot}")

        # total of late sitting and early sitting 
        total_sitting = float(self.late_sitting) + float(self.early_sitting)
        self.total_sitting = "{:.2f}".format(total_sitting)

        # total of approved ot1
        self.approved_late_sitting =  "{:.2f}".format(total_seconds_approved_ot1 / 3600.0)

        # total of approved_eot 
        self.approved_early_sitting = "{:.2f}".format(time_seconds_approved_eot1 / 3600.0)

        # approved total sitting
        approved_total_sitting = float(self.approved_late_sitting) + float(self.approved_early_sitting)
        self.approved_total_sitting = approved_total_sitting

        for data in self.table1:
            first_in_time = timedelta(hours=1,minutes=0,seconds=0)
            first_out_time = timedelta(hours=1,minutes=0,seconds=0)
            data.late_sitting = None
            data.additional_hours = None
            data.late_coming_hours = None
            data.early_going_hours = None
            data.early = 0
            data.absent = 0
            # data.weekly_off = 0
            data.total_ot_amount = 0
            tempdate = data.date
            holiday_flag = False
            
            if getdate(data.date) < getdate(frappe.db.get_value("Employee",self.employee,"date_of_joining")):
                data.absent=1
                self.total_absents+=1
                index+=1
                continue
            if frappe.db.get_value("Employee",self.employee,"relieving_date"):
                if getdate(data.date) > getdate(frappe.db.get_value("Employee",self.employee,"relieving_date")):
                    data.absent=1
                    self.total_absents+=1
                    index+=1
                    continue
            
            

            if str(getdate(data.date)) in [str(d.holiday_date) for d in holidays]:
                        holiday_flag = True
                        data.public_holiday = 0
                        data.weekly_off = 0
                        for h in holidays:
                            if str(getdate(data.date)) == str(h.holiday_date):
                                if h.public_holiday == 1:
                                    data.public_holiday = 1
                                    self.total_public_holidays += 1
                                break
                        if data.public_holiday == 0: 
                            # pass
                            # data.weekly_off = 1
                            self.total_weekly_off += 1
                        if hr_settings.absent_sandwich in ['Absent Before Holiday']:
                            if previous and previous.absent == 1:
                                p_date = previous.date
                                lv = frappe.get_all("Leave Application", filters={"from_date":["<=",p_date],"to_date":[">=",p_date],"employee":self.employee,"status":"Approved"},fields=["*"])
                                if len(lv) > 0:
                                    pass
                                else:
                                    data.absent=1
                                    data.absent_due_to_below_threshould = 1
                                    self.total_absents+=1
                                    index+=1
                                    continue
                        elif hr_settings.absent_sandwich in ['Absent Before Or After Holiday']:
                            if previous and previous.absent == 1:
                                p_date = previous.date
                                lv = frappe.get_all("Leave Application", filters={"from_date":["<=",p_date],"to_date":[">=",p_date],"employee":self.employee,"status":"Approved"},fields=["*"])
                                if len(lv) > 0:
                                    pass
                                else:
                                    data.absent=1
                                    # data.absent_due_to_below_threshould = 1
                                    self.total_absents+=1
                                    index+=1
                                    continue
          
            
            if not holiday_flag:
                total_working_days+=1
            LA = frappe.get_all("Leave Application", filters={"from_date":["<=",tempdate],"to_date":[">=",tempdate],"employee":self.employee,"status":"Approved"},fields=["*"])
            if len(LA) > 0:
                leave_flag = True
                if LA[0].half_day:
                    half_day_leave = 1
                

           
            try:
                total_time = None
                hrs = timedelta(hours=0, minutes=0, seconds=0)
                s_type =None
                day_data = None
                if not data.check_in_1 and data.check_out_1:
                    data.check_in_1 = hr_settings.auto_fetch_check_in
                if not data.check_out_1 and data.check_in_1:
                    data.check_out_1 = hr_settings.auto_fetch_check_out
                
                if str(data.check_in_1) == str(hr_settings.auto_fetch_check_in):
                    data.check_in_1 = None
                if str(data.check_out_1) == str(hr_settings.auto_fetch_check_out):
                    data.check_out_1 = None
                
                # if data.check_in_1 != None and data.check_out_1 == None and data.date < today():
                #     data.check_out_1 = timedelta(hours=int(str(data.check_in_1).split(":")[0]),
                #                               minutes=int(str(data.check_in_1).split(":")[1])+1)
             
                if data.approved_ot1:
                    total_approved_ot+= timedelta(hours=int(str(data.approved_ot1).split(":")[0]),minutes=int(str(data.approved_ot1).split(":")[1]))
                if data.check_in_1 and data.check_out_1 and data.check_in_1 != data.check_out_1:
                    first_in_time = timedelta(hours=int(str(data.check_in_1).split(":")[0]),
                                              minutes=int(str(data.check_in_1).split(":")[1]))
                    first_out_time = timedelta(hours=int(str(data.check_out_1).split(":")[0]),
                                              minutes=int(str(data.check_out_1).split(":")[1]))
                   
                    diff = str(first_out_time - first_in_time)
                    if "day" in diff:
                        diff = diff.split("day, ")[1].split(":")
                        diff = timedelta(hours=float(diff[0]), minutes=float(
                            diff[1]), seconds=float(diff[2]))
                    else:
                        diff = first_out_time - first_in_time
                    total_time = total_time + diff if total_time else diff
                   
                if data.check_in_1 and data.check_in_1 != data.check_out_1:
                    shift = None
                    shift_ass = frappe.get_all("Shift Assignment", filters={'employee': self.employee,
                                                                            'start_date': ["<=", getdate(data.date)],'end_date': [">=", getdate(data.date)]}, fields=["*"])
                    if len(shift_ass) > 0:
                        shift = shift_ass[0].shift_type
                    else:
                        shift_ass = frappe.get_all("Shift Assignment", filters={'employee': self.employee,
                                                                            'start_date': ["<=", getdate(data.date)]}, fields=["*"])
                    if len(shift_ass) > 0:
                        shift = shift_ass[0].shift_type
                    if shift == None:
                        frappe.throw(_("No shift available for this employee{0}").format(self.employee))
                    data.shift = shift
                    shift_doc = frappe.get_doc("Shift Type", shift)
                    s_type = shift_doc.shift_type
                    data.absent = 0

                    #  day of week 
                
                    # date1 = data.date
                    # print(f"\n\n\n\\\n\n\n{date1}")
                    # dateobj = getdate(date1)
                    # day_of_week = dateobj.strftime('%A')
                    # data.day = day_of_week
                    print(dateobj)
                   
                    day_name = datetime.strptime(
                        str(data.date), '%Y-%m-%d').strftime('%A')

                    in_diff = first_in_time - shift_doc.start_time
                   
                    day_data = None
                    for day in shift_doc.day:
                        if day_name == day.day:
                            day_data = day
                            break

                    if data.weekly_off == 1 or data.public_holiday == 1:
                        #settings required
                        if total_time:
                            total_holiday_hours += total_time

                            

                    if data.day_type == "Weekly Off":
                        # data.estimated_late = total_time
                        shift1 = None
                        if data.day_type == "Weekly Off":
                            # Fetch the shift assignment
                            shift_ass = frappe.get_all("Shift Assignment", 
                                                        filters={
                                                            'employee': self.employee,
                                                            'start_date': ["<=", data.date],
                                                            'status': 'Active'
                                                        }, 
                                                        fields=['*'])

                            if shift_ass:
                                # Fetch the assigned shift
                                shift1 = frappe.get_all("Shift Type", filters={"name": shift_ass[0].shift_type}, fields=['*'])
                                if shift1:
                                    weekend_slab = shift1[0].custom_slab
                                    overtime_slab = frappe.get_doc("Over Time Slab", weekend_slab)

                                    # Get specific overtime slab details
                                    over_time_slab_doc = frappe.db.sql("""
                                        SELECT 
                                            otc.from_time, otc.to_time, otc.type, otc.formula, otc.per_hour_calculation,
                                            otc.over_time_threshold, otc.fixed_hour, otc.maximum_over_time_limit_in_hours
                                        FROM 
                                            `tabOver Time Slab CT` as otc
                                        WHERE 
                                            otc.parent = %s AND otc.type = %s
                                        """, (weekend_slab, data.day_type), as_dict=True)

                                    if over_time_slab_doc:
                                        # Parse check-in and check-out times
                                        check_in_1 = datetime.strptime(data.check_in_1, "%H:%M:%S").time()
                                        check_out_1 = datetime.strptime(data.check_out_1, "%H:%M:%S").time()
                                        time_difference = datetime.strptime(data.difference1, "%H:%M:%S").time()
                                        time_difference_delta = timedelta(
                                            hours=time_difference.hour, minutes=time_difference.minute, seconds=time_difference.second
                                        )

                                        # Loop through each slab record for overtime calculation
                                        for record in over_time_slab_doc:
                                            if isinstance(record['from_time'], timedelta):
                                                from_time = (datetime.min + record['from_time']).time()
                                            else:
                                                from_time = datetime.strptime(record['from_time'], "%H:%M:%S").time()

                                            if isinstance(record['to_time'], timedelta):
                                                to_time = (datetime.min + record['to_time']).time()
                                            else:   
                                                to_time = datetime.strptime(record['to_time'], "%H:%M:%S").time()
                                            
                                            
                                            # Determine if shift crosses midnight
                                            if from_time <= to_time:  # Standard range
                                                in_time_range = from_time <= check_out_1 <= to_time
                                            else:  # Midnight crossover range
                                                in_time_range = check_out_1 >= from_time or check_out_1 <= to_time

                                            if in_time_range:
                                                # Calculate time difference for overtime
                                                check_in_dt = datetime.combine(datetime.today(), check_in_1)
                                                check_out_dt = datetime.combine(datetime.today(), check_out_1)
                                                actual_work_time = check_out_dt - check_in_dt

                                                # Apply per-hour calculation to get the estimated late time
                                                overtime_seconds = actual_work_time.total_seconds() * record['per_hour_calculation']
                                                overtime_timedelta = timedelta(seconds=overtime_seconds)

                                                # Calculate total overtime including fixed hours
                                                if isinstance(record['fixed_hour'], timedelta):
                                                    fixed_hours = record['fixed_hour']  # Already a timedelta
                                                else:
                                                    fixed_hours = timedelta(hours=record['fixed_hour']) if record['fixed_hour'] else timedelta()

                                                # Calculate total overtime
                                                total_overtime = overtime_timedelta + fixed_hours

                                                # Format total overtime to `HH:MM:SS`
                                                hours, remainder = divmod(int(total_overtime.total_seconds()), 3600)
                                                minutes, seconds = divmod(remainder, 60)
                                                # data.estimated_late = f"{hours:02}:{minutes:02}:{seconds:02}"
                                                break


                                        
                                


                    if not day_data:
                        data.difference = total_time
                        data.difference1 = total_time
                        check_sanwich_after_holiday(self,previous,data,hr_settings,index)
                        previous = data
                        index+=1
                        if data.absent == 0 and data.check_in_1:
                            if holiday_flag:
                                if hr_settings.count_working_on_holiday_in_present_days == 1:
                                    present_days+=1
                                if total_time:
                                    if total_time >= timedelta(hours=hr_settings.holiday_halfday_ot,minutes=00,seconds=0) and \
                                        total_time < timedelta(hours=hr_settings.holiday_full_day_ot,minutes=00,seconds=0):
                                        holiday_halfday_ot = holiday_halfday_ot + 1
                                    elif total_time >= timedelta(hours=hr_settings.holiday_full_day_ot,minutes=00,seconds=0):
                                        holiday_full_day_ot = holiday_full_day_ot + 1
                                    if total_time >= timedelta(hours=hr_settings.double_overtime_after,minutes=0,seconds=0):
                                        data.late_sitting = timedelta(hours=hr_settings.double_overtime_after,minutes=0,seconds=0) + timedelta(hours=hr_settings.double_overtime_after,minutes=0,seconds=0)
                                        total_late_hr_worked += data.late_sitting
                                        #total_holiday_hours += total_time
                                    if (total_time) >= timedelta(hours=hr_settings.threshold_for_additional_hours,minutes=0,seconds=0):
                                            data.additional_hours  =  (total_time) - timedelta(hours=hr_settings.threshold_for_additional_hours,minutes=0,seconds=0)
                                            total_additional_hours = total_additional_hours + data.additional_hours
                                    if data.late_sitting == None:
                                        data.late_sitting = total_time
                                        total_late_hr_worked += data.late_sitting
                            else:
                                present_days+=1
                        
                        continue

                    
                    
                    if day_data.end_time > first_out_time:
                        per_day_h = first_out_time - first_in_time
                    else:
                        per_day_h = day_data.end_time - first_in_time
                    data.per_day_hour = per_day_h
                    if "day" in str(per_day_h):
                        per_day_h = str(per_day_h).split("day, ")[1].split(":")
                        per_day_h = timedelta(hours=float(per_day_h[0]), minutes=float(
                            per_day_h[1]), seconds=float(per_day_h[2]))
                    
                    data.per_day_hour = per_day_h
                    total_per_day_h = total_per_day_h + per_day_h
                    req_working = day_data.end_time - day_data.start_time
                    if "day" in str(req_working):
                        req_working = str(req_working).split("day, ")[1].split(":")
                        req_working = timedelta(hours=float(req_working[0]), minutes=float(
                            req_working[1]), seconds=float(req_working[2]))
                    if half_day_leave:
                        t = (flt(req_working.total_seconds())/3600)/2
                        required_working_hrs= required_working_hrs+t
                    else:
                        required_working_hrs= required_working_hrs+round(
                                            flt(req_working.total_seconds())/3600, 2)
                    half_day_time = day_data.half_day
                    late_mark = day_data.late_mark
                    in_diff = first_in_time - day_data.start_time
                    if not half_day_time:
                        half_day_time = day_data.late_mark
                    if "day" in str(in_diff):
                        in_diff = str(in_diff).split("day, ")[1].split(":")
                        in_diff = timedelta(hours=float(in_diff[0]), minutes=float(
                            in_diff[1]), seconds=float(in_diff[2]))

                    # if first_in_time < day_data.start_time:
                    #     if first_in_time != timedelta(hours=0):
                    #         if day_data.early_overtime_start:
                                # if first_in_time < day_data.early_overtime_start:
                                #     first_in_time = day_data.early_overtime_start
                                # data.early_overtime = day_data.start_time
                                # data.early_overtime = day_data.start_time - first_in_time 
                                # total_early_ot = total_early_ot + (day_data.start_time - first_in_time )
                                # first_in_time = day_data.start_time
                        
                    # if data.late1 == 1:
                    #     data.late = 0
                    # if data.late1 == 1:  # This is the correct way to check for late1 in the child table data
                    #     data.late = 0
                    if first_in_time >= late_mark and first_in_time < half_day_time:
                        data.late = 1
                        if day_data.calculate_late_hours == "Late Mark":
                            data.late_coming_hours = first_in_time - late_mark
                        else:    
                            data.late_coming_hours = first_in_time - day_data.start_time
                    else:
                        data.late = 0
                    if shift_doc.shift_type == "Night":
                        if first_in_time > late_mark:
                            if (first_in_time - late_mark) > timedelta(hours=12,minutes=0,seconds=0):
                                data.late = 0
                            else:
                                data.late = 1
                        elif first_in_time < late_mark:
                            if (late_mark - first_in_time) > timedelta(hours=12,minutes=0,seconds=0):
                                data.late = 1
                            else:
                                data.late = 0

                                

                    if first_in_time >= frappe.db.get_single_value('V HR Settings', 'night_shift_start_time'):
                        self.no_of_nights += 1
                   

                    if first_in_time >= half_day_time and shift_doc.shift_type != "Night":
                        data.half_day = 1
                    else:
                        data.half_day = 0
                    
                    if shift_doc.shift_type == "Night":
                        if first_in_time > half_day_time:
                            if (first_in_time - half_day_time) > timedelta(hours=12,minutes=0,seconds=0):
                                data.half_day = 0
                            else:
                                data.late = 0
                                data.half_day = 1
                        elif first_in_time < half_day_time:
                            if (half_day_time - first_in_time) > timedelta(hours=12,minutes=0,seconds=0):
                                data.half_day = 1
                                data.late = 0
                            else:
                                data.half_day = 0
                    
                    # if data.late1 == 1:  # This is the correct way to check for late1 in the child table data
                    #     data.late = 0
                    
                    
                    if data.check_out_1:
                        out_diff = day_data.end_time - first_out_time
                        if "day" in str(out_diff):
                            out_diff = str(out_diff).split("day, ")[1].split(":")
                            out_diff = timedelta(hours=float(out_diff[0]), minutes=float(
                                out_diff[1]), seconds=float(out_diff[2]))

                        if (out_diff.total_seconds()/60) > 00.00 and (out_diff.total_seconds()/60) <= float(day_data.max_early):
                            if first_out_time < day_data.end_time:
                                data.early = 1
                        elif (out_diff.total_seconds()/60) >= float(day_data.max_early) and (out_diff.total_seconds()/60) < float(day_data.max_half_day):
                            
                            data.half_day = 1
                            data.early = 0
                        elif (out_diff.total_seconds()/60) > 720:
                            tmp  = (out_diff.total_seconds()/60) -720
                            if tmp >= float(day_data.max_early) and tmp < float(day_data.max_half_day) and (total_time < (day_data.end_time - day_data.start_time)):
                                data.half_day = 1
                                data.early = 0 
                        elif (out_diff.total_seconds()/60) > float(day_data.max_half_day) and data.weekly_off==0 and data.public_holiday == 0:
                            if first_out_time < day_data.end_time:
                                data.absent = 1
                        else:
                            data.early = 0
                       
                        out_diff = day_data.over_time_start - first_out_time
                        
                        if "day" in str(out_diff):
                            out_diff = str(out_diff).split("day, ")[1].split(":")
                            out_diff = timedelta(hours=float(out_diff[0]), minutes=float(
                                out_diff[1]), seconds=float(out_diff[2]))
                        
                        ot_start  = day_data.over_time_start if day_data.over_time_start else day_data.end_time
                        if (out_diff.total_seconds()/60) > 720 and first_out_time < ot_start and shift_doc.shift_type!="Night":
                            hrs = timedelta(hours=24, minutes=0,
                                            seconds=0) - out_diff
                            hrs = hrs
                           
                            data.late_sitting = hrs
                        if (out_diff.total_seconds()/60) > 720 and first_out_time > ot_start and shift_doc.shift_type!="Night":
                            hrs = timedelta(hours=24, minutes=0,
                                            seconds=0) - out_diff
                           
                            hrs = hrs
                            data.late_sitting = hrs
                        if first_out_time > ot_start and shift_doc.shift_type == "Night":
                            hrs = timedelta(hours=24, minutes=0,
                                            seconds=0) - out_diff
                            hrs = hrs
                            data.late_sitting = hrs
                        if data.absent == 1 or not data.check_out_1:
                            data.late_sitting = None
                        #setting required
                        if data.late_sitting:
                            new_late_sitting = data.late_sitting
                            if data.late_sitting >= timedelta(hours=hr_settings.double_overtime_after,minutes=0,seconds=0):
                                new_late_sitting = timedelta(hours=hr_settings.double_overtime_after,minutes=0,seconds=0) + timedelta(hours=hr_settings.double_overtime_after,minutes=0,seconds=0)
                            if data.late_sitting >= timedelta(hours=hr_settings.threshold_for_additional_hours,minutes=0,seconds=0):
                                    data.additional_hours  =  data.late_sitting - timedelta(hours=hr_settings.threshold_for_additional_hours,minutes=0,seconds=0)
                                    total_additional_hours = total_additional_hours + data.additional_hours
                            data.late_sitting = new_late_sitting

                        if first_out_time >= timedelta(hours=get_time(hr_settings.night_shift_start_time).hour,minutes=get_time(hr_settings.night_shift_start_time).minute) and holiday_flag:
                            data.holiday_night = 1
                            self.no_of_holiday_night+=1

                else:
                    if data.weekly_off==0 and data.public_holiday == 0:
                        data.absent = 1 
                        data.late = 0
                        data.half_day = 0
                        data.early = 0


                if total_time:
                    total_time_hours = total_time.total_seconds()/3600
                    if total_time_hours >= day_data.minimum_hours_for_present:
                        if day_data.minimum_hours_for_present > 0:
                            data.absent = 0
                            data.half_day = 0
                    elif total_time_hours >= day_data.minimum_hours_for_half_day:
                        if day_data.minimum_hours_for_half_day > 0:
                            data.half_day = 1
                    else:
                        if (day_data.minimum_hours_for_half_day > 0 and day_data.minimum_hours_for_present > 0) \
                             or total_time_hours < day_data.minimum_hours_for_absent :
                            data.absent = 1
                            data.half_day = 0
                            data.early = 0
                            data.late = 0
                if hr_settings.late_and_early_mark:
                    if data.early==1 and data.late == 1:
                        data.half_day = 1
                elif hr_settings.late_mark:
                    if data.late == 1:
                        data.half_day = 1
                elif hr_settings.early_mark:
                    if data.early==1:
                        data.half_day = 1
                if day_data:
                    if day_data.end_time > first_out_time and data.early ==1:
                        data.early_going_hours =  day_data.end_time - first_out_time
                        if day_data.calculate_early_hours == "Exit Grace Period":
                                    data.early_going_hours = data.early_going_hours - timedelta(hours=0,minutes=int(day_data.max_early),seconds=0)
                        #total_early_going_hrs = total_early_going_hrs + data.early_going_hours
                if data.weekly_off==1 or data.public_holiday == 1:
                     data.absent = 0 
                
                if first_in_time:
                    if first_in_time >= timedelta(hours=get_time(hr_settings.night_shift_start_time).hour,minutes=get_time(hr_settings.night_shift_start_time).minute) or s_type == "Night":
                        data.night = 1
                
                # if data.late1 == 1:  # This is the correct way to check for late1 in the child table data
                #         data.late = 0

                if data.early:
                    total_early += 1
                if data.late:
                    total_lates += 1
                    # if data.late_coming_hours:
                    #     total_late_coming_hours = total_late_coming_hours + data.late_coming_hours
                if data.half_day:
                    total_half_days += 1
              
                if data.absent == 1:
                    self.total_absents +=1
                if data.half_day == 1:
                    if data.absent == 1:
                        data.absent = 0
                        self.total_absents -=1
                if data.absent == 0 and data.check_in_1:
                    if holiday_flag:
                        if hr_settings.count_working_on_holiday_in_present_days == 1:
                            present_days+=1
                    else:
                     present_days+=1
                

                if total_time:    
                    total_hr_worked = total_hr_worked + total_time
                    
                
                
                

                # if data.late1 == 1:  # This is the correct way to check for late1 in the child table data
                #         data.late = 0
                if data.late_sitting and data.weekly_off == 0 and data.public_holiday == 0:
                    
                    if day_data.overtime_slabs:
                        OT_slabs = frappe.get_doc("Overtime Slab",day_data.overtime_slabs)
                        prev_hours = None
                        for lb in OT_slabs.hours_slabs:
                            l_hrs = str(lb.actual_hours).split(".")[0]
                            l_mnt = str(lb.actual_hours).split(".")[1]
                            l_mnt  = "."+l_mnt
                            l_mnt = float(l_mnt)*60
                            l_actual_hours = timedelta(hours=int(l_hrs),minutes=int(l_mnt))
                            if data.late_sitting > l_actual_hours:
                                prev_hours = lb.counted_hours
                            elif data.late_sitting == l_actual_hours:
                                prev_hours = lb.counted_hours
                                break
                            else:
                                break
                        if prev_hours:
                            l_hrs = str(prev_hours).split(".")[0]
                            l_mnt = str(prev_hours).split(".")[1]
                            l_mnt  = "."+l_mnt
                            l_mnt = float(l_mnt)*60
                            l_counted_hours = timedelta(hours=int(l_hrs),minutes=int(l_mnt))
                            data.late_sitting = l_counted_hours

                        total_late_hr_worked = total_late_hr_worked + data.late_sitting
                        late_hours = round(
                                    flt((data.late_sitting).total_seconds())/3600, 2)
                       
                        amount = 0
                        for sl in OT_slabs.slabs:
                            if flt(late_hours) <= flt(sl.hours):
                               amount  = sl.amount
                            if flt(sl.hours) > flt(late_hours):
                                break
                            #for case if late sitting hours are greater than all slabs
                            amount  = sl.amount
                            
                        data.total_ot_amount = amount
                        extra_ot_amount+=amount
                    else:
                        total_late_hr_worked = total_late_hr_worked + data.late_sitting

                    data.extra_duty_for_fullday = 0
                    data.extra_duty_for_halfday = 0
                    if (data.late_sitting.total_seconds())/3600 >= hr_settings.working_day_fullday_overtime:
                        data.extra_duty_for_fullday = round((data.late_sitting.total_seconds())/3600,2)
                        self.total_extra_duty_for_fullday +=  data.extra_duty_for_fullday

                    elif (data.late_sitting.total_seconds())/3600 >= hr_settings.working_day_halfday_overtime:
                        data.extra_duty_for_halfday = round((data.late_sitting.total_seconds())/3600,2)
                        self.total_extra_duty_for_halfday += data.extra_duty_for_halfday

                data.difference = total_time  
                if holiday_flag == True and getdate(tempdate) <= getdate(today()):
                    accun_holiday+=1
                if data.extra_absent:
                    self.total_absents+=1
               
                if holiday_flag:
                     self.no_of_sundays+=1
                
                   
                     if total_time:
                                    if total_time >= timedelta(hours=hr_settings.holiday_halfday_ot,minutes=00,seconds=0) and \
                                        total_time < timedelta(hours=hr_settings.holiday_full_day_ot,minutes=00,seconds=0):
                                        holiday_halfday_ot = holiday_halfday_ot + 1
                                    elif total_time >= timedelta(hours=hr_settings.holiday_full_day_ot,minutes=00,seconds=0):
                                        holiday_full_day_ot = holiday_full_day_ot + 1
                                    if total_time >= timedelta(hours=hr_settings.double_overtime_after,minutes=0,seconds=0):
                                        data.late_sitting = timedelta(hours=hr_settings.double_overtime_after,minutes=0,seconds=0) + timedelta(hours=hr_settings.double_overtime_after,minutes=0,seconds=0)
                                        total_late_hr_worked += data.late_sitting
                                        #total_holiday_hours += total_time
                                    if (total_time) >= timedelta(hours=hr_settings.threshold_for_additional_hours,minutes=0,seconds=0):
                                            data.additional_hours  =  (total_time) - timedelta(hours=hr_settings.threshold_for_additional_hours,minutes=0,seconds=0)
                                            total_additional_hours = total_additional_hours + data.additional_hours
                                    if data.late_sitting == None:
                                        data.late_sitting = total_time
                                        total_late_hr_worked += data.late_sitting
                
                

                if data.late1 == 1:  # This is the correct way to check for late1 in the child table data
                        self.late_comparision += 1
                        data.late = 0
                        data.late_coming_hours = None
                        total_lates -= 1
                if data.weekly_off:
                    data.shift_start = None
                    data.shift_end = None
                    data.early_over_time = None
                    # data.approved_ot1 = None
                if data.check_in_1 is None and data.check_out_1 is not None:
                    data.absent = 0
                    
                if data.check_in_1 is not None and data.check_out_1 is None:
                    data.absent = 0
                        
                # if data.weekly_off or data.public_holiday:
                    # If either is True, set weekly_off to 0 and weekday to 0
                #     data.weekly_off = 0
                #     data.weekday = 0
                #     data.public_holiday = 0
                # else:
                #     data.weekday = 1
                    
                # if data.weekly_off == 1:
                #     data.day_type = "Weekly Off"
                # elif data.weekday == 1:
                #     data.day_type = "Weekday"
                # elif data.day_type == "Public Holiday":
                #     data.public_holiday = 1
                

                # if data.public_holiday == 1:
                #     data.day_type = "Public Holiday"
                
                # if data.day_type == "Weekly Off":
                #     data.weekly_off = 1

                employee = frappe.get_doc("Employee", self.employee)
                if employee.custom_late_unmark == 1:
                    #late
                    self.total_lates = 0
                    data.late = 0 
                    # late coming 
                if employee.custom_late_coming_unmark == 1:
                    data.late_coming_hours = None
                    data.short_hours = 0


                shift1 = None

                shift_ass = frappe.get_all("Shift Assignment", 
                                           filters={'employee': self.employee,
                                            'start_date': ["<=", getdate(data.date)],
                                            'status' : 'Active',
                                            # 'start_date': ["<=", '2024-06-01']
                                            }, 
                                            fields=['*'])
                # if data.day == "Monday":
                #     data.early_ot = "90:90:90"
                shift1 = None
            
                if shift_ass:
                    first_shift_ass = shift_ass[0]
                
                    # shift1 = frappe.get_all("Shift Type", filters={"name": shift}, fields=['*'])
                    shift1 = frappe.get_all("Shift Type", filters={"name": shift_ass[0].shift_type}, fields=['*'])
                    if shift1 and len(shift1) > 0:
                        shift_data = shift1[0]
                        # data.early_ot = "90:00:00"
                        child_table_records = frappe.db.sql("""
                        select name, day, start_time, end_time, over_time_slab
                                                            FROM `tabShift Day`
                                                            WHERE parent = %s
                        """,(shift_data['name'],), as_dict=True)
                        
                        

                        
                       
                        
                        if child_table_records and len(child_table_records) > 0:
                            child_table = child_table_records[0]
                            for child_table in child_table_records:
                                if data.day == child_table['day']:
                                    data.shift_in = child_table.start_time
                                    data.shift_out = child_table.end_time
                                    if not child_table.over_time_slab:
                                        continue
                                    
                                    #  calculating difference b/w shift out and check in 
                                    shift_out_str = data.shift_out  # Example: "18:00:00"
                                    check_out_1_str = data.check_out_1  # Example: "19:30:00"
                                    shift_in_str = data.shift_in
                                    check_in_1_str = data.check_in_1
                                    
                                    # difference1 = timedelta()

                                    # Handle the case where `shift_out_str` is a timedelta
                                    if isinstance(shift_out_str, timedelta):
                                        # Convert timedelta to a time string
                                        shift_out_time = (datetime.min + shift_out_str).time()
                                        shift_out_str = shift_out_time.strftime("%H:%M:%S")
                                        
                                    if isinstance(shift_in_str, timedelta):
                                        shift_in_time = (datetime.min + shift_in_str).time()
                                        shift_in_str = shift_in_time.strftime("%H:%M:%S")
                                    
                                    if isinstance(check_in_1_str, timedelta):
                                        check_in_1_time = (datetime.min + check_in_1_str).time()
                                        check_in_1_str = check_in_1_time.strftime("%H:%M:%S")
                                    
                                    if isinstance(check_out_1_str, timedelta):
                                        check_out_1_time = (datetime.min + check_out_1_time).time()
                                        check_out_1_str = check_out_1_time.strftime("%H:%M:%S")
                                    
                                    if data.over_time_type == "Weekly Off":
                                        shift_out_str = data.shift_out  # Example: "18:00:00"
                                        check_out_1_str = data.check_out_1  # Example: "19:30:00"
                                        shift_in_str = data.shift_in
                                        check_in_1_str = data.check_in_1
                                                            
                                        # difference1 = timedelta()

                                        # Handle the case where `shift_out_str` is a timedelta
                                        if isinstance(shift_out_str, timedelta):
                                            # Convert timedelta to a time string
                                            shift_out_time = (datetime.min + shift_out_str).time()
                                            shift_out_str = shift_out_time.strftime("%H:%M:%S")
                                                                
                                        if isinstance(shift_in_str, timedelta):
                                            shift_in_time = (datetime.min + shift_in_str).time()
                                            shift_in_str = shift_in_time.strftime("%H:%M:%S")
                                                            
                                        if isinstance(check_in_1_str, timedelta):
                                            check_in_1_time = (datetime.min + check_in_1_str).time()
                                            check_in_1_str = check_in_1_time.strftime("%H:%M:%S")
                                                            
                                        if isinstance(check_out_1_str, timedelta):
                                            check_out_1_time = (datetime.min + check_out_1_time).time()
                                            check_out_1_str = check_out_1_time.strftime("%H:%M:%S")
                                            

                                        

                                        if isinstance(check_in_1_str, str) and isinstance(check_out_1_str, str):
                                            try:
                                                check_in_1_time = datetime.strptime(check_in_1_str, "%H:%M:%S")
                                                check_out_1_time = datetime.strptime(check_out_1_str, "%H:%M:%S")                   
                                                difference1 = timedelta()
                                                                    
                                                if check_out_1_time < check_in_1_time:
                                                    check_out_1_time += timedelta(days=1)
                                                difference1 = check_out_1_time - check_in_1_time
                                                
                                                total_seconds = int(difference1.total_seconds())
                                                hours = total_seconds // 3600
                                                minutes = (total_seconds % 3600) // 60
                                                seconds = total_seconds % 60
                                                                    
                                                difference_str = f"{hours:02}:{minutes:02}:{seconds:02}"
                                                data.difference1 = "cecking1"  # Assign the formatted difference to the data object
                                                # data.difference1 = difference1
                                            except ValueError as e:
                                                pass
                                       
                                        
                                    # Ensure both are strings and `check_out_1_str` is not None
                                    if isinstance(shift_out_str, str) and isinstance(check_out_1_str, str) and isinstance(shift_in_str, str):
                                        try:
                                            # Convert the string times to datetime objects
                                            shift_out_time = datetime.strptime(shift_out_str, "%H:%M:%S")
                                            check_out_1_time = datetime.strptime(check_out_1_str, "%H:%M:%S")
                                            shift_in_time = datetime.strptime(shift_in_str, "%H:%M:%S")
                                            
                                            difference1 = timedelta()
                                             
                                            if check_out_1_time < shift_out_time and data.over_time_type != "Weekly Off":
                                                check_out_1_time += timedelta(days=1)
                                                difference1 = check_out_1_time - shift_out_time
                                            
                                            if check_out_1_time > shift_out_time:
                                                difference1 = check_out_1_time - shift_out_time
                                            if data.over_time_type == "Weekly Off":
                                                # difference1 = timedelta(hours=10, minutes=10, seconds=10)
                                                difference1 = check_out_1_time - shift_in_time
                                            
                                            # # Get the total difference in seconds and break it down into hours, minutes, and seconds
                                            total_seconds = int(difference1.total_seconds())
                                            hours = total_seconds // 3600
                                            minutes = (total_seconds % 3600) // 60
                                            seconds = total_seconds % 60
                                            
                                            # Format the time difference as HH:MM:SS
                                            difference_str = f"{hours:02}:{minutes:02}:{seconds:02}"
                                            data.difference1 = difference_str  # Assign the formatted difference to the data object
                                            # data.difference1 = difference1
                                        except ValueError as e:
                                            pass
                                    
                                    if isinstance(shift_in_str, str) and isinstance(check_in_1_str, str):
                                        try:
                                            # Parse the time strings into datetime objects
                                            shift_in_time = datetime.strptime(shift_in_str, "%H:%M:%S")
                                            check_in_1_time = datetime.strptime(check_in_1_str, "%H:%M:%S")

                                            # Initialize the time difference
                                            difference1 = timedelta()

                                            # Calculate the difference as CHECK IN - SHIFT IN
                                            if check_in_1_time < shift_in_time:
                                                difference1 = shift_in_time - check_in_1_time
                                            # else:
                                            #     difference1 = None
                                            #     # Optional: If check-in is before the shift, handle that scenario if needed
                                            #     difference1 = shift_in_time - check_in_1_time

                                            # Convert the total difference in seconds and format as HH:MM:SS
                                            if difference1 is not None:
                                                total_seconds = int(difference1.total_seconds())
                                                hours = total_seconds // 3600
                                                minutes = (total_seconds % 3600) // 60
                                                seconds = total_seconds % 60

                                                # Format the time difference as HH:MM:SS
                                                difference_str = f"{hours:02}:{minutes:02}:{seconds:02}"

                                                # Assign the formatted difference to the data object
                                                data.early_difference1 = difference_str

                                        except ValueError as e:
                                            # Handle any value parsing errors here
                                            print(f"Error parsing time strings: {e}")

                                    
                            day_type = data.day_type 

                            over_time_slab_doc = frappe.db.sql("""
                            SELECT 
                                ots.name,
                                otc.from_time,
                                otc.to_time,
                                otc.type,
                                otc.formula,
                                otc.per_hour_calculation,
                                otc.over_time_threshold,
                                otc.fixed_hour
                            FROM 
                                `tabOver Time Slab` as ots
                            LEFT JOIN 
                                `tabOver Time Slab CT` as otc 
                            ON 
                                otc.parent = ots.name
                            WHERE 
                                otc.type = %s 
                        """, (day_type,), as_dict=True)
                            
                            over_time_slab_doc_1 = frappe.db.sql("""
                            SELECT 
                                ots.name,
                                otc.from_time,
                                otc.to_time,
                                otc.type,
                                otc.formula,
                                otc.per_hour_calculation
                            FROM 
                                `tabOver Time Slab` as ots
                            LEFT JOIN 
                                `tabEarly Overtime Slab` as otc 
                            ON 
                                otc.parent = ots.name
                            WHERE 
                                otc.type = %s 
                        """, (day_type,), as_dict=True)

                        
                        # Ensure `check_out_1_str` and `shift_out_str` are not None and are strings
                        # Ensure `shift_out_str` and `check_out_1_str` are strings and handle other types
                        shift_in_str_1 = data.shift_in
                        shift_out_str = data.shift_out
                        check_in_1_str = data.check_in_1
                        check_out_1_str = data.check_out_1


                        

                        # Initialize check_out_1_time and shift_out_time
                        time_difference_delta = timedelta(0)
                        check_out_1_time = None
                        shift_out_time = None
                        check_in_1_time = None
                        shift_in_time_1 = None

                        # Convert to string if they are of type datetime.timedelta
                        if isinstance(shift_out_str, timedelta):
                            shift_out_str = str(shift_out_str)
                        if isinstance(check_out_1_str, timedelta):
                            check_out_1_str = str(check_out_1_str)
                        if isinstance(shift_in_str_1, timedelta):
                            shift_in_str_1 = str(shift_in_str_1)
                        if isinstance(check_in_1_str, timedelta):
                            check_in_1_str = str(check_in_1_str)

                        # Check if the strings are valid
                        if isinstance(shift_out_str, str) and isinstance(check_out_1_str, str) and isinstance(data.difference1, str):
                            try:
                                shift_out_time = datetime.strptime(shift_out_str, "%H:%M:%S").time()
                                check_out_1_time = datetime.strptime(check_out_1_str, "%H:%M:%S").time()
                                time_difference = datetime.strptime(data.difference1, "%H:%M:%S").time()
                                time_difference_delta = timedelta(hours=time_difference.hour, minutes=time_difference.minute, seconds=time_difference.second)
                                
                            except ValueError as e:
                                # print(f"Error parsing time: {e}")
                                pass
                        else:
                            pass
                            # print("Error: shift_out_str or check_out_1_str is not a valid string.")
                        


                        if isinstance(shift_in_str_1, str) and isinstance(check_in_1_str, str) and isinstance(data.early_difference1, str):
                            try:
                                shift_in_time_1 = datetime.strptime(shift_in_str_1, "%H:%M:%S").time()
                                check_in_1_time = datetime.strptime(check_in_1_str, "%H:%M:%S").time()
                                time_difference1 = datetime.strptime(data.early_difference1, "%H:%M:%S")
                                time_difference_delta1 = timedelta(hours=time_difference1.hour, minutes=time_difference1.minute, seconds=time_difference1.second)


                            except ValueError as e:
                                print(f"Error parsing time: {e}")
                        
                        # frappe.log_error(f"Check-out time: {check_out_1_time}, Shift out time: {shift_out_time}, Time difference: {time_difference_delta}")

                        if isinstance(check_out_1_time, datetime):
                            check_out_1_time = check_out_1_time.time()
                        
                        if over_time_slab_doc:
                            for record in over_time_slab_doc:
                                data.over_time_type = record.type
                                data.per_hours_calculation = record.per_hour_calculation
                                data.over_time_amount = record.formula
                                threshould = record.over_time_threshold
                                required_hours = record.required_hours
                                max_limit_ot = record.maximum_over_time_limit_in_hours

                                if isinstance(record.from_time, timedelta):
                                    record.from_time = (datetime.min + record.from_time).time()

                                if isinstance(record.to_time, timedelta):
                                    record.to_time = (datetime.min + record.to_time).time()

                                if data.shift_out is not None:
                                    if isinstance(data.shift_out, str):
                                        shift_time = datetime.strptime(data.shift_out, "%H:%M:%S").time()
                                    elif isinstance(data.shift_out, timedelta):
                                        shift_time = (datetime.min + data.shift_out).time()
                                
                                if data.shift_in is not None:
                                    if isinstance(data.shift_in, str):
                                        shift_in_time = datetime.strptime(data.shift_in, "%H:%M:%S").time()
                                    elif isinstance(data.shift_in, timedelta):
                                        shift_in_time = (datetime.min + data.shift_in).time()

                                if required_hours is not None:
                                    if isinstance(required_hours, str):
                                        # Convert to timedelta if stored as a time string in 'hh:mm:ss' format
                                        hours, minutes, seconds = map(int, required_hours.split(':'))
                                        required_hours = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                                    elif type(required_hours) is time:
                                        # Convert `time` to `timedelta`
                                        required_hours = timedelta(hours=required_hours.hour, minutes=required_hours.minute, seconds=required_hours.second)
                                    elif type(required_hours) is timedelta:
                                        required_hours = required_hours  # Already a timedelta
                                    else:
                                        raise ValueError("Unsupported type for required_hours")
                                

                                if check_out_1_time is not None:
                                    # print(f"Type of check_out_1_time: {type(check_out_1_time)}")
                                    # frappe.log_error(f"Type of check_out_1_time: {type(check_out_1_time)}")
                                    # Convert check_out_1_time to datetime or time if it's not already
                                    if isinstance(check_out_1_time, str):
                                        # Try to parse if it's a string (assuming hh:mm:ss format)
                                        check_out_1_time = datetime.strptime(check_out_1_time, '%H:%M:%S').time()
                                    elif isinstance(check_out_1_time, datetime):
                                        # If it's a datetime object, convert it to a time object
                                        check_out_1_time = check_out_1_time.time()
                                    elif isinstance(check_out_1_time, timedelta):
                                        # Convert timedelta to time
                                        check_out_1_time = (datetime.min + check_out_1_time).time()

                                if data.total_time is not None and data.total_time != '':
                                    if isinstance(data.total_time, str):
                                        # Convert to timedelta if stored as a time string in 'hh:mm:ss' format
                                        hours, minutes, seconds = map(int, data.total_time.split(':'))
                                        total_time1 = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                                    elif isinstance(data.total_time, time):
                                        # Convert `time` to `timedelta`
                                        total_time1 = timedelta(hours=data.total_time.hour, minutes=data.total_time.minute, seconds=data.total_time.second)
                                    elif isinstance(data.total_time, timedelta):
                                        total_time1 = data.total_time  # Already a timedelta
                                    else:
                                        raise ValueError("Unsupported type for total_time")
                                    

                                    # if isinstance(check_out_1_time, time):   
                                    if record.type == "Weekday" and check_out_1_time and shift_time and shift_in_time:
                                            # if check_out_1_time < shift_time and check_out_1_time > shift_in_time:
                                            #         data.early = 1
                                            #         # Convert both times to datetime objects to calculate the difference
                                            #         check_out_datetime = datetime.combine(datetime.today(), check_out_1_time)
                                            #         shift_datetime = datetime.combine(datetime.today(), shift_time)
                                            #         shift_in_datetime = datetime.combine(datetime.today(), shift_in_time)
                                                    
                                            #         # Calculate the early going hours as a timedelta
                                            #         early_going_timedelta = shift_datetime - check_out_datetime
                                                    
                                            #         # Store the result as hours, minutes, and seconds in early_going_hours
                                            #         data.early_going_hours = str(early_going_timedelta)
                                            # else:
                                            #     data.early_going_hours = ""
                                            #     data.early = 0
                                            #     data.estimated_late = "1"


                                    

                                            

                                            if record.from_time > record.to_time:
                                                # Shift crosses midnight
                                                # check_out_1_time = check_out_1_time.time()
                                                if check_out_1_time >= record.from_time or check_out_1_time <= record.to_time:
                                                    if isinstance(threshould, timedelta):
                                                        threshold_timedelta = threshould
                                                        # data.estimated_late = "2"
                                                    else:
                                                        threshold_timedelta = timedelta(hours=float(threshould))
                                                        # data.estimated_late = "2"

                                                    # data.estimated_late = "difference_str1"
                                                    
                                                    # log_message = (f"Date: {data.date}, Difference: {time_difference_delta}, "
                                                    # f"Threshold: {threshold_timedelta}")

                                                    # Log with a short title
                                                    # Use the first argument for the log message and specify the title keyword argument correctly.
                                                    # frappe.log_error(message=log_message[:140], title=str(data.date))

                                                    if time_difference_delta >= threshold_timedelta:
                                                        # frappe.log_error(f"Time difference: {time_difference_delta} exceeds threshold: {threshold_timedelta}")
                                                        data.late_threshold = threshould
                                                        data.data = record.otc_name

                                                        # Convert fixed_hour (time) to timedelta
                                                        # frappe.log_error(f"Type of fixed_hour: {type(record.fixed_hour)}")

                                                        # Ensure record.fixed_hour is not None and is a valid timedelta object
                                                        if record.fixed_hour is not None:
                                                            # Check if fixed_hour is a timedelta object
                                                            if isinstance(record.fixed_hour, timedelta):
                                                                fixed_hour_timedelta = record.fixed_hour  # Use it directly as it's already timedelta
                                                                # frappe.log_error(f"Fixed hour timedelta used directly: {fixed_hour_timedelta}")
                                                            else:
                                                                # frappe.log_error(f"fixed_hour is not a timedelta object, defaulting to 0")
                                                                fixed_hour_timedelta = timedelta(0)  # Default to 0 if it's not a timedelta
                                                        else:
                                                            pass
                                                            # frappe.log_error(f"fixed_hour is None, defaulting to 0")
                                                            fixed_hour_timedelta = timedelta(0)  # Default to 0 if None

                                                        # Calculate total time difference in seconds and apply per hour calculation
                                                        time_difference_multiplied = (time_difference_delta.total_seconds() * record.per_hour_calculation)

                                                        # Convert the result to a timedelta and add fixed_hour
                                                        time_difference_result = timedelta(seconds=time_difference_multiplied) + fixed_hour_timedelta
                                                        # frappe.log_error(f"{fixed_hour_timedelta}{time_difference_multiplied}")

                                                        # Convert back to total seconds for formatting
                                                        time_delta_difference = int(time_difference_result.total_seconds())
                                                        hours = time_delta_difference // 3600
                                                        minutes = (time_delta_difference % 3600) // 60
                                                        seconds = time_delta_difference % 60
                                                        
                                                        overtime_round_off = hr_settings.overtime_round_off
                                                        if data.difference1 != "00:00:00":
                                                            if overtime_round_off == 1:
                                                                if minutes >= 30:
                                                                    minutes = 30
                                                                else: 
                                                                    minutes = 00
                                                                if seconds >= 30:
                                                                    seconds = 00
                                                                else:
                                                                    seconds = 00

                                                        # Format the result as a string in hh:mm:ss format
                                                        difference_str1 = f"{hours}:{minutes:02}:{seconds:02}"
                                                        # data.estimated_late = difference_str1

                                                        # frappe.log_error(f"Calculated Estimated Late: {difference_str1}")
                                                        # log_message = (
                                                        #     f"{data.date} "
                                                        #     f"Fixed Hour: {fixed_hour_timedelta.total_seconds() / 3600:.2f} hours, "
                                                        #     f"Total Hours (Before Calculation): {time_difference_delta.total_seconds() / 3600:.2f} hours, "
                                                        #     f"Estimated Late Calculation: {data.estimated_late}"
                                                        # )

                                                        # Log the combined message
                                                        # frappe.log_error(log_message)
                                                # elif check_out_1_time >= record.to_time:
                                                #     data.estimated_late = "difference_str1"

                                            # elif check_out_1_time > record.from_time:
                                            #         data.estimated_late = "str1"
                                            else:
                                                pass
                                            
                                                # data.estimated_late = "str1"
                                                
                                                if isinstance(check_out_1_time, datetime):
                                                    check_out_1_time = check_out_1_time.time()
                                                # check_out_1_time = check_out_1_time.time()
                                                # Handle the case where the shift does not cross midnight
                                                if check_out_1_time >= record.from_time and check_out_1_time <= record.to_time:
                                                    if threshould is None:
                                                        threshold_timedelta = timedelta(hours=0)  # Default to zero hours if None
                                                    elif isinstance(threshould, timedelta):
                                                        threshold_timedelta = threshould  # Already a timedelta, no need to convert
                                                        # data.estimated_late = "str2"
                                                    else:
                                                        threshold_timedelta = timedelta(hours=float(threshould))
                                                        # data.estimated_late = "str3"



                                                    if isinstance(threshould, timedelta):
                                                        # Convert timedelta to total hours
                                                        threshold_hours = threshould.total_seconds() / 3600
                                                        threshold_timedelta = timedelta(hours=threshold_hours)
                                                        # data.estimated_late = "str4"
                                                    elif isinstance(threshould, (int, float, str)) and threshould != '':
                                                        # Convert string/int/float to timedelta
                                                        threshold_timedelta = timedelta(hours=float(threshould))
                                                        # data.estimated_late = "str5"
                                                    else:
                                                        # Handle None or invalid values
                                                        threshold_timedelta = timedelta(hours=0)
                                                        # data.estimated_late = "str6"

                                                    # if threshould is not None:
                                                    #     threshold_timedelta = timedelta(hours=threshould)
                                                    # else:
                                                    #     threshold_timedelta = timedelta(0)
                                                    
                                                    

                                                    if time_difference_delta >= threshold_timedelta:
                                                        # Store OTC name
                                                        data.data = record.otc_name
                                                        # data.estimated_late = "str7"

                                                        # Handle fixed hour logic dynamically
                                                        # frappe.log_error(f"Value of fixed_hour: {record.fixed_hour} (Type: {type(record.fixed_hour)})")

                                                        # Ensure fixed_hour is not None and is a valid value
                                                        if record.fixed_hour is not None:
                                                            # Check if fixed_hour is a timedelta object
                                                            if isinstance(record.fixed_hour, timedelta):
                                                                # data.estimated_late = "str9"
                                                                fixed_hour_timedelta = record.fixed_hour  # Use it directly as it's already timedelta
                                                                # frappe.log_error(f"Fixed hour timedelta used directly: {fixed_hour_timedelta}")
                                                            else:
                                                                # frappe.log_error(f"fixed_hour is not a timedelta object, defaulting to 0")
                                                                fixed_hour_timedelta = timedelta(0)
                                                                # data.estimated_late = "stf1"
                                                                # Default to 0 if it's not a timedelta
                                                        else:
                                                            pass
                                                            # frappe.log_error(f"fixed_hour is None, defaulting to 0")
                                                            fixed_hour_timedelta = timedelta(0)
                                                            # data.estimated_late = "stf2"


                                                        # Evaluate per hour calculation
                                                        if isinstance(record.per_hour_calculation, str):
                                                            eval_expression = record.per_hour_calculation.replace('time_difference_delta', str(time_difference_delta.total_seconds() / 3600))
                                                            try:
                                                                time_difference_multiplied = eval(eval_expression)
                                                            except Exception as e:
                                                                # frappe.log_error(f"Error evaluating formula: {e}")
                                                                time_difference_multiplied = 0.0
                                                        else:
                                                            time_difference_multiplied = time_difference_delta.total_seconds() / 3600 * record.per_hour_calculation

                                                        # Convert total_hours back to timedelta
                                                        final_timedelta = timedelta(hours=time_difference_multiplied) + fixed_hour_timedelta

                                                        # Calculate hours, minutes, and seconds
                                                        time_delta_difference = int(final_timedelta.total_seconds())
                                                        hours = time_delta_difference // 3600
                                                        minutes = (time_delta_difference % 3600) // 60
                                                        seconds = time_delta_difference % 60

                                                        # if hours >= max_limit_ot:
                                                        #     hours = max_limit_ot
                                                        #     minutes = 00
                                                        #     seconds = 00
                                                        # elif hours == max_limit_ot:
                                                        #     hours = max_limit_ot
                                                        #     minutes = 00
                                                        #     seconds = 00
                                                        # else:
                                                        #     hours
                                                        #     minutes
                                                        #     seconds


                                                        overtime_round_off = hr_settings.overtime_round_off
                                                        if data.difference1 != "00:00:00":
                                                            if overtime_round_off == 1:
                                                                if minutes >= 30:
                                                                    minutes = 30
                                                                else: 
                                                                    minutes = 00
                                                                if seconds >= 30:
                                                                    seconds = 30
                                                                else:
                                                                    seconds = 00

                                                        # if total_time1 > required_hours:
                                                        difference_str1 = f"{hours}:{minutes:02}:{seconds:02}"
                                                        # data.estimated_late = difference_str1

                                                        # Format the time as hh:mm:ss
                                                        # difference_str1 = f"{hours:02}:{minutes:02}:{seconds:02}"
                                                        # data.estimated_late = difference_str1
                                                        
                                                        # Combined log message
                                                        # log_message = (
                                                        #     f"{data.date} "
                                                        #     f"Fixed Hour: {fixed_hour_timedelta.total_seconds() / 3600:.2f} hours, "
                                                        #     f"Total Hours (Before Calculation): {time_difference_delta.total_seconds() / 3600:.2f} hours, "
                                                        #     f"Estimated Late Calculation: {data.estimated_late}"
                                                        # )
                                                    else:
                                                        pass
                                                        # data.estimated_late = threshold_timedelta
                                    else:
                                        pass


                                    # if data.day_type == "Weekly Off":
                                    #     shift_out_str = data.shift_out  # Example: "18:00:00"
                                    #     check_out_1_str = data.check_out_1  # Example: "19:30:00"
                                    #     shift_in_str = data.shift_in
                                    #     check_in_1_str = data.check_in_1
                                                            
                                    #     # difference1 = timedelta()

                                    #     # Handle the case where `shift_out_str` is a timedelta
                                    #     if isinstance(shift_out_str, timedelta):
                                    #         # Convert timedelta to a time string
                                    #         shift_out_time = (datetime.min + shift_out_str).time()
                                    #         shift_out_str = shift_out_time.strftime("%H:%M:%S")
                                                                
                                    #     if isinstance(shift_in_str, timedelta):
                                    #         shift_in_time = (datetime.min + shift_in_str).time()
                                    #         shift_in_str = shift_in_time.strftime("%H:%M:%S")
                                                            
                                    #     if isinstance(check_in_1_str, timedelta):
                                    #         check_in_1_time = (datetime.min + check_in_1_str).time()
                                    #         check_in_1_str = check_in_1_time.strftime("%H:%M:%S")
                                                            
                                    #     if isinstance(check_out_1_str, timedelta):
                                    #         check_out_1_time = (datetime.min + check_out_1_time).time()
                                    #         check_out_1_str = check_out_1_time.strftime("%H:%M:%S")

                                    #     if isinstance(check_in_1_str, str) and isinstance(check_out_1_str, str):
                                    #         try:
                                    #             check_in_1_time = datetime.strptime(check_in_1_str, "%H:%M:%S")
                                    #             check_out_1_time = datetime.strptime(check_out_1_str, "%H:%M:%S")                   
                                    #             difference1 = timedelta()
                                                                    
                                    #             if check_out_1_time < check_in_1_time:
                                    #                 check_out_1_time += timedelta(days=1)
                                    #             difference1 = check_out_1_time - check_in_1_time
                                                
                                    #             total_seconds = int(difference1.total_seconds())
                                    #             hours = total_seconds // 3600
                                    #             minutes = (total_seconds % 3600) // 60
                                    #             seconds = total_seconds % 60
                                                                    
                                    #             difference_str = f"{hours:02}:{minutes:02}:{seconds:02}"
                                    #             data.difference1 = difference_str  # Assign the formatted difference to the data object
                                    #             # data.difference1 = difference1
                                    #         except ValueError as e:
                                    #             pass


                                        # day_type = data.day_type 

                                                

                                        # over_time_slab_doc = frappe.db.sql("""
                                        #         SELECT 
                                        #             ots.name,
                                        #             otc.name as otc_name,
                                        #             otc.type,
                                        #             otc.from_time,
                                        #             otc.to_time,
                                        #             otc.type,
                                        #             otc.formula,
                                        #             otc.per_hour_calculation,
                                        #             otc.over_time_threshold,
                                        #             otc.fixed_hour
                                        #         FROM 
                                        #             `tabOver Time Slab` as ots
                                        #         LEFT JOIN 
                                        #             `tabOver Time Slab CT` as otc 
                                        #         ON 
                                        #             otc.parent = ots.name
                                        #         WHERE 
                                        #             otc.type = %s 
                                        #     """, (day_type,), as_dict=True)
                                                
                                        # over_time_slab_doc_1 = frappe.db.sql("""
                                        #         SELECT 
                                        #             ots.name,
                                        #             otc.from_time,
                                        #             otc.to_time,
                                        #             otc.type,
                                        #             otc.formula,
                                        #             otc.per_hour_calculation,
                                        #             otc.per_hour_calculation
                                        #         FROM 
                                        #             `tabOver Time Slab` as ots
                                        #         LEFT JOIN 
                                        #             `tabEarly Overtime Slab` as otc 
                                        #         ON 
                                        #             otc.parent = ots.name
                                        #         WHERE 
                                        #             otc.type = %s 
                                        #     """, (day_type,), as_dict=True)

                                            
                                        #     # Ensure `check_out_1_str` and `shift_out_str` are not None and are strings
                                        #     # Ensure `shift_out_str` and `check_out_1_str` are strings and handle other types
                                        # shift_in_str_1 = data.shift_in
                                        # shift_out_str = data.shift_out
                                        # check_in_1_str = data.check_in_1
                                        # check_out_1_str = data.check_out_1
                                            


                                            

                                        #     # Initialize check_out_1_time and shift_out_time
                                        # time_difference_delta = timedelta(0)
                                        # check_out_1_time = None
                                        # shift_out_time = None
                                        # check_in_1_time = None
                                        # shift_in_time_1 = None

                                        # # Convert to string if they are of type datetime.timedelta
                                        # if isinstance(shift_out_str, timedelta):
                                        #     shift_out_str = str(shift_out_str)
                                        # if isinstance(check_out_1_str, timedelta):
                                        #     check_out_1_str = str(check_out_1_str)
                                        # if isinstance(shift_in_str_1, timedelta):
                                        #     shift_in_str_1 = str(shift_in_str_1)
                                        # if isinstance(check_in_1_str, timedelta):
                                        #     check_in_1_str = str(check_in_1_str)

                                        # # Check if the strings are valid
                                        # if isinstance(check_out_1_str, str) and isinstance(data.difference1, str):
                                        #     try:
                                        #         # shift_out_time = datetime.strptime(shift_out_str, "%H:%M:%S").time()
                                        #         check_out_1_time = datetime.strptime(check_out_1_str, "%H:%M:%S").time()
                                        #         time_difference = datetime.strptime(data.difference1, "%H:%M:%S").time()
                                        #         time_difference_delta = timedelta(hours=time_difference.hour, minutes=time_difference.minute, seconds=time_difference.second)
                                                
                                        #     except ValueError as e:
                                        #         print(f"Error parsing time: {e}")
                                        # else:
                                        #     print("Error: shift_out_str or check_out_1_str is not a valid string.")
                                            
                                        # if isinstance(check_in_1_str, str):
                                        #     try:
                                            
                                        #         check_in_1_time = datetime.strptime(check_in_1_str, "%H:%M:%S").time()

                                        #     except ValueError as e:
                                        #         print(f"Error parsing time: {e}")

                                        # if isinstance(check_in_1_str, str) and isinstance(data.early_difference1, str):
                                        #     try:
                                        #         # shift_in_time_1 = datetime.strptime(shift_in_str_1, "%H:%M:%S").time()
                                        #         check_in_1_time = datetime.strptime(check_in_1_str, "%H:%M:%S").time()
                                        #         time_difference1 = datetime.strptime(data.early_difference1, "%H:%M:%S")
                                        #         time_difference_delta1 = timedelta(hours=time_difference1.hour, minutes=time_difference1.minute, seconds=time_difference1.second)

                                        #     except ValueError as e:
                                        #         print(f"Error parsing time: {e}")
                                        
                                        # # frappe.log_error(f"Check-out time: {check_out_1_time}, Shift out time: {shift_out_time}, Time difference: {time_difference_delta}")

                                        
                                        
                                        # if over_time_slab_doc:
                                        #     for record in over_time_slab_doc:
                                        #         data.over_time_type = record.type
                                        #         data.per_hours_calculation = record.per_hour_calculation
                                        #         data.over_time_amount = record.formula
                                        #         threshould = record.over_time_threshold
                                        #         data.late_threshold = threshould

                                        #         if record.get('fixed_hour') is not None:
                                        #             data.fixed_hours = record['fixed_hour']
                                        #         else:
                                        #             data.fixed_hours = record.fixed_hour
                                        #         # data.fixed_hours = record.fixed_hour

                                        #         if isinstance(record.from_time, timedelta):
                                        #             record.from_time = (datetime.min + record.from_time).time()

                                        #         if isinstance(record.to_time, timedelta):
                                        #             record.to_time = (datetime.min + record.to_time).time()

                                        #         # frappe.log_error('checking456')
                                        #         if data.check_out_1 is not None:
                                        #             # if record.type == data.day_type:
                                        #             # frappe.log_error(f"{data.date} {data.day_type}")
                                        #             if data.day_type == "Weekly Off":

                                        #                 if record.from_time < record.to_time:
                                                            
                                        #                     # Shift crosses midnight
                                        #                     # data.estimated_late = "difference_str2"
                                        #                     # frappe.log_error('Condition met:') # this is working
                            
                                        #                     # frappe.log_error(f"data{data.date}checkout{data.check_out_1}checkout_time{check_out_1_time}record.from_time{record.from_time}record.to_time{record.to_time}")
                                        #                     if check_out_1_time is not None and check_in_1_time is not None:
                                        #                         # Log the initial condition
                                        #                         # frappe.log_error('Condition: All times are not None', 'Timing Validation')
                                        #                         # frappe.log_error(f"{check_out_1_time}{record.from_time}{record.to_time}")

                                        #                         # Check if checkout time is within the range
                                        #                         # if check_in_1_time >= record.from_time and check_out_1_time <= record.to_time:
                                        #                         if check_out_1_time >= record.from_time and check_out_1_time <= record.to_time:
                                        #                             placeholder_date = data.date

                                        #                         # Convert time to datetime objects
                                        #                             check_out_1_datetime = datetime.combine(placeholder_date, check_out_1_time)
                                        #                             from_time_datetime = datetime.combine(placeholder_date, record.from_time)
                                        #                             to_time_datetime = datetime.combine(placeholder_date, record.to_time)

                                        #                             # Now, perform the comparison and subtraction
                                        #                             if from_time_datetime <= check_out_1_datetime <= to_time_datetime:
                                        #                                 # Subtract datetime objects to get a timedelta
                                        #                                 test = check_out_1_datetime - from_time_datetime
                                        #                                 if isinstance(threshould, timedelta):
                                        #                                 # If threshould is already a timedelta, you can use it directly
                                        #                                     threshold_timedelta = threshould
                                        #                                 elif isinstance(threshould, (float, int)):
                                        #                                     # Create a threshold timedelta from float/int hours
                                        #                                     threshold_timedelta = timedelta(hours=threshould)
                                        #                                 else:
                                        #                                     frappe.log_error(f"Invalid threshould value: {threshould}", 'Timing Validation')
                                        #                                     threshold_timedelta = timedelta(0)

                                        #                                 if record.fixed_hour is not None:
                                        #                                     # Check if fixed_hour is a timedelta object
                                        #                                     if isinstance(record.fixed_hour, timedelta):
                                        #                                         fixed_hour_timedelta = record.fixed_hour
                                        #                                         # frappe.log_error(f"Fixed hour timedelta used directly: {fixed_hour_timedelta}", 'Timing Calculation')
                                        #                                     else:
                                        #                                         # If it's not a timedelta, default to 0
                                        #                                         fixed_hour_timedelta = timedelta(0)
                                        #                                         # frappe.log_error("fixed_hour is not a timedelta object, defaulting to 0", 'Timing Calculation')
                                        #                                 else:
                                        #                                     fixed_hour_timedelta = timedelta(0)

                                                                        
                                        #                                 time_difference_delta = timedelta(hours=1)  # Placeholder: replace with actual time difference calculation
                                        #                                 time_difference_multiplied = test.total_seconds() * record.per_hour_calculation
                                        #                                 # frappe.log_error(f"time_difference_delta    {time_difference_delta}")
                                                                        

                                        #                                 # # Convert the result to a timedelta and add fixed_hour
                                        #                                 time_difference_result = timedelta(seconds=time_difference_multiplied) + fixed_hour_timedelta

                                        #                                 # # Log the calculated time difference
                                        #                                 # # frappe.log_error(f"Calculated time difference result: {time_difference_result}", 'Timing Calculation')

                                        #                                 # # Convert back to total seconds for formatting
                                        #                                 time_delta_difference = int(time_difference_result.total_seconds())
                                        #                                 hours = time_delta_difference // 3600
                                        #                                 minutes = (time_delta_difference % 3600) // 60
                                        #                                 seconds = time_delta_difference % 60

                                        #                                 # # Format the result as a string in hh:mm:ss format
                                        #                                 difference_str1 = f"{hours}:{minutes:02}:{seconds:02}"

                                                                            

                                        #                                 data.estimated_late = difference_str1


                                                

                                        #     else:
                                        #         pass
                                        #         # frappe.log_error('Condition not met: check_out_1_time not within range', 'Timing Validation')
                                        # else:
                                        #     pass
                                          
                                    # else:
                                    #     # Handle the case where the shift does not cross midnight
                                    #     # frappe.log_error('Condition:') # this is working 
                                    #     if check_out_1_time is not None and record.from_time is not None and record.to_time is not None and check_in_1_time is not None:
                                    #         # frappe.log_error('Condition1')
                                    #         # if check_in_1_time >= record.from_time and check_out_1_time <= record.to_time:
                                    #         if check_out_1_time >= record.from_time and check_out_1_time <= record.to_time:
                                    #             # frappe.log_error('Condition metty:')
                                    #             # frappe.log_error(f"thresoulh{threshould}")
                                    #             # data.data = "909090"
                                    #             data.late_threshould = threshould

                                    #             if isinstance(threshould, timedelta):
                                    #                 # Convert to total hours
                                    #                 threshold_hours = threshould.total_seconds() / 3600
                                    #                 threshold_timedelta = timedelta(hours=threshold_hours)
                                    #             else:
                                    #                 threshold_timedelta = timedelta(hours=float(threshould))

                                                # if threshould is not None:
                                                #     threshold_timedelta = timedelta(hours=threshould)
                                                # else:
                                                #     threshold_timedelta = timedelta(0)
                                                
                                                

                                                # if time_difference_delta >= threshold_timedelta:
                                                #     # Store OTC name
                                                #     data.data = record.otc_name

                                                #     # Handle fixed hour logic dynamically
                                                #     # frappe.log_error(f"Value of fixed_hour: {record.fixed_hour} (Type: {type(record.fixed_hour)})")

                                                #     # Ensure fixed_hour is not None and is a valid value
                                                #     if record.fixed_hour is not None:
                                                #         # Check if fixed_hour is a timedelta object
                                                #         if isinstance(record.fixed_hour, timedelta):
                                                #             fixed_hour_timedelta = record.fixed_hour  # Use it directly as it's already timedelta
                                                #             # frappe.log_error(f"Fixed hour timedelta used directly: {fixed_hour_timedelta}")
                                                #         else:
                                                #             # frappe.log_error(f"fixed_hour is not a timedelta object, defaulting to 0")
                                                #             fixed_hour_timedelta = timedelta(0)  # Default to 0 if it's not a timedelta
                                                #     else:
                                                #         pass
                                                #         # frappe.log_error(f"fixed_hour is None, defaulting to 0")
                                                #         fixed_hour_timedelta = timedelta(0)


                                                #     # Evaluate per hour calculation
                                                #     if isinstance(record.per_hour_calculation, str):
                                                #         eval_expression = record.per_hour_calculation.replace('time_difference_delta', str(time_difference_delta.total_seconds() / 3600))
                                                #         try:
                                                #             time_difference_multiplied = eval(eval_expression)
                                                #         except Exception as e:
                                                #             # frappe.log_error(f"Error evaluating formula: {e}")
                                                #             time_difference_multiplied = 0.0
                                                #     else:
                                                #         time_difference_multiplied = time_difference_delta.total_seconds() / 3600 * record.per_hour_calculation

                                                #     # Convert total_hours back to timedelta
                                                #     final_timedelta = timedelta(hours=time_difference_multiplied) + fixed_hour_timedelta
                                                #     # frappe.log_error(f"final_timedelta{final_timedelta}")

                                                #     # Calculate hours, minutes, and seconds
                                                #     time_delta_difference = int(final_timedelta.total_seconds())
                                                #     hours = time_delta_difference // 3600
                                                #     minutes = (time_delta_difference % 3600) // 60
                                                #     seconds = time_delta_difference % 60

                                                #     # Format the time as hh:mm:ss
                                                #     difference_str1 = f"{hours:02}:{minutes:02}:{seconds:02}"
                                                #     data.estimated_late = difference_str1
                                                    # frappe.log_error(f"else final estimate{difference_str1}")
                                                    
                                                    # Combined log message
                                                    # log_message = (
                                                    #     f"{data.date} "
                                                    #     f"Fixed Hour: {fixed_hour_timedelta.total_seconds() / 3600:.2f} hours, "
                                                    #     f"Total Hours (Before Calculation): {time_difference_delta.total_seconds() / 3600:.2f} hours, "
                                                    #     f"Estimated Late Calculation: {data.estimated_late}"
                                                    # )
                                # else:
                                #     pass

                                    
                                    
                                    
                                                
                                        
                                # frappe.log_error(f"Estimated Late: {data.date} - {data.estimated_late}")
                        if over_time_slab_doc_1:
                            for record_1 in over_time_slab_doc_1:
                                data.over_time_type1 = record_1.type
                                data.early_per_hours_calculation = record_1.per_hour_calculation
                                data.early_over_time_amount = record_1.formula
                                threshould1 = record_1.over_time_threshold

                                if isinstance(record_1.from_time, timedelta):
                                    record_1.from_time = (datetime.min + record_1.from_time).time()

                                if isinstance(record_1.to_time, timedelta):
                                    record_1.to_time = (datetime.min + record_1.to_time).time()
                            
                                if data.check_in_1:
                                    if record_1.from_time < record_1.to_time:
                                        if isinstance(check_in_1_time, datetime):
                                            check_in_1_time = check_in_1_time.time()  # Convert to time
                                        # Shift crosses midnight
                                        if check_in_1_time < record_1.to_time:
                                            if threshould is not None:
                                                # Convert threshould from float (hours) to timedelta
                                                if isinstance(threshould, float):
                                                    threshold_timedelta = timedelta(hours=threshould)
                                                elif isinstance(threshould, timedelta):
                                                    threshold_timedelta = threshould
                                                # else:
                                                #     raise ValueError("threshould must be a float or a timedelta")

                                                
                                                if time_difference_delta1 > threshold_timedelta:
                                                    time_difference_multiplied = time_difference_delta1 * record_1.per_hour_calculation
                                                    time_difference_result = time_difference_multiplied.total_seconds()

                                                    final_timedelta = timedelta(seconds=time_difference_result)
                                                    time_delta_difference = int(final_timedelta.total_seconds())
                                                    hours = time_delta_difference // 3600
                                                    minutes = (time_delta_difference % 3600) // 60
                                                    seconds = time_delta_difference % 60
                                                    difference_str1 = f"{hours}:{minutes}:{seconds}"

                                                    # Store the estimated early time in your data object
                                                    data.estimate_early = final_timedelta

                                                    # You can also log the difference if needed
                                                    print(f"Estimated Early Time: {difference_str1}")
                                        else:
                                            if data.over_time_type == "Weekly Off":
                                                if time_difference_delta1 > threshould:
                                                    time_difference_multiplied = time_difference_delta1 * record_1.per_hour_calculation
                                                    time_difference_result = time_difference_multiplied.total_seconds()
                                                    final_timedelta = timedelta(seconds=time_difference_result)
                                                    time_delta_difference = int(final_timedelta.total_seconds())
                                                    hours = time_delta_difference // 3600
                                                    minutes = (time_delta_difference % 3600) // 60
                                                    seconds = time_delta_difference % 60
                                                    difference_str1 = f"{hours}:{minutes}:{seconds}"
                                                    data.estimate_early = difference_str1
                                                    
                                    else:
                                        pass
                                        # Shift crosses midnight
                                        # if check_in_1_time >= record_1.from_time or check_in_1_time <= record_1.to_time:
                                        #     if time_difference_delta1 < threshould:
                                        #         time_difference_multiplied = time_difference_delta1 * record_1.per_hour_calculation
                                        #         time_difference_result = time_difference_multiplied.total_seconds()
                                        #         final_timedelta = timedelta(seconds=time_difference_result)
                                        #         time_delta_difference = int(final_timedelta.total_seconds())
                                        #         hours = time_delta_difference // 3600
                                        #         minutes = (time_delta_difference % 3600) // 60
                                        #         seconds = time_delta_difference % 60
                                        #         difference_str1 = f"{hours}:{minutes}:{seconds}"
                                        #         data.estimate_early = "09:09:09"

                    
                        def time_to_seconds(time_string):
                            """Helper function to convert time string to seconds."""
                            if time_string is None:
                                raise ValueError("Time string is None")
                            t = datetime.strptime(time_string, "%H:%M:%S").time()
                            return t.hour * 3600 + t.minute * 60 + t.second

                        def get_time_difference(t1, t2):
                            """Calculate time difference in seconds between two time strings."""
                            t1_seconds = time_to_seconds(t1)
                            t2_seconds = time_to_seconds(t2)
                            return timedelta(seconds=t1_seconds - t2_seconds)

                        # Retrieve and verify data values
                        shift_in = data.shift_in
                        check_in_1 = data.check_in_1

                        # Print statements for debugging
                        # print(f"shift_in: {shift_in}")
                        # print(f"check_in_1: {check_in_1}")

                        # Convert shift_in and check_in_1 to time strings if they are timedelta
                        if isinstance(shift_in, timedelta):
                            total_seconds = int(shift_in.total_seconds())
                            hours, remainder = divmod(total_seconds, 3600)
                            minutes, seconds = divmod(remainder, 60)
                            shift_in_time_string = f"{hours:02}:{minutes:02}:{seconds:02}"
                        else:
                            shift_in_time_string = shift_in

                        if isinstance(check_in_1, timedelta):
                            total_seconds = int(check_in_1.total_seconds())
                            hours, remainder = divmod(total_seconds, 3600)
                            minutes, seconds = divmod(remainder, 60)
                            check_in_1_time_string = f"{hours:02}:{minutes:02}:{seconds:02}"
                        else:
                            check_in_1_time_string = check_in_1

                        # Ensure both time strings are not None
                        if not shift_in_time_string or not check_in_1_time_string:
                            data.early_ot = None
                        else:
                            
                        # elif shift_in_time_string is not None and check_in_1_time_string is not None or shift_in_time_string is "" or check_in_1_time_string is "":
                            # Convert time strings to datetime objects for comparison
                            shift_in_datetime = datetime.strptime(shift_in_time_string, "%H:%M:%S")
                            check_in_1_datetime = datetime.strptime(check_in_1_time_string, "%H:%M:%S")


                            # Calculate time difference if check_in_1 is earlier than shift_in
                            if check_in_1_datetime < shift_in_datetime:
                                time_difference = get_time_difference(shift_in_time_string, check_in_1_time_string)
                                data.early_ot = time_difference
                            else:
                                data.early_ot = None
                        
                        if data.late_sitting:
                            late_sitting_timedelta = data.late_sitting
                            # late_sitting_timedelta = timedelta(hours=data.late_sitting.hour, minutes=data.late_sitting.minutes, seconds= data.late_sitting.seconds)
                        else:
                            late_sitting_timedelta = timedelta(0)
                        
                        if data.early_ot:
                            if isinstance(data.early_ot, str):
                                early_ot_hours, early_ot_minutes, early_ot_seconds = map(int, data.early_ot.split(':'))
                                early_ot_timedelta = timedelta(hours=early_ot_hours,minutes=early_ot_minutes,seconds=early_ot_seconds)
                            else:
                                early_ot_timedelta = data.early_ot

                        else:
                            early_ot_timedelta = timedelta(0)
                        
                        total_ot_time_delta = late_sitting_timedelta + early_ot_timedelta

                        total_seconds = total_ot_time_delta.total_seconds()
                        hours, remainder = divmod(total_seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        data.total_ot_hours = "{:02}:{:02}:{:02}".format(int(hours),int(minutes),int(seconds))

                        if data.approved_ot1:
                            approved_ot1_hours, approved_ot1_minutes, approved_ot1_seconds = map(int, data.approved_ot1.split(':'))

                            # approved_ot1_hours, approved_ot1_minutes, approved_ot1_seconds = map(int, data.approved_ot1(':'))
                            approved_ot1_timedelta = timedelta(hours=approved_ot1_hours, minutes=approved_ot1_minutes, seconds=approved_ot1_seconds)
                            # approved_eot_timedelta = data.total_approved_ot
                            # data.total_approved_ot = approved_ot1_seconds
                        else:
                            approved_ot1_timedelta = timedelta(0) 
                        
                        if data.approved_eot:
                            approved_eot_hours, approved_eot_minutes, approved_eot_seconds = map(int, data.approved_eot.split(':'))
                            approved_eot_timedelta = timedelta(hours=approved_eot_hours, minutes=approved_eot_minutes, seconds=approved_eot_seconds)
                            # data.total_approved_ot = approved_eot_timedelta 
                        else:
                            approved_eot_timedelta = timedelta(0)
                        
                        total_approved_ot_data = approved_ot1_timedelta + approved_eot_timedelta

                        total_seconds = total_approved_ot_data.total_seconds()
                        hours, remainder = divmod(total_seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        data.total_approved_ot = "{:02}:{:02}:{:02}".format(int(hours),int(minutes),int(seconds))

                        if self.late_sitting_hours is None:
                            self.late_sitting_hours = 0.0
                        else:
                            self.late_sitting_hours = float(self.late_sitting_hours)

                        late_sitting_hours_float = float(self.late_sitting_hours)

                        # set total overtime in employee attendance   
                        if self.early_ot is None:
                            self.early_ot = 0.0
                        else:
                            self.early_ot = float(self.early_ot)

                        early_ot_float = float(self.early_ot)

                        # else:
                        #     raise ValueError("No Shift Found")    
                        
                        if data.late_sitting:
                            late_sitting_timedelta = data.late_sitting
                            # late_sitting_timedelta = timedelta(hours=data.late_sitting.hour, minutes=data.late_sitting.minutes, seconds= data.late_sitting.seconds)
                        else:
                            late_sitting_timedelta = timedelta(0)

                        # remove lates if in employee profile it is marked
                        
                        
                        # if data.early_ot:
                        #     early_ot_timedelta = data.early_ot
                            # if isinstance(data.early_ot, str):
                            #     early_ot_hours, early_ot_minutes, early_ot_seconds = map(int, data.early_ot.split(':'))
                            #     early_ot_timedelta = timedelta(hours=early_ot_hours,minutes=early_ot_minutes,seconds=early_ot_seconds)
                            # else:
                            #     early_ot_timedelta = data.early_ot

                        # else:
                        #     early_ot_timedelta = timedelta(0)
                        
                        # total_ot_time_delta = late_sitting_timedelta + early_ot_timedelta

                        # total_seconds = total_ot_time_delta.total_seconds()
                        # hours, remainder = divmod(total_seconds, 3600)
                        # minutes, seconds = divmod(remainder, 60)
                        # data.total_ot_hours = "{:02}:{:02}:{:02}".format(int(hours),int(minutes),int(seconds))
                        # set total overtime 
                        if self.late_sitting_hours:
                            self.total_overtime = self.late_sitting_hours
                        else:
                            self.total_overtime = 0
                        if self.early_ot:
                            self.total_overtime = self.early_ot
                        else:
                            self.total_overtime = 0
                        if self.late_sitting_hours and self.early_ot:
                            self.total_overtime = self.early_ot + self.late_sitting_hours

                        # set approved overtime le

                        if self.approved_ot:
                            self.approved_overtime_le = float(self.approved_ot)
                        else:
                            self.approved_overtime_le = 0
                        if self.approved_early_over_time_hour:
                            self.approved_overtime_le = float(self.approved_early_over_time_hour)
                        else:
                            self.approved_early_over_time_hour = 0
                        if self.approved_ot and self.approved_early_over_time_hour:
                            approved_overtime_le = float(self.approved_ot) + float(self.approved_early_over_time_hour)
                            self.approved_overtime_le = "{:.2f}".format(approved_overtime_le)

                        else:
                            self.approved_overtime_le = 0
                
                else:
                    pass
                    # raise ValueError(f"No Shift Found for these employee: {self.employee}")
                
                
                

                # if data.check_in_1:

                    # late_sitting_time = data.late_sitting if data.late_sitting else timedelta(0)
                    # early_over_time = data.early_over_time if data.early_over_time else timedelta(0)    

                    # total_ot_time_delta = late_sitting_time + early_over_time

                    # total_seconds = total_ot_time_delta.total_seconds()

                    # hours, remainder = divmod(total_seconds, 3600)
                    # minutes, seconds = divmod(remainder, 60)
                    # data.total_ot_hours = "{:02}:{:02}:{:02}".format(int(hours),int(minutes), int(seconds))
                    # pass
                    # late_sitting_time = datetime.strptime(data.late_sitting)
                    # early_over_time = datetime.strptime(data.early_over_time)
                    # total_ot_delta = (late_sitting_time - datetime(1900,1,1)) + (early_over_time - datetime(1900,1,1))
                    # data.total_ot_hours = str(total_ot_delta)
                    # if '.' in data.total_ot_hours:
                    #     data.total_ot_hours = data.total_ot_hours.split('.')[0]
                    
                    # print(data.total_ot_hours)

                # if data.late_sitting:
                #     data.total_ot_hours
                # if data.early_over_time:
                #     data.total_ot_hours
                # if data.late_sitting and data.early_over_time:
                #     data.total_ot_hours = data.late_sitting + data.early_over_time                

                
                # if data.check_in_1:
                #     time_format = "%H:%M:%S"
                    
                #     # Parse the strings into datetime objects
                #     check_in_1_time = datetime.strptime(data.check_in_1, time_format)
                #     shift_in_time = datetime.strptime(data.shift_in, time_format)
                    
                #     # Calculate the difference
                #     early_ot_timedelta = shift_in_time - check_in_1_time
                    
                #     # Convert the difference back to hh:mm:ss format
                #     early_ot_time = str(early_ot_timedelta)
                    
                #     # If the timedelta includes days, remove them
                #     if len(early_ot_time) > 8:
                #         early_ot_time = early_ot_time[-8:]
                        
                #     data.early_ot = early_ot_time

                # if data.check_in_1:
                #     time_format = "%H:%M:%S"
                #     check_in_1_time = datetime.strptime(data.check_in_1, time_format)
                #     shift_in_time = datetime.strptime(data.shift_in, time_format)
                #     early_ot_timedelta = shift_in_time - check_in_1_time
                #     early_ot_time = str(early_ot_timedelta)
                #     data.early_ot = early_ot_time

                # if data.check_in_1 == None:
                #     data.approved_early_over_time = "00:00:00"
                # if data.check_in_1:
                #     data.approved_early_over_time = "00:00:00"
                #     # data.early_over_time = data.check_in_1 - start_time_formatted
                #     check_in_datetime = datetime.strptime(data.check_in_1, '%H:%M:%S')
                #     check_in_time = check_in_datetime.time()
                #     check_in_time_delta = timedelta(hours=check_in_time.hour, minutes=check_in_time.minute, seconds=check_in_time.second)
                #     shift_start_time = data.shift_start
                #     shift_start_time_delta = timedelta(hours=shift_start_time.hour, minutes=shift_start_time.minute, seconds=shift_start_time.second)
                #     if check_in_time_delta < shift_start_time_delta:
                #         result_delta = shift_start_time_delta - check_in_time_delta
                #         result_time = (datetime.min + result_delta).time()
                #         data.early_over_time = result_time

                #     else:
                #         data.early_over_time = None
                    
                    # result_delta = check_in_time_delta - shift_start_time_delta
                    # result_time = (datetime.min + result_delta).time()
                    # data.early_over_time = result_time
                    # data.check = result_time

                

                if day_data and not holiday_flag:
                    if day_data.late_slab and data.late_coming_hours:
                        lsm = frappe.get_doc("Late Slab", day_data.late_slab)
                        if data.late_coming_hours > timedelta(hours=0,minutes=int(lsm.late_slab_minutes)):
                            data.late_coming_hours = data.late_coming_hours - timedelta(hours=0,minutes=int(lsm.late_slab_minutes))
                            prev_hours = None
                            for lb in lsm.late_details:
                                l_hrs = str(lb.actual_hours).split(".")[0]
                                l_mnt = str(lb.actual_hours).split(".")[1]
                                l_mnt  = "."+l_mnt
                                l_mnt = float(l_mnt)*60
                                l_actual_hours = timedelta(hours=int(l_hrs),minutes=int(l_mnt))
                                
                                if data.late_coming_hours > l_actual_hours:
                                    prev_hours = lb.counted_hours
                                elif data.late_coming_hours == l_actual_hours:
                                    prev_hours = lb.counted_hours
                                    break
                                else:
                                    break
                            if prev_hours:
                                l_hrs = str(prev_hours).split(".")[0]
                                l_mnt = str(prev_hours).split(".")[1]
                                l_mnt  = "."+l_mnt
                                l_mnt = float(l_mnt)*60
                                l_counted_hours = timedelta(hours=int(l_hrs),minutes=int(l_mnt))
                                data.late_coming_hours = l_counted_hours
                            total_late_coming_hours = total_late_coming_hours + data.late_coming_hours
                    else:
                        if data.late_coming_hours:
                            total_late_coming_hours = total_late_coming_hours + data.late_coming_hours



                    # if day_data.early_slab and data.early_going_hours:
                    #     esm = frappe.get_doc("Early Slab", day_data.early_slab)
                    #     if data.early_going_hours > timedelta(hours=0,minutes=int(esm.early_slab_minutes)):
                    #         data.early_going_hours = data.early_going_hours - timedelta(hours=0,minutes=int(esm.early_slab_minutes))
                    #         prev_hours = None
                    #         for lb in esm.early_details:
                    #             l_hrs = str(lb.actual_hours).split(".")[0]
                    #             l_mnt = str(lb.actual_hours).split(".")[1]
                    #             l_mnt  = "."+l_mnt
                    #             l_mnt = float(l_mnt)*60
                    #             l_actual_hours = timedelta(hours=int(l_hrs),minutes=int(l_mnt))
                    #             if data.early_going_hours > l_actual_hours:
                    #                 prev_hours = lb.counted_hours
                    #             elif data.early_going_hours == l_actual_hours:
                    #                 prev_hours = lb.counted_hours
                    #                 break
                    #             else:
                    #                 break
                    #         if prev_hours:
                    #             l_hrs = str(prev_hours).split(".")[0]
                    #             l_mnt = str(prev_hours).split(".")[1]
                    #             l_mnt  = "."+l_mnt
                    #             l_mnt = float(l_mnt)*60
                    #             l_counted_hours = timedelta(hours=int(l_hrs),minutes=int(l_mnt))
                    #             data.early_going_hours = l_counted_hours
                    #         total_early_going_hrs = total_early_going_hrs + data.early_going_hours
                    # else:
                    #     if data.early_going_hours:
                    #         total_early_going_hrs = total_early_going_hrs + data.early_going_hours
                    if day_data.early_slab and data.early_going_hours:
                        esm = frappe.get_doc("Early Slab", day_data.early_slab)
                        if data.early_going_hours > timedelta(hours=0, minutes=int(esm.early_slab_minutes)):
                            data.early_going_hours -= timedelta(hours=0, minutes=int(esm.early_slab_minutes))
                            prev_hours = None
                            for lb in esm.early_details:
                                l_hrs = str(lb.actual_hours).split(".")[0]
                                l_mnt = str(lb.actual_hours).split(".")[1]
                                l_mnt = "." + l_mnt
                                l_mnt = float(l_mnt) * 60
                                l_actual_hours = timedelta(hours=int(l_hrs), minutes=int(l_mnt))
                                
                                if data.early_going_hours > l_actual_hours:
                                    prev_hours = lb.counted_hours
                                elif data.early_going_hours == l_actual_hours:
                                    prev_hours = lb.counted_hours
                                    break
                                else:
                                    break

                            if prev_hours:
                                l_hrs = str(prev_hours).split(".")[0]
                                l_mnt = str(prev_hours).split(".")[1]
                                l_mnt = "." + l_mnt
                                l_mnt = float(l_mnt) * 60
                                l_counted_hours = timedelta(hours=int(l_hrs), minutes=int(l_mnt))
                                data.early_going_hours = l_counted_hours
                        
                        # Ensure data.early_going_hours is a timedelta before adding
                        if isinstance(data.early_going_hours, str):
                            # Convert to timedelta from string format
                            h, m, s = map(int, data.early_going_hours.split(':'))
                            data.early_going_hours = timedelta(hours=h, minutes=m, seconds=s)
                            
                        total_early_going_hrs += data.early_going_hours
                    else:
                        if data.early_going_hours:
                            # Ensure data.early_going_hours is a timedelta
                            if isinstance(data.early_going_hours, str):
                                # Convert to timedelta from string format
                                h, m, s = map(int, data.early_going_hours.split(':'))
                                data.early_going_hours = timedelta(hours=h, minutes=m, seconds=s)
                            
                            total_early_going_hrs += data.early_going_hours

                # Store total early going hours in the parent doctype
                self.total_early_going_hours = str(total_early_going_hrs)
                    
                
                if holiday_flag:
                    if data.early_going_hours and total_early_going_hrs!= timedelta(hours=0, minutes=0, seconds=0):
                            total_early_going_hrs = total_early_going_hrs - data.early_going_hours
                            data.early_going_hours = None
                    if data.late_coming_hours and total_late_coming_hours != timedelta(hours=0, minutes=0, seconds=0):
                            total_late_coming_hours = total_late_coming_hours - data.late_coming_hours
                            data.late_coming_hours = None

                    if data.early:
                        total_early -= 1
                        data.early = 0
                    if data.late1 == 1:  
                        total_lates -= 1
                    if data.late:
                        total_lates -= 1
                        data.late = 0
                
                # if data.check_out_1 is None:
                #     log = frappe.get_all(
                #         'Attendance Logs',
                #         filters={'attendance_date': "2024-08-31", 'type': 'Check Out'},  # Ensure correct date format
                #         fields=['attendance_time']
                #     )
                    
                #     if log:  # Check if log is not empty
                #         data.check_out_1 = log[0].attendance_time

                # if data.check_out_1 is None or data.check_out_1 is not None or data.check_in_1 is not None:
                    
                #     formatted_date = frappe.utils.formatdate(data.check_in_1, "yyyy-mm-dd")
                    
                #     log = frappe.db.sql("""
                #         SELECT attendance_time 
                #         FROM `tabAttendance Logs`
                #         WHERE attendance_date = %s
                #         AND `type` = 'Check Out'
                #     """, (formatted_date,))  # Ensure the date format is 'YYYY-MM-DD'


                #     if log:  # Check if log is not empty
                #         data.check_out_1 = log[0][0]  # Since frappe.db.sql returns a list of tuples
                
                
                check_sanwich_after_holiday(self,previous,data,hr_settings,index)
               
                previous = data
                index+=1

                half_day_leave = False
                holiday_flag = False
               
            except:
                frappe.log_error(frappe.get_traceback(),"Attendance")
                previous = data
             

        self.hours_worked = round(
            flt((total_hr_worked-total_late_hr_worked).total_seconds())/3600, 2)
        self.late_sitting_hours = round(
            flt(total_late_hr_worked.total_seconds())/3600, 2)
        self.holiday_halfday_ot = holiday_halfday_ot
        self.holiday_full_day_ot = holiday_full_day_ot
        self.over_time = self.late_sitting_hours
        # self.difference = round(
        #     (flt(self.hours_worked)-flt(required_working_hrs)), 2)
        if self.over_time >= 1:
            self.over_time = round(self.over_time)
        else:
            self.over_time = 0.0
        self.difference = round(
            flt(total_late_coming_hours.total_seconds())/3600, 2)
        self.approved_ot = round(
            flt(total_approved_ot.total_seconds())/3600, 2)
        
        self.extra_hours = round(
            flt(total_additional_hours.total_seconds())/3600, 2)
        self.extra_ot_amount = extra_ot_amount
        self.total_lates = total_lates
        self.total_early_goings = total_early
        self.total_half_days = total_half_days
        self.total_early_going_hours = total_early_going_hrs
        self.holiday_hour = round(flt(total_holiday_hours.total_seconds())/3600, 2)
        self.early_over_time = round(flt(total_early_ot.total_seconds())/3600, 2)
        t_lat = 0
        t_earl = 0
        if hr_settings.maximum_lates_for_absent > 0:
            t_lat = int(total_lates/hr_settings.maximum_lates_for_absent) if total_lates >= hr_settings.maximum_lates_for_absent else 0
        self.lates_for_absent = t_lat

        if hr_settings.maximum_early_for_absent > 0:
            t_earl = int(total_early/hr_settings.maximum_early_for_absent) if total_early >= hr_settings.maximum_early_for_absent else 0
        self.early_for_absents = t_earl
       
        self.short_hours = self.difference
       
        self.total_working_hours = round(required_working_hrs,2)
        self.total_difference_hours = round(self.total_working_hours - self.hours_worked,2)
        self.late_plus_early_hours_ = total_late_coming_hours + self.total_early_going_hours
        self.present_days = present_days 
        lfh = 0
        if hr_settings.maximum_lates_for_halfday > 0:
            lfh = int(total_lates/hr_settings.maximum_lates_for_halfday) if total_lates >= hr_settings.maximum_lates_for_halfday else 0
        self.lates_for_halfday = round(lfh/2,1)

        efh = 0
        if hr_settings.maximum_early_for_halfday > 0:
            efh = int(total_early/hr_settings.maximum_early_for_halfday) if total_early >= hr_settings.maximum_early_for_halfday else 0
        self.early_for_halfday = round(efh/2,1)
        self.total_early_going_hours = round(flt(total_early_going_hrs.total_seconds())/3600, 2)

        employee = frappe.get_doc("Employee", self.employee)
        if employee.custom_late_unmark == 1:
            self.manual_absent = 0
                                
            self.total_lates = 0
            data.late = 0 
        else:
            pass
            # frappe.log_error(f"Total Lates for {self.employee}: {self.total_lates}", 'Late Attendance Calculation')

    def get_month_no(self, month):
        dict_={
            "January":1,
            "February":2,
            "March":3,
            "April":4,
            "May":5,
            "June":6,
            "July":7,
            "August":8,
            "September":9,
            "October":10,
            "November":11,
            "December":12
        }
        return dict_[month]
    

                

def check_sanwich_after_holiday(self, previous,data,hr_settings,index):
    ab_index = []
    ab_index_process = False
    if data.absent == 1:
        for num in reversed(range(index)) :
            if self.table1[num].weekly_off ==1 or self.table1[num].public_holiday==1:
                ab_index.append(num)
            else:
                if hr_settings.absent_sandwich == 'Absent After Holiday':
                    ab_index_process = True
                    break
                elif hr_settings.absent_sandwich == 'Absent Before and After Holiday' and self.table1[num].absent == 1:
                        ab_index_process = True
                        break
                elif hr_settings.absent_sandwich == 'Absent Before Or After Holiday':
                        ab_index_process = True
                        break
                break
            
            
    
    if ab_index_process == True:
        for ind in ab_index:
                if self.table1[ind].absent != 1:
                    self.table1[ind].absent = 1
                    self.table1[ind].absent_due_to_below_threshould = 1
                    
                    self.no_of_sundays-=1
                    if self.table1[ind].difference:
                        if self.table1[ind].difference >= timedelta(hours=hr_settings.holiday_halfday_ot,minutes=00,seconds=0) and \
                            self.table1[ind].difference < timedelta(hours=hr_settings.holiday_full_day_ot,minutes=00,seconds=0):
                           self.holiday_halfday_ot = self.holiday_halfday_ot - 1
                        elif self.table1[ind].difference >= timedelta(hours=hr_settings.holiday_full_day_ot,minutes=00,seconds=0):
                            if self.holiday_full_day_ot and self.holiday_full_day_ot != "":
                                self.holiday_full_day_ot = float(self.holiday_full_day_ot or 0) - 1
                    self.total_absents += 1



def get_holidays_for_employee(
	employee, start_date, end_date, raise_exception=True, only_non_weekly=False
):
	"""Get Holidays for a given employee

	`employee` (str)
	`start_date` (str or datetime)
	`end_date` (str or datetime)
	`raise_exception` (bool)
	`only_non_weekly` (bool)

	return: list of dicts with `holiday_date` and `description`
	"""
	holiday_list = get_holiday_list_for_employee(employee, raise_exception=raise_exception)

	if not holiday_list:
		return []

	filters = {"parent": holiday_list, "holiday_date": ("between", [start_date, end_date])}

	if only_non_weekly:
		filters["weekly_off"] = False

	holidays = frappe.get_all("Holiday", fields=["description","public_holiday", "weekly_off","holiday_date"], filters=filters)

	return holidays

