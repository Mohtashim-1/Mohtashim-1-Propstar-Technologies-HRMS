from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from datetime import datetime, timedelta
import datetime as special
from frappe.utils import fmt_money

def execute(filters=None):
    columns, data = [], []
    columns = get_column()
    data = get_data(filters, columns)
    return columns, data

def get_column():
    column = [
        _("S No") + "::80",
        _("Emp Id") + "::80",
        _("Name") + "::180",
        _("Designation") + "::150",
        _("Total Month Days") + "::100",
        _("Present Days") + "::100",
        _("Half Days") + "::100",
        _("Absents") + "::100",
        _("Total Late") + "::100",
        _("Salary") + "::100",
        _("Gross") + "::100",
        _("OT Days") + "::100",
        _("OT Amount") + "::100",
        _("Total Income") + "::100",
        _("Tax") + "::100",
        _("Late") + "::100",
        _("Absent") + "::100",
        _("Early") + "::100",
        # _("E.O.B.I Ded.") + "::100",
        _("Total Ded") + "::100",
        _("Net Payable") + "::100",
        _("Receiver Signature") + "::100"
    ]
    return column

def get_data(filters, columns):
    cond = {}
    if filters.month:
        cond["month"] = filters.month
    if filters.year:
        cond["year"] = filters.year
    if filters.employee:
        cond["employee"] = filters.employee
    if filters.department:
        cond["department"] = filters.department

    salary_slips = frappe.get_all("Salary Slip", filters=cond, fields=["*"])
    grouped_data = {}
    serial_no = 1  

    for sp in salary_slips:
        doc = frappe.get_doc("Salary Slip", sp.name)

        if doc.department not in grouped_data:
            grouped_data[doc.department] = []

        overtime = 0.0
        tax = 0.0
        abse = 0.0
        early = 0.0
        late = 0.0
        gross = 0.0

        for ern in doc.earnings:
            if "Overtime".lower() in ern.salary_component.lower():
                overtime += ern.amount
            if "Gross Salary".lower() in ern.salary_component.lower():
                gross += ern.amount

        for ern in doc.deductions:
            if "Tax".lower() in ern.salary_component.lower():
                tax = ern.amount
            elif "Absent".lower() in ern.salary_component.lower():
                abse += ern.amount
            elif "Late".lower() in ern.salary_component.lower():
                late = ern.amount
            elif "Early".lower() in ern.salary_component.lower():
                early = ern.amount

        row = [
            serial_no,
            doc.biometric_id or "",  
            doc.employee_name or "",  
            doc.designation or "",  
            doc.custom_total_month_days or 0,
            doc.custom_present or 0,
            doc.custom_half_day or 0,
            doc.custom_absents or 0,
            doc.custom_total_late or 0,
            int(doc.basic_salary) if doc.basic_salary else 0, 
            int(gross) if gross else 0,  
            int(doc.custom_weekend_days),
            int(overtime),
            int(doc.gross_pay) if doc.gross_pay else 0,  
            int(tax),
            int(late),
            int(abse),
            int(early),
            # int(doc.eobi_deduction) if hasattr(doc, 'eobi_deduction') else 0, 
            int(doc.total_deduction) if doc.total_deduction else 0,  
            int(doc.rounded_total) if doc.rounded_total else 0,  
            ""
        ]

        # Ensure row length matches column count
        while len(row) < len(columns):
            row.append("")
        while len(row) > len(columns):
            row = row[:len(columns)]  

        grouped_data[doc.department].append(row)
        serial_no += 1  

    data = []
    for department, rows in grouped_data.items():
        department_row = [""] * len(columns)
        department_row[2] = f"<b>{department}</b>"
        data.append(department_row)

        total_gross_salary = 0
        total_ot_hours = 0
        total_ot_amount = 0
        total_income = 0
        total_tax = 0
        total_late = 0
        total_early = 0
        total_eobi = 0
        total_ded = 0
        total_net_payable = 0
        total_month_days = 0
        total_present = 0
        total_half_day = 0
        total_absents = 0
        total_late_hours = 0
        total_gross= 0
        total_abse = 0

        for row in rows:
            data.append(row)

            total_month_days += row[4]
            total_present += row[5]
            total_half_day += row[6]
            total_absents += row[7]
            total_late_hours += row[8]
            total_gross_salary += row[9]
            total_gross += row[10] 
            total_ot_hours += row[11]
            total_ot_amount += row[12]
            total_income += row[13]
            total_tax += row[14]
            total_late += row[15]
            total_early += row[16]
            total_abse += row[17]
            # total_eobi += row[16]
            total_ded += row[18]
            total_net_payable += row[19]

        totals_row = [
            "<b>Total</b>",  
            "", "", "",  
            f"<b>{total_month_days}</b>",
            f"<b>{total_present}</b>",
            f"<b>{total_half_day}</b>",
            f"<b>{total_absents}</b>",
            f"<b>{total_late_hours}</b>",
            f"<b>{total_gross}</b>", 
            f"<b>{total_gross_salary}</b>",  
            f"<b>{total_ot_hours}</b>",  
            f"<b>{total_ot_amount}</b>",  
            f"<b>{total_income}</b>",  
            f"<b>{total_tax}</b>",  
            f"<b>{total_late}</b>",  
            f"<b>{total_early}</b>",  
            f"<b>{total_abse}</b>",  
            f"<b>{total_ded}</b>",  
            f"<b>{total_net_payable}</b>",  
            ""
        ]
        
        data.append(totals_row)

    return data  
