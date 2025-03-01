from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import fmt_money

def execute(filters=None):
    columns = get_column()
    data = get_data(filters, columns)
    return columns, data

def get_column():
    return [
        _("S No") + "::80",
        _("Emp Id") + "::80",
        _("Name") + "::180",
        _("Designation") + "::150",
        _("Total Month Days") + "::100",
        _("Paid Days") + "::100",
        _("Half Days") + "::100",
        _("Absents") + "::100",
        _("Total Late") + "::100",
        _("OT Hours") + "::100",
        _("OT Days") + "::100",
        _("OT Amount") + "::100",
        _("Salary") + "::100",
        
        # _("Total Income") + "::100",
        _("Tax") + "::100",
        _("Late") + "::100",
        _("Absent") + "::100",
        _("Early") + "::100",
        _("Total Earn") + "::100",
        _("Total Ded") + "::100",
        _("Net Payable") + "::100",
        _("Receiver Signature") + "::100"
    ]

def get_data(filters, columns):
    cond = {}
    if filters.get("month"):
        cond["month"] = filters["month"]
    if filters.get("year"):
        cond["year"] = filters["year"]
    if filters.get("employee"):
        cond["employee"] = filters["employee"]
    if filters.get("department"):
        cond["department"] = filters["department"]

    salary_slips = frappe.get_all("Salary Slip", filters=cond, fields=["*"])
    grouped_data = {}
    serial_no = 1  

    for sp in salary_slips:
        doc = frappe.get_doc("Salary Slip", sp.name)

        if doc.department not in grouped_data:
            grouped_data[doc.department] = []

        overtime = sum(ern.amount for ern in doc.earnings if "overtime" in ern.salary_component.lower())
        tax = sum(ern.amount for ern in doc.deductions if "tax" in ern.salary_component.lower())
        abse = sum(ern.amount for ern in doc.deductions if "absent" in ern.salary_component.lower())
        late = sum(ern.amount for ern in doc.deductions if "late" in ern.salary_component.lower())
        early = sum(ern.amount for ern in doc.deductions if "early" in ern.salary_component.lower())

        row = [
            serial_no,
            doc.biometric_id or "",  
            doc.employee_name or "",  
            doc.designation or "",  
            doc.custom_total_month_days or 0,
            float((doc.custom_total_month_days or 0) -( (doc.custom_absents or 0) + (doc.custom_half_day / 2 or 0)) ), 
            doc.custom_half_day or 0,
            doc.custom_absents or 0,
            doc.custom_total_late or 0,
            doc.custom_total_sitting or 0,
            float(doc.custom_weekend_days + (doc.custom_weekends_half_day/2)),
            int(overtime),
            int(doc.basic_salary or 0),  
            # int(doc.gross_pay or 0),  
            int(tax),
            int(late),
            int(abse),
            int(early),
            int(doc.gross_pay or 0), 
            int(doc.total_deduction or 0),  
            int(doc.net_pay or 0),  
            ""
        ]

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

        totals = [0] * len(columns)

        for i, row in enumerate(rows):
            data.append(row)
            for j in range(4, len(row) - 1):  
                totals[j] += int(row[j]) if isinstance(row[j], (int, float)) else 0

        totals[0] = "<b>Total</b>"
        for k in range(4, len(totals) - 1):
            totals[k] = f"<b>{totals[k]}</b>"

        data.append(totals)

    return data
